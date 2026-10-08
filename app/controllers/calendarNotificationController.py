from flask import jsonify, request, session

from app import db
from app.models.calendarNotificationModel import CalendarNotification
from app.services.calendar.notification_service import (
    list_for_nip,
    mark_read,
    unread_count,
)


def _serialize(row):
    return {
        "id": row.ID,
        "title": row.TITLE or row.MESSAGE or "Notifikasi",
        "message": row.MESSAGE or "",
        "source_type": row.SOURCE_TYPE or "AGENDA_RAPAT",
        "source_id": row.SOURCE_ID or (
            str(row.EVENT_ID) if row.EVENT_ID is not None else None
        ),
        "url": row.URL,
        "read": row.READ_STATUS == "Y",
        "created_at": (
            row.CREATED_DATE.isoformat()
            if row.CREATED_DATE else (
                row.SENT_DATE.isoformat() if row.SENT_DATE else None
            )
        ),
        "read_at": row.READ_DATE.isoformat() if row.READ_DATE else None,
    }


def api_calendar_notifications():
    nip = str(session.get("nip") or "").strip()
    if not nip:
        return jsonify({"status": "error", "message": "NIP tidak ditemukan."}), 401

    try:
        limit = min(max(int(request.args.get("limit", 30)), 1), 100)
    except (TypeError, ValueError):
        limit = 30

    rows = list_for_nip(nip, limit=limit)
    return jsonify({
        "status": "success",
        "data": [_serialize(row) for row in rows],
        "unread_count": unread_count(nip),
    })


def api_calendar_notifications_unread_count():
    nip = str(session.get("nip") or "").strip()
    if not nip:
        return jsonify({"status": "error", "message": "NIP tidak ditemukan."}), 401

    return jsonify({
        "status": "success",
        "unread_count": unread_count(nip),
    })


def api_calendar_notification_read(notification_id):
    nip = str(session.get("nip") or "").strip()
    if not nip:
        return jsonify({"status": "error", "message": "NIP tidak ditemukan."}), 401

    try:
        notification_id = int(notification_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "ID notifikasi tidak valid."}), 400

    row = mark_read(notification_id, nip)
    if not row:
        return jsonify({"status": "error", "message": "Notifikasi tidak ditemukan."}), 404

    db.session.commit()
    return jsonify({
        "status": "success",
        "data": _serialize(row),
        "unread_count": unread_count(nip),
    })


def api_calendar_notifications_read_all():
    nip = str(session.get("nip") or "").strip()
    if not nip:
        return jsonify({"status": "error", "message": "NIP tidak ditemukan."}), 401

    from datetime import datetime

    db.session.query(CalendarNotification).filter(
        CalendarNotification.NIP == nip,
        CalendarNotification.IS_ACTIVE == "Y",
        CalendarNotification.READ_STATUS == "N",
    ).update(
        {
            CalendarNotification.READ_STATUS: "Y",
            CalendarNotification.READ_DATE: datetime.utcnow(),
        },
        synchronize_session=False,
    )
    db.session.commit()

    return jsonify({
        "status": "success",
        "unread_count": 0,
    })


def _internal_nip():
    from config import Config

    supplied = str(request.headers.get("X-Calendar-Internal-Key") or "").strip()
    expected = str(Config.CALENDAR_INTERNAL_API_KEY or "").strip()
    if not expected or supplied != expected:
        return None

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    return nip or None


def api_calendar_notifications_internal():
    nip = _internal_nip()
    if not nip:
        return jsonify({"status": "error", "message": "Unauthorized."}), 401

    try:
        limit = min(max(int(request.args.get("limit", 30)), 1), 100)
    except (TypeError, ValueError):
        limit = 30

    rows = list_for_nip(nip, limit=limit)
    return jsonify({
        "status": "success",
        "data": [_serialize(row) for row in rows],
        "unread_count": unread_count(nip),
    })


def api_calendar_notifications_unread_count_internal():
    nip = _internal_nip()
    if not nip:
        return jsonify({"status": "error", "message": "Unauthorized."}), 401

    return jsonify({
        "status": "success",
        "unread_count": unread_count(nip),
    })


def api_calendar_notification_read_internal(notification_id):
    nip = _internal_nip()
    if not nip:
        return jsonify({"status": "error", "message": "Unauthorized."}), 401

    try:
        notification_id = int(notification_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "ID notifikasi tidak valid."}), 400

    row = mark_read(notification_id, nip)
    if not row:
        return jsonify({"status": "error", "message": "Notifikasi tidak ditemukan."}), 404

    db.session.commit()
    return jsonify({
        "status": "success",
        "data": _serialize(row),
        "unread_count": unread_count(nip),
    })


def api_calendar_notifications_read_all_internal():
    nip = _internal_nip()
    if not nip:
        return jsonify({"status": "error", "message": "Unauthorized."}), 401

    from datetime import datetime

    db.session.query(CalendarNotification).filter(
        CalendarNotification.NIP == nip,
        CalendarNotification.IS_ACTIVE == "Y",
        CalendarNotification.READ_STATUS == "N",
    ).update(
        {
            CalendarNotification.READ_STATUS: "Y",
            CalendarNotification.READ_DATE: datetime.utcnow(),
        },
        synchronize_session=False,
    )
    db.session.commit()

    return jsonify({
        "status": "success",
        "unread_count": 0,
    })
