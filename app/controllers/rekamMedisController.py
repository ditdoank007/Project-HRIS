# app/controllers/rekamMedisController.py
from decimal import Decimal, InvalidOperation

from flask import jsonify, render_template, request, session

from app import db
from app.models.pegawaiModel import Pegawai
from app.models.rekamMedisModel import RekamMedis
from app.utils.pegawaiHelper import search_operational_pegawai
from app.controllers.hrisOperationalController import is_operational_pegawai


def rekam_medis():
    return render_template("pages/dashboard_1/Rekam Medis.html")


def api_rekam_medis_search_pegawai():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"data": []})

    rows = search_operational_pegawai(keyword)
    return jsonify({
        "data": [
            {
                "nip": p.NIP,
                "nama": p.NAMA or "",
                "unit_kerja": p.UNIT_KERJA or "",
            }
            for p in rows
        ]
    })


def _validate(payload):
    jenis = (payload.get("jenis_pasien") or "").strip().upper()
    if jenis not in {"PEGAWAI", "NON_PEGAWAI"}:
        raise ValueError("Jenis pemeriksaan tidak valid.")

    nama = (payload.get("nama") or "").strip()
    if not nama:
        raise ValueError("Nama wajib diisi.")

    if jenis == "PEGAWAI":
        nip = (payload.get("nip") or "").strip()
        if not nip:
            raise ValueError("Pegawai wajib dipilih dari pencarian nama.")

        pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
        if not is_operational_pegawai(pegawai):
            raise ValueError("Pegawai tidak aktif atau unit kerjanya tidak aktif.")
        return jenis, nama, pegawai

    nik = (payload.get("nik") or "").strip()
    instansi = (payload.get("instansi") or "").strip()
    email = (payload.get("email") or "").strip()
    phone = (payload.get("no_handphone") or "").strip()
    if not nik:
        raise ValueError("NIK wajib diisi untuk non pegawai.")
    if not instansi:
        raise ValueError("Instansi / Organisasi wajib diisi.")
    if not email:
        raise ValueError("Email wajib diisi.")
    if not phone:
        raise ValueError("No. Handphone wajib diisi.")
    return jenis, nama, None


def _number(payload, key, label, integer=False):
    raw = payload.get(key)
    if raw in (None, ""):
        return None
    try:
        return int(raw) if integer else Decimal(str(raw))
    except (ValueError, TypeError, InvalidOperation):
        raise ValueError(f"{label} harus berupa angka.")


def api_rekam_medis_save():
    payload = request.get_json(silent=True) or {}
    try:
        jenis, nama, pegawai = _validate(payload)

        record = RekamMedis(
            JENIS_PASIEN=jenis,
            NIP=pegawai.NIP if pegawai else None,
            NIK=(payload.get("nik") or "").strip() or None,
            NAMA=pegawai.NAMA if pegawai else nama,
            UNIT_KERJA=pegawai.UNIT_KERJA if pegawai else None,
            INSTANSI=(payload.get("instansi") or "").strip() or None,
            EMAIL=(payload.get("email") or "").strip() or None,
            NO_HANDPHONE=(payload.get("no_handphone") or "").strip() or None,
            TEKANAN_DARAH=(payload.get("tekanan_darah") or "").strip() or None,
            NADI=_number(payload, "nadi", "Nadi", integer=True),
            FREKUENSI_NAFAS=_number(payload, "frekuensi_nafas", "Frekuensi nafas", integer=True),
            SUHU=_number(payload, "suhu", "Suhu"),
            SPO2=_number(payload, "spo2", "SpO2", integer=True),
            KELUHAN=(payload.get("keluhan") or "").strip() or None,
            TINDAKAN=(payload.get("tindakan") or "").strip() or None,
            HASIL_KEBUGARAN=(payload.get("hasil_kebugaran") or "").strip().upper() or None,
            PEMERIKSA=(payload.get("pemeriksa") or "").strip() or None,
            CREATED_BY=session.get("nip"),
        )
        db.session.add(record)
        db.session.commit()
        return jsonify({"success": True, "data": record.to_dict()})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Gagal menyimpan rekam medis."}), 500
