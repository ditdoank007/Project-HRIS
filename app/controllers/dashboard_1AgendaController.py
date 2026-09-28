from datetime import datetime
import os

from flask import jsonify, render_template, request, send_file, session, Response

from app import db
from app.models.calendarEventModel import CalendarEvent
from app.models.calendarParticipantModel import CalendarParticipant
from app.models.agendaRapatMetaModel import AgendaRapatMeta
from app.models.agendaRapatAttendanceModel import AgendaRapatAttendance
from app.models.hrisDocumentModel import HrisDocument
from app.models.pegawaiModel import Pegawai
from app.services.calendar.event_service import create_event
from app.services.agenda_rapat_service import (
    attendance_rows,
    build_qr_svg,
    generate_daftar_hadir_pdf,
    get_meta,
    get_or_create_meta,
    record_attendance,
)
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


def _get_organizer(event):
    meta = get_meta(event.EVENT_ID)
    if not meta:
        return None
    return Pegawai.query.filter(Pegawai.NIP == meta.ORGANIZER_NIP).first()


def _can_manage_event(event):
    nip = session.get("nip")
    if not nip:
        return False
    meta = get_meta(event.EVENT_ID)
    organizer_nip = meta.ORGANIZER_NIP if meta else event.CREATED_BY
    return (
        is_administrator()
        or is_hris_operator()
        or event.CREATED_BY == nip
        or organizer_nip == nip
    )


def _can_view_event_document(event):
    nip = session.get("nip")
    if not nip:
        return False
    if is_administrator() or is_hris_operator():
        return True
    if _can_manage_event(event):
        return True
    return CalendarParticipant.query.filter(
        CalendarParticipant.EVENT_ID == event.EVENT_ID,
        CalendarParticipant.NIP == nip,
    ).first() is not None


def _can_upload_event_document(event):
    return _can_manage_event(event)


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

    meta = get_meta(event.EVENT_ID)
    organizer_nip = meta.ORGANIZER_NIP if meta else event.CREATED_BY
    organizer = Pegawai.query.filter(Pegawai.NIP == organizer_nip).first()
    can_view_notulen = _can_view_event_document(event)
    notulen = _get_notulen(event.EVENT_ID) if can_view_notulen else None

    attendance = attendance_rows(event.EVENT_ID)
    attendance_data = [
        {
            "nip": item["pegawai"].NIP,
            "nama": item["pegawai"].NAMA,
            "scanned_date": item["attendance"].SCANNED_DATE.isoformat(),
            "method": item["attendance"].METHOD,
        }
        for item in attendance
    ]

    return {
        "event_id": event.EVENT_ID,
        "title": event.TITLE,
        "description": event.DESCRIPTION,
        "start": event.START_DATE.isoformat() if event.START_DATE else None,
        "end": event.END_DATE.isoformat() if event.END_DATE else None,
        "location": event.LOCATION,
        "status": event.STATUS,
        "event_type": event.EVENT_TYPE,
        "created_by": event.CREATED_BY,
        "created_by_name": (
            Pegawai.query.filter(Pegawai.NIP == event.CREATED_BY).first().NAMA
            if Pegawai.query.filter(Pegawai.NIP == event.CREATED_BY).first()
            else event.CREATED_BY
        ),
        "organizer_nip": organizer_nip,
        "organizer_name": organizer.NAMA if organizer else organizer_nip,
        "participants": [
            {"nip": nip, "nama": names.get(nip, nip)}
            for nip in nips
        ],
        "attendance": attendance_data,
        "attendance_count": len(attendance_data),
        "qr_active": bool(meta and meta.QR_ACTIVE == "Y"),
        "notulen": notulen.to_dict() if notulen else None,
        "can_view_notulen": can_view_notulen,
        "can_upload_notulen": _can_upload_event_document(event),
        "can_edit": _can_manage_event(event) and event.STATUS not in ("SELESAI", "BATAL"),
        "can_complete": _can_manage_event(event) and event.STATUS not in ("SELESAI", "BATAL"),
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
        organizer_nip = str(payload.get("organizer_nip") or "").strip()
        if not title:
            raise ValueError("Judul / agenda rapat wajib diisi.")
        if not organizer_nip:
            raise ValueError("Pimpinan rapat wajib dipilih.")
        _participant_rows([organizer_nip])

        start = _parse_datetime(payload.get("start_date"))
        end = _parse_datetime(payload.get("end_date")) if payload.get("end_date") else None
        if end and end <= start:
            raise ValueError("Waktu selesai harus lebih besar dari waktu mulai.")

        participants = payload.get("participants") or []
        nips = [x.get("nip") if isinstance(x, dict) else x for x in participants]
        _participant_rows(nips)

        from app.models.calendarCategoryModel import CalendarCategory
        category = CalendarCategory.query.filter(CalendarCategory.CODE == "RAPAT").first()

        event = create_event({
            "title": title,
            "description": payload.get("description"),
            "start_date": start,
            "end_date": end,
            "location": payload.get("location"),
            "category_id": category.ID if category else None,
            "event_type": "RAPAT",
            "source": "AGENDA_RAPAT",
            "status": payload.get("status") or "TERJADWAL",
            "participants": [
                {"nip": nip, "role": "PESERTA"}
                for nip in dict.fromkeys(nips)
                if nip != organizer_nip
            ],
        }, user)

        get_or_create_meta(event, organizer_nip, user)
        db.session.commit()
        return jsonify({"status": "success", "data": _serialize_event(event)})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menyimpan agenda rapat."}), 500


def api_agenda_rapat_update(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404
    if event.STATUS in ("SELESAI", "BATAL"):
        return jsonify({"status": "error", "message": "Rapat yang sudah SELESAI/BATAL tidak dapat mengubah data kejadian rapat."}), 409
    if not _can_manage_event(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang mengubah rapat ini."}), 403

    payload = request.get_json(silent=True) or {}
    try:
        title = str(payload.get("title") or "").strip()
        organizer_nip = str(payload.get("organizer_nip") or "").strip()
        if not title or not organizer_nip:
            raise ValueError("Judul dan Pimpinan rapat wajib diisi.")

        _participant_rows([organizer_nip])
        start = _parse_datetime(payload.get("start_date"))
        end = _parse_datetime(payload.get("end_date")) if payload.get("end_date") else None
        if end and end <= start:
            raise ValueError("Waktu selesai harus lebih besar dari waktu mulai.")

        participants = payload.get("participants") or []
        nips = [x.get("nip") if isinstance(x, dict) else x for x in participants]
        _participant_rows(nips)

        old_start = event.START_DATE
        document = _get_notulen(event.EVENT_ID)
        moved_notulen = None

        if document and old_start and start.date() != old_start.date():
            old_path = notulen_absolute_path(old_start, event.EVENT_ID)
            new_path = notulen_absolute_path(start, event.EVENT_ID)
            if not os.path.isfile(old_path):
                raise ValueError("File Notulen yang tersimpan tidak ditemukan di central storage.")
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            os.replace(old_path, new_path)
            moved_notulen = (old_path, new_path)
            document.STORAGE_PATH = notulen_relative_path(start, event.EVENT_ID)
            document.UPDATE_BY = session.get("nip")
            document.UPDATE_DATE = datetime.utcnow()

        event.TITLE = title
        event.DESCRIPTION = payload.get("description")
        event.START_DATE = start
        event.END_DATE = end
        event.LOCATION = payload.get("location")
        event.STATUS = payload.get("status") or event.STATUS
        event.UPDATE_BY = session.get("nip")
        event.UPDATE_DATE = datetime.utcnow()

        attended_nips = {
            row.NIP
            for row in AgendaRapatAttendance.query.filter(
                AgendaRapatAttendance.EVENT_ID == event.EVENT_ID,
                AgendaRapatAttendance.STATUS == "HADIR",
            ).all()
        }

        CalendarParticipant.query.filter(
            CalendarParticipant.EVENT_ID == event.EVENT_ID
        ).delete(synchronize_session=False)

        now = datetime.utcnow()
        planned_nips = set(dict.fromkeys(nips))
        for nip in sorted(planned_nips | attended_nips):
            if nip == organizer_nip and nip not in attended_nips:
                continue
            db.session.add(CalendarParticipant(
                EVENT_ID=event.EVENT_ID,
                NIP=nip,
                ROLE="HADIR" if nip in attended_nips else "PESERTA",
                STATUS="ATTENDED" if nip in attended_nips else "INVITED",
                CREATED_DATE=now,
            ))

        meta = get_meta(event.EVENT_ID) or get_or_create_meta(event, organizer_nip, session.get("nip"))
        meta.ORGANIZER_NIP = organizer_nip
        meta.UPDATE_BY = session.get("nip")
        meta.UPDATE_DATE = now

        db.session.commit()
        return jsonify({"status": "success", "data": _serialize_event(event)})
    except ValueError as exc:
        db.session.rollback()
        if 'moved_notulen' in locals() and moved_notulen:
            old_path, new_path = moved_notulen
            if os.path.isfile(new_path):
                os.replace(new_path, old_path)
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        if 'moved_notulen' in locals() and moved_notulen:
            old_path, new_path = moved_notulen
            if os.path.isfile(new_path):
                os.replace(new_path, old_path)
        return jsonify({"status": "error", "message": "Gagal memperbarui agenda rapat."}), 500


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
    if event.STATUS == "SELESAI":
        return jsonify({"status": "error", "message": "Rapat yang sudah SELESAI tidak dapat dibatalkan."}), 409
    if not _can_manage_event(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang membatalkan rapat ini."}), 403
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
    if not _can_manage_event(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang menyelesaikan rapat ini."}), 403
    if event.STATUS == "BATAL":
        return jsonify({"status": "error", "message": "Rapat yang dibatalkan tidak dapat diselesaikan."}), 400

    event.STATUS = "SELESAI"
    event.UPDATE_BY = session.get("nip", "system")
    event.UPDATE_DATE = datetime.utcnow()
    meta = get_meta(event.EVENT_ID)
    if meta:
        meta.QR_ACTIVE = "Y"
        meta.UPDATE_BY = session.get("nip", "system")
        meta.UPDATE_DATE = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize_event(event)})


def api_pegawai_agenda_search():
    q = str(request.args.get("q") or "").strip()
    query = Pegawai.query
    if q:
        query = query.filter((Pegawai.NIP.like(f"%{q}%")) | (Pegawai.NAMA.like(f"%{q}%")))
    rows = query.filter((Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR != "Y")).order_by(Pegawai.NAMA.asc()).limit(20).all()
    return jsonify({"status": "success", "data": [{"nip": x.NIP, "nama": x.NAMA, "jabatan": x.JABATAN, "unit_kerja": x.UNIT_KERJA} for x in rows]})


def api_agenda_rapat_qr(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404
    if not _can_manage_event(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang melihat QR rapat ini."}), 403

    meta = get_meta(event.EVENT_ID)
    if not meta:
        meta = get_or_create_meta(event, event.CREATED_BY, session.get("nip"))
        db.session.commit()

    svg, scan_url = build_qr_svg(meta.QR_TOKEN)
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-store", "X-QR-Scan-URL": scan_url})


def api_agenda_rapat_scan(token):
    meta = AgendaRapatMeta.query.filter(
        AgendaRapatMeta.QR_TOKEN == token,
        AgendaRapatMeta.QR_ACTIVE == "Y",
    ).first()
    if not meta:
        return render_template(
            "pages/dashboard_1/Agenda Rapat Scan.html",
            success=False,
            message="QR rapat tidak valid atau sudah tidak aktif.",
            event=None,
            pegawai=None,
        ), 404

    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == meta.EVENT_ID,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event or event.STATUS == "BATAL":
        return render_template(
            "pages/dashboard_1/Agenda Rapat Scan.html",
            success=False,
            message="Rapat tidak ditemukan atau sudah dibatalkan.",
            event=event,
            pegawai=None,
        ), 404

    nip = session.get("nip")
    if not nip:
        return render_template(
            "pages/dashboard_1/Agenda Rapat Scan.html",
            success=False,
            message="Silakan login ke HRIS terlebih dahulu, lalu scan QR rapat kembali.",
            event=event,
            pegawai=None,
        ), 401

    try:
        attendance, pegawai, created = record_attendance(event, nip, "QR")
        message = (
            "Kehadiran berhasil dicatat."
            if created
            else "Kehadiran Anda untuk rapat ini sudah tercatat sebelumnya."
        )
        return render_template(
            "pages/dashboard_1/Agenda Rapat Scan.html",
            success=True,
            message=message,
            event=event,
            pegawai=pegawai,
            attendance=attendance,
        )
    except ValueError as exc:
        db.session.rollback()
        return render_template(
            "pages/dashboard_1/Agenda Rapat Scan.html",
            success=False,
            message=str(exc),
            event=event,
            pegawai=None,
        ), 400


def api_agenda_rapat_attendance(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404
    if not _can_manage_event(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang melihat daftar hadir."}), 403

    return jsonify({
        "status": "success",
        "data": [
            {
                "nip": item["pegawai"].NIP,
                "nama": item["pegawai"].NAMA,
                "scanned_date": item["attendance"].SCANNED_DATE.isoformat(),
                "method": item["attendance"].METHOD,
            }
            for item in attendance_rows(event.EVENT_ID)
        ],
    })


def api_agenda_rapat_daftar_hadir_pdf(event_id):
    event = CalendarEvent.query.filter(
        CalendarEvent.EVENT_ID == event_id,
        CalendarEvent.EVENT_TYPE == "RAPAT",
    ).first()
    if not event:
        return jsonify({"status": "error", "message": "Agenda rapat tidak ditemukan."}), 404
    if not _can_manage_event(event):
        return jsonify({"status": "error", "message": "Anda tidak berwenang mengunduh Daftar Hadir."}), 403

    pdf = generate_daftar_hadir_pdf(event)
    safe_name = f"daftar-hadir-rapat-{event.EVENT_ID}.pdf"
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=safe_name,
        max_age=0,
    )


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
