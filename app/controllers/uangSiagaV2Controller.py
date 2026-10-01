from flask import jsonify, request

from config import Config
from app.services.uang_siaga_v2_service import calculate_uang_siaga_v2


def api_calendar_benefit_uang_siaga_v2_internal():
    key = request.headers.get("X-Calendar-Internal-Key")
    expected = Config.CALENDAR_INTERNAL_API_KEY

    if not key or key != expected:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP wajib diisi."
        }), 400

    try:
        year = int(request.args.get("year"))
        month = int(request.args.get("month"))

        if year < 2015 or month < 1 or month > 12:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Periode tidak valid."
        }), 400

    try:
        return jsonify(calculate_uang_siaga_v2(nip, year, month))
    except Exception:
        from app import db
        db.session.rollback()
        raise
