from datetime import datetime

from flask import jsonify, render_template, request, session

from app import db
from app.models.calendarEventModel import CalendarEvent
from app.models.calendarParticipantModel import CalendarParticipant
from app.models.pegawaiModel import Pegawai
from app.services.calendar.event_service import create_event


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


def api_pegawai_agenda_search():
    q = str(request.args.get("q") or "").strip()
    query = Pegawai.query
    if q:
        query = query.filter((Pegawai.NIP.like(f"%{q}%")) | (Pegawai.NAMA.like(f"%{q}%")))
    rows = query.filter((Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR != "Y")).order_by(Pegawai.NAMA.asc()).limit(20).all()
    return jsonify({"status": "success", "data": [{"nip": x.NIP, "nama": x.NAMA, "jabatan": x.JABATAN, "unit_kerja": x.UNIT_KERJA} for x in rows]})
