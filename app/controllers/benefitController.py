from datetime import datetime

from flask import jsonify, request

from config import Config
from app.services.benefit_service import (
    calculate_tunjangan_kinerja,
    calculate_uang_makan,
    calculate_uang_siaga,
)


def _authorized(nip):
    key = request.headers.get("X-Calendar-Internal-Key")
    expected = Config.CALENDAR_INTERNAL_API_KEY

    if not key or key != expected:
        return False, jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    nip = str(nip or "").strip()
    if not nip:
        return False, jsonify({
            "status": "error",
            "message": "NIP wajib diisi."
        }), 400

    return True, nip, None


def api_calendar_benefit_tunjangan_kinerja_internal():
    ok, value, error = _authorized(request.headers.get("X-Calendar-NIP"))
    if not ok:
        return error

    start = request.args.get("start")
    end = request.args.get("end")

    if not start or not end:
        return jsonify({
            "status": "error",
            "message": "Parameter start dan end wajib diisi (YYYY-MM-DD)."
        }), 400

    try:
        result = calculate_tunjangan_kinerja(value, start, end)
    except ValueError as exc:
        return jsonify({
            "status": "error",
            "message": str(exc)
        }), 400
    except Exception:
        from app import db
        db.session.rollback()
        raise

    return jsonify(result)


def _benefit_month_call(calculator):
    ok, value, error = _authorized(request.headers.get("X-Calendar-NIP"))
    if not ok:
        return error

    year = request.args.get("year")
    month = request.args.get("month")

    if not year or not month:
        return jsonify({
            "status": "error",
            "message": "Parameter year dan month wajib diisi."
        }), 400

    try:
        year = int(year)
        month = int(month)
        if year < 2015 or month < 1 or month > 12:
            raise ValueError
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "Periode tidak valid."
        }), 400

    try:
        return jsonify(calculator(value, year, month))
    except Exception:
        from app import db
        db.session.rollback()
        raise


def api_calendar_benefit_uang_makan_internal():
    return _benefit_month_call(calculate_uang_makan)


def api_calendar_benefit_uang_siaga_internal():
    return _benefit_month_call(calculate_uang_siaga)
