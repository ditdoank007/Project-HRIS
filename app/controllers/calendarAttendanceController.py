"""
Internal attendance API for the public Calendar QR gateway.

The public Calendar server never writes directly to HRIS database.
It calls these server-to-server endpoints using the internal API key.
"""

from flask import jsonify, request

from app import db
from app.models.agendaRapatAttendanceModel import AgendaRapatAttendance
from app.models.agendaRapatMetaModel import AgendaRapatMeta
from app.models.calendarEventModel import CalendarEvent
from app.models.pegawaiModel import Pegawai
from app.models.kesamaptaanKegiatanModel import KesamaptaanKegiatan
from app.models.kesamaptaanKehadiranModel import KesamaptaanKehadiran
from app.services.agenda_rapat_service import (
    get_meta,
    record_employee_attendance,
    record_guest_attendance,
)
from app.services.kesamaptaan_service import (
    employee_for_nip,
    record_employee_attendance as record_kesamaptaan_attendance,
)


def _authorized():
    from config import Config

    supplied = request.headers.get("X-Calendar-Internal-Key")
    expected = Config.CALENDAR_INTERNAL_API_KEY
    return bool(supplied and expected and supplied == expected)


def _event_from_token(token):
    meta = (
        AgendaRapatMeta.query
        .filter(AgendaRapatMeta.QR_TOKEN == str(token or "").strip())
        .first()
    )
    if not meta:
        return None, None

    event = (
        CalendarEvent.query
        .filter(
            CalendarEvent.EVENT_ID == meta.EVENT_ID,
            CalendarEvent.EVENT_TYPE == "RAPAT",
        )
        .first()
    )
    return meta, event


def _kesamaptaan_from_token(token):
    kegiatan = KesamaptaanKegiatan.query.filter(
        KesamaptaanKegiatan.QR_TOKEN == str(token or "").strip()
    ).first()
    return kegiatan


def _kesamaptaan_payload(kegiatan, nip=None):
    employee = employee_for_nip(nip) if nip else None
    own = KesamaptaanKehadiran.query.filter(
        KesamaptaanKehadiran.KEGIATAN_ID == kegiatan.KEGIATAN_ID,
        KesamaptaanKehadiran.NIP == nip,
        KesamaptaanKehadiran.STATUS == "HADIR",
    ).first() if nip else None
    return {
        "activity_type": "KESAMAPTAAN",
        "event_id": kegiatan.KEGIATAN_ID,
        "title": kegiatan.JUDUL,
        "description": "",
        "start": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
        "end": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
        "location": "Kantor SAR Surabaya",
        "status": kegiatan.STATUS,
        "organizer_name": "Kantor SAR Surabaya",
        "qr_active": kegiatan.QR_ACTIVE == "Y",
        "employee_eligible": bool(employee),
        "employee_attended": bool(own),
        "employee_attendance_at": own.SCANNED_DATE.isoformat() if own else None,
    }


def _event_payload(event, meta, nip=None):
    employee_attendance = None
    if nip:
        employee_attendance = (
            AgendaRapatAttendance.query
            .filter(
                AgendaRapatAttendance.EVENT_ID == event.EVENT_ID,
                AgendaRapatAttendance.ATTENDEE_TYPE == "PEGAWAI",
                AgendaRapatAttendance.NIP == nip,
                AgendaRapatAttendance.STATUS == "HADIR",
            )
            .first()
        )

    organizer = (
        Pegawai.query
        .filter(Pegawai.NIP == meta.ORGANIZER_NIP)
        .first()
        if meta else None
    )

    return {
        "event_id": event.EVENT_ID,
        "title": event.TITLE,
        "description": event.DESCRIPTION,
        "start": event.START_DATE.isoformat() if event.START_DATE else None,
        "end": event.END_DATE.isoformat() if event.END_DATE else None,
        "location": event.LOCATION,
        "status": event.STATUS,
        "organizer_name": organizer.NAMA if organizer else (meta.ORGANIZER_NIP if meta else "-"),
        "qr_active": bool(meta and meta.QR_ACTIVE == "Y"),
        "employee_attended": bool(employee_attendance),
        "employee_attendance_at": (
            employee_attendance.SCANNED_DATE.isoformat()
            if employee_attendance else None
        ),
    }


def api_calendar_rapat_attendance_info():
    if not _authorized():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    token = str(request.args.get("token") or "").strip()
    if not token or len(token) > 150:
        return jsonify({"status": "error", "message": "Token QR tidak valid."}), 400

    meta, event = _event_from_token(token)
    nip = str(request.headers.get("X-Calendar-NIP") or "").strip() or None

    if not meta or not event:
        kegiatan = _kesamaptaan_from_token(token)
        if not kegiatan:
            return jsonify({"status": "error", "message": "QR kegiatan tidak ditemukan."}), 404
        return jsonify({
            "status": "success",
            "data": _kesamaptaan_payload(kegiatan, nip),
        })

    return jsonify({
        "status": "success",
        "data": _event_payload(event, meta, nip),
    })


def api_calendar_rapat_employee_attendance():
    if not _authorized():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()
    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()

    if not token:
        return jsonify({"status": "error", "message": "Token QR wajib diisi."}), 400
    if not nip:
        return jsonify({"status": "error", "message": "NIP pegawai wajib diisi."}), 400

    meta, event = _event_from_token(token)
    if not meta or not event:
        kegiatan = _kesamaptaan_from_token(token)
        if not kegiatan:
            return jsonify({"status": "error", "message": "QR kegiatan tidak ditemukan."}), 404
        try:
            attendance, pegawai, created = record_kesamaptaan_attendance(kegiatan, nip)
            return jsonify({
                "status": "success",
                "created": created,
                "data": {
                    "event_id": kegiatan.KEGIATAN_ID,
                    "attendee_type": "PEGAWAI",
                    "nip": pegawai.NIP,
                    "nama": pegawai.NAMA,
                    "scanned_date": attendance.SCANNED_DATE.isoformat(),
                },
                "message": (
                    "Kehadiran Kesamaptaan berhasil dicatat."
                    if created else "Kehadiran Kesamaptaan Anda sudah tercatat sebelumnya."
                ),
            })
        except ValueError as exc:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(exc)}), 400
        except Exception:
            db.session.rollback()
            return jsonify({"status": "error", "message": "Gagal mencatat kehadiran Kesamaptaan."}), 500

    try:
        attendance, pegawai, created = record_employee_attendance(event, nip, "QR")
        return jsonify({
            "status": "success",
            "created": created,
            "data": {
                "event_id": event.EVENT_ID,
                "attendance_id": attendance.ATTENDANCE_ID,
                "attendee_type": "PEGAWAI",
                "nip": pegawai.NIP,
                "nama": pegawai.NAMA,
                "email": pegawai.MAIL,
                "scanned_date": attendance.SCANNED_DATE.isoformat(),
            },
            "message": (
                "Kehadiran berhasil dicatat."
                if created
                else "Kehadiran Anda untuk rapat ini sudah tercatat sebelumnya."
            ),
        })
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal mencatat kehadiran pegawai."}), 500


def api_calendar_rapat_guest_attendance():
    if not _authorized():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()
    name = str(payload.get("name") or "").strip()
    email = str(payload.get("email") or "").strip()
    signature_data = payload.get("signature_data")
    attendance_key = str(payload.get("attendance_key") or "").strip()
    nip_or_finger = str(payload.get("nip_or_finger") or "").strip()

    if not token:
        return jsonify({"status": "error", "message": "Token QR wajib diisi."}), 400

    meta, event = _event_from_token(token)
    if not meta or not event:
        return jsonify({"status": "error", "message": "QR rapat tidak ditemukan."}), 404

    try:
        attendance, created = record_guest_attendance(
            event=event,
            name=name,
            email=email,
            signature_data=signature_data,
            attendance_key=attendance_key,
            nip_or_finger=nip_or_finger,
            method="QR_GUEST",
        )
        return jsonify({
            "status": "success",
            "created": created,
            "data": {
                "event_id": event.EVENT_ID,
                "attendance_id": attendance.ATTENDANCE_ID,
                "attendee_type": "NON_PEGAWAI",
                "name": attendance.NAME,
                "email": attendance.EMAIL,
                "nip_or_finger": attendance.NIP,
                "scanned_date": attendance.SCANNED_DATE.isoformat(),
            },
            "message": (
                "Kehadiran tamu berhasil dicatat."
                if created
                else "Kehadiran tamu sudah tercatat."
            ),
        })
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal mencatat kehadiran tamu."}), 500
