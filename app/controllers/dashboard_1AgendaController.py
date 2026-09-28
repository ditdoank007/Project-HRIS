from datetime import datetime
import os

from flask import jsonify, render_template, request, send_file, session

from app import db
from app.models.calendarEventModel import CalendarEvent
from app.models.calendarParticipantModel import CalendarParticipant
from app.models.hrisDocumentModel import HrisDocument
from app.models.pegawaiModel import Pegawai
from app.services.calendar.event_service import create_event
from app.services.document_storage import (
    notulen_absolute_path,
    notulen_relative_path,
    restore_previous_notulen,
    save_notulen,
)
from app.utils.authorization import is_administrator, is_hris_operator


def agenda_rapat():
    return render_template("pages/dashboard_1/Agenda Rapat.html")


def _parse_datetime(value):
    if not value:
        raise ValueError("Tanggal dan waktu wajib diisi.")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise ValueError("Format tanggal/waktu tidak valid.")


def _participant_rows(nips):
    clean = []
    for nip in nips or []:
        nip = str(nip).strip()
        if nip and nip not in clean:
            clean.append(nip)
    if not clean:
        return []
    rows = Pegawai.query.filter(Pegawai.NIP.in_(clean)).all()
    found = {x.NIP for x in rows}
    missing = [x for x in clean if x not in found]
    if missing:
        raise ValueError("NIP peserta tidak ditemukan: " + ", ".join(missing))
    return rows


def _can_view_event_document(event):
    nip = session.get("nip")
    if not nip:
        return False
    if is_administrator() or is_hris_operator():
        return True
    if event.CREATED_BY == nip:
        return True
    return CalendarParticipant.query.filter(
        CalendarParticipant.EVENT_ID == event.EVENT_ID,
        CalendarParticipant.NIP == nip,
    ).first() is not None


def _can_upload_event_document(event):
    nip = session.get("nip")
    if not nip:
        return False
    return (
        is_administrator()
        or is_hris_operator()
        or event.CREATED_BY == nip
    )


def _get_notulen(event_id):
    return HrisDocument.query.filter(
        HrisDocument.DOCUMENT_TYPE == "NOTULEN_RAPAT",
        HrisDocument.ENTITY_TYPE == "CALENDAR_EVENT",
        HrisDocument.ENTITY_ID == str(event_id),
    ).first()


def _serialize_event(event):
    participants = (
        CalendarParticipant.query
        .filter(CalendarParticipant.EVENT_ID == event.EVENT_ID)
        .all()
    )
    nips = [p.NIP for p in participants]
    names = {
        p.NIP: p.NAMA
        for p in Pegawai.query.filter(Pegawai.NIP.in_(nips)).all()
    } if nips else {}

    can_view_notulen = _can_view_event_document(event)
    notulen = _get_notulen(event) if can_view_notulen else None

    return {
        "event_id": event.EVENT_ID,
        "title": event.TITLE,
        "description": event.DESCRIPTION,
        "start": event.START_DATE.isoformat() if event.START_DATE else None,
        "end": event.END_DATE.isoformat() if event.END_DATE else None,
        "location": event.LOCATION,
        "status": event.STATUS,
        "event_type": event.EVENT_TYPE,
        "organizer_nip": event.CREATED_BY,
        "organizer_name": names.get(event.CREATED_BY, event.CREATED_BY),
        "participants": [
            {"nip": nip, "nama": names.get(nip, nip)} for nip in nips
        ],
        "notulen": notulen.to_dict() if notulen else None,
        "can_view_notulen": can_view_notulen,
        "can_upload_notulen": _can_upload_event_document(event),
    }

def api_agenda_rapat_list():
    rows = (
        CalendarEvent.query
        .filter(CalendarEvent.EVENT_TYPE == "RAPAT")
        .order_by(CalendarEvent.START_DATE.desc())
        .all()
    )
    return jsonify({"status": "success", "data": [_serialize_event(x) for x in rows]})


def api_agenda_rapat_save():
    payload = request.get_json(silent=True) or {}
    user = session.get("nip")
    if not user:
        return jsonify({"status": "error", "message": "NIP pengguna tidak ditemukan."}), 401

    try:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("Judul / agenda rapat wajib diisi.")
        start = _parse_datetime(payload.get("start_date"))
        end = _parse_datetime(payload.get("end_date")) if payload.get("end_date") else None
        if end and end <= start:
            raise ValueError("Waktu selesai harus lebih besar dari waktu mulai.")

        participants = payload.get("participants") or []
        nips = [x.get("nip") if isinstance(x, dict) else x for x in participants]
        _participant_rows(nips)

        category_id = None
        from app.models.calendarCategoryModel import CalendarCategory
        category = CalendarCategory.query.filter(CalendarCategory.CODE == "RAPAT").first()
        if category:
            category_id = category.ID

        event = create_event({
            "title": title,
            "description": payload.get("description"),
            "start_date": start,
            "end_date": end,
            "location": payload.get("location"),
            "category_id": category_id,
            "event_type": "RAPAT",
            "source": "AGENDA_RAPAT",
            "status": payload.get("status") or "TERJADWAL",
            "participants": [
                {"nip": nip, "role": "ORGANIZER" if nip == user else "PESERTA"}
                for nip in dict.fromkeys([user] + nips)
            ],
        }, user)
        return jsonify({"status": "success", "data": _serialize_event(event)})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menyimpan agenda rapat."}), 500


def api_agenda_rapat_detail(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404
    return jsonify({"status": "success", "data": _serialize_event(event)})


def api_agenda_rapat_cancel(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404
    event.STATUS = "BATAL"
    event.UPDATE_BY = session.get("nip", "system")
    event.UPDATE_DATE = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize_event(event)})


def api_agenda_rapat_complete(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404

    if not _can_upload_event_document(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang menyelesaikan rapat ini."}), 403

    if event.STATUS == "BATAL":
        return jsonify({"status": "error", "message": "Rapat yang dibatalkan tidak dapat diselesaikan."}), 400

    if event.STATUS == "SELESAI":
        return jsonify({"status": "success", "data": _serialize_event(event)})

    event.STATUS = "SELESAI"
    event.UPDATE_BY = session.get("nip", "system")
    event.UPDATE_DATE = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize_event(event)})


def api_pegawai_agenda_search():
    q = str(request.args.get("q") or "").strip()
    query = Pegawai.query
    if q:
        query = query.filter((Pegawai.NIP.like(f"%{q}%")) | (Pegawai.NAMA.like(f"%{q}%")))
    rows = query.filter((Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR != "Y")).order_by(Pegawai.NAMA.asc()).limit(20).all()
    return jsonify({"status": "success", "data": [{"nip": x.NIP, "nama": x.NAMA, "jabatan": x.JABATAN, "unit_kerja": x.UNIT_KERJA} for x in rows]})


def api_agenda_rapat_notulen_upload(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404

    if not _can_upload_event_document(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang mengunggah Notulen rapat ini."}), 403

    file_storage = request.files.get("notulen")
    saved = None
    try:
        saved = save_notulen(file_storage, event.START_DATE, event.EVENT_ID)
        now = datetime.utcnow()
        document = _get_notulen(event.EVENT_ID)

        if document:
            document.ORIGINAL_FILENAME = saved["filename"]
            document.STORAGE_PATH = saved["relative_path"]
            document.MIME_TYPE = saved["mime_type"]
            document.FILE_SIZE = saved["size"]
            document.SHA256 = saved["sha256"]
            document.UPDATE_BY = session.get("nip")
            document.UPDATE_DATE = now
        else:
            document = HrisDocument(
                DOCUMENT_TYPE="NOTULEN_RAPAT",
                ENTITY_TYPE="CALENDAR_EVENT",
                ENTITY_ID=str(event.EVENT_ID),
                ORIGINAL_FILENAME=saved["filename"],
                STORAGE_PATH=saved["relative_path"],
                MIME_TYPE=saved["mime_type"],
                FILE_SIZE=saved["size"],
                SHA256=saved["sha256"],
                CREATED_BY=session.get("nip"),
                CREATED_DATE=now,
            )
            db.session.add(document)

        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Notulen PDF berhasil disimpan.",
            "data": _serialize_event(event),
        })
    except ValueError as exc:
        db.session.rollback()
        if saved:
            restore_previous_notulen(saved)
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        if saved:
            restore_previous_notulen(saved)
        return jsonify({"status": "error", "message": "Gagal menyimpan Notulen PDF."}), 500


def api_agenda_rapat_notulen_download(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404

    if not _can_view_event_document(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang mengakses Notulen rapat ini."}), 403

    document = _get_notulen(event.EVENT_ID)
    if not document:
        return jsonify({"status": "error", "message": "Notulen belum tersedia."}), 404

    expected_path = notulen_absolute_path(event.START_DATE, event.EVENT_ID)
    expected_relative = notulen_relative_path(event.START_DATE, event.EVENT_ID)
    if document.STORAGE_PATH != expected_relative:
        return jsonify({"status": "error", "message": "Metadata storage Notulen tidak valid."}), 409

    if not os.path.isfile(expected_path):
        return jsonify({"status": "error", "message": "File Notulen tidak ditemukan di central storage."}), 404

    return send_file(
        expected_path,
        mimetype=document.MIME_TYPE,
        as_attachment=False,
        download_name=document.ORIGINAL_FILENAME,
        max_age=0,
    )
