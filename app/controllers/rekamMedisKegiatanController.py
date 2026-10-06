from datetime import datetime
from urllib.parse import quote

from flask import jsonify, render_template, request, session, Response

from app import db
from app.models.rekamMedisKegiatanModel import RekamMedisKegiatan
from app.models.rekamMedisModel import RekamMedis
from app.models.rekamMedisPesertaModel import RekamMedisPeserta
from app.services.agenda_rapat_service import build_qr_svg
from app.utils.authorization import has_form_access, is_administrator, is_hris_operator


def _can_access():
    return is_administrator() or has_form_access("REKAM_MEDIS")


def _page(jenis):
    return render_template(
        "pages/dashboard_4/Rekam Medis Kegiatan.html",
        jenis=jenis,
        title="Rekam Medis Pegawai" if jenis == "PEGAWAI" else "Rekam Medis Non Pegawai",
    )


def rekam_medis_pegawai():
    return _page("PEGAWAI")


def rekam_medis_non_pegawai():
    return _page("NON_PEGAWAI")


def _serialize(kegiatan):
    rows = RekamMedisPeserta.query.filter(
        RekamMedisPeserta.KEGIATAN_ID == kegiatan.KEGIATAN_ID
    ).all()
    total = len(rows)
    selesai = sum(1 for x in rows if x.STATUS_PEMERIKSAAN == "SELESAI")
    return kegiatan.to_dict(total, selesai, total - selesai)


def _list(jenis):
    rows = (
        RekamMedisKegiatan.query
        .filter(RekamMedisKegiatan.JENIS == jenis)
        .order_by(RekamMedisKegiatan.TANGGAL.desc(), RekamMedisKegiatan.JAM.desc())
        .all()
    )
    return jsonify({"status": "success", "data": [_serialize(x) for x in rows]})


def api_rekam_medis_kegiatan_pegawai_list():
    return _list("PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_list():
    return _list("NON_PEGAWAI")


def _save(jenis):
    payload = request.get_json(silent=True) or {}
    judul = str(payload.get("judul") or "").strip()
    tanggal = str(payload.get("tanggal") or "").strip()
    jam = str(payload.get("jam") or "").strip()

    if not judul:
        return jsonify({"status": "error", "message": "Judul kegiatan wajib diisi."}), 400
    if not tanggal or not jam:
        return jsonify({"status": "error", "message": "Hari, tanggal, dan jam wajib diisi."}), 400

    try:
        tanggal_obj = datetime.strptime(tanggal, "%Y-%m-%d").date()
        jam_obj = datetime.strptime(jam, "%H:%M").time()
    except ValueError:
        return jsonify({"status": "error", "message": "Format tanggal atau jam tidak valid."}), 400

    kegiatan = RekamMedisKegiatan(
        JENIS=jenis,
        JUDUL=judul,
        TANGGAL=tanggal_obj,
        JAM=jam_obj,
        STATUS="TERJADWAL",
        QR_TOKEN=RekamMedisKegiatan.new_token(),
        QR_ACTIVE="Y",
        CREATED_BY=session.get("nip") or "system",
    )
    db.session.add(kegiatan)
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize(kegiatan)})


def api_rekam_medis_kegiatan_pegawai_save():
    return _save("PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_save():
    return _save("NON_PEGAWAI")


def _detail(kegiatan_id, jenis):
    kegiatan = RekamMedisKegiatan.query.filter(
        RekamMedisKegiatan.KEGIATAN_ID == kegiatan_id,
        RekamMedisKegiatan.JENIS == jenis,
    ).first()
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Rekam Medis tidak ditemukan."}), 404
    return jsonify({"status": "success", "data": _serialize(kegiatan)})


def api_rekam_medis_kegiatan_pegawai_detail(kegiatan_id):
    return _detail(kegiatan_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_detail(kegiatan_id):
    return _detail(kegiatan_id, "NON_PEGAWAI")


def _qr(kegiatan_id, jenis):
    kegiatan = RekamMedisKegiatan.query.filter(
        RekamMedisKegiatan.KEGIATAN_ID == kegiatan_id,
        RekamMedisKegiatan.JENIS == jenis,
    ).first()
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan tidak ditemukan."}), 404
    if not kegiatan.QR_ACTIVE or kegiatan.STATUS in ("SELESAI", "BATAL"):
        return jsonify({"status": "error", "message": "QR Code kegiatan sudah tidak aktif."}), 409

    svg, scan_url = build_qr_svg(kegiatan.QR_TOKEN)
    return Response(svg, mimetype="image/svg+xml", headers={
        "Cache-Control": "no-store",
        "X-QR-Scan-URL": scan_url,
    })


def api_rekam_medis_kegiatan_pegawai_qr(kegiatan_id):
    return _qr(kegiatan_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_qr(kegiatan_id):
    return _qr(kegiatan_id, "NON_PEGAWAI")
