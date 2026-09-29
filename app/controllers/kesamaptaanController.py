from datetime import datetime
from flask import jsonify, render_template, request, send_file, session, Response
from sqlalchemy import func

from app import db
from app.models.kesamaptaanKegiatanModel import KesamaptaanKegiatan
from app.models.kesamaptaanKehadiranModel import KesamaptaanKehadiran
from app.models.kesamaptaanDokumentasiModel import KesamaptaanDokumentasi
from app.services.kesamaptaan_service import (
    attendance_rows,
    build_qr_svg,
    documentation_rows,
    employee_for_nip,
    finalize_pdf,
    jakarta_now,
    record_employee_attendance,
    save_photos,
)
from app.utils.authorization import is_administrator, is_hris_operator


JUDUL_KESAMAPTAAN = "KESAMAPTAAN PEGAWAI KANTOR SAR SURABAYA"


def kesamaptaan():
    return render_template("pages/dashboard_4/Kesamaptaan.html")


def _can_manage():
    return is_administrator() or is_hris_operator()


def _serialize(kegiatan, nip=None):
    attendance = attendance_rows(kegiatan.KEGIATAN_ID)
    photos = documentation_rows(kegiatan.KEGIATAN_ID)
    own = next((x for x in attendance if nip and x.NIP == nip), None)

    return {
        "kegiatan_id": kegiatan.KEGIATAN_ID,
        "judul": kegiatan.JUDUL,
        "hari": kegiatan.HARI,
        "tanggal": kegiatan.TANGGAL.isoformat(),
        "jam": kegiatan.JAM.strftime("%H:%M"),
        "status": kegiatan.STATUS,
        "qr_active": kegiatan.QR_ACTIVE == "Y",
        "attendance_count": len(attendance),
        "photo_count": len(photos),
        "employee_attended": bool(own),
        "employee_attendance_at": own.SCANNED_DATE.isoformat() if own else None,
        "pdf_available": bool(kegiatan.PDF_PATH),
        "pdf_sha256": kegiatan.PDF_SHA256,
    }


def api_kesamaptaan_list():
    rows = KesamaptaanKegiatan.query.order_by(
        KesamaptaanKegiatan.TANGGAL.desc(),
        KesamaptaanKegiatan.JAM.desc(),
    ).all()
    return jsonify({"status": "success", "data": [_serialize(x) for x in rows]})


def api_kesamaptaan_save():
    if not _can_manage():
        return jsonify({"status": "error", "message": "Anda tidak berwenang membuat kegiatan Kesamaptaan."}), 403

    payload = request.get_json(silent=True) or {}
    hari = str(payload.get("hari") or "").strip()
    tanggal_raw = str(payload.get("tanggal") or "").strip()
    jam_raw = str(payload.get("jam") or "").strip()

    if not hari or not tanggal_raw or not jam_raw:
        return jsonify({"status": "error", "message": "Hari, tanggal, dan jam wajib diisi."}), 400

    try:
        tanggal = datetime.strptime(tanggal_raw, "%Y-%m-%d").date()
        jam = datetime.strptime(jam_raw, "%H:%M").time()
    except ValueError:
        return jsonify({"status": "error", "message": "Format tanggal atau jam tidak valid."}), 400

    import secrets
    kegiatan = KesamaptaanKegiatan(
        JUDUL=JUDUL_KESAMAPTAAN,
        HARI=hari,
        TANGGAL=tanggal,
        JAM=jam,
        QR_TOKEN=secrets.token_urlsafe(32),
        QR_ACTIVE="Y",
        STATUS="TERJADWAL",
        CREATED_BY=session.get("nip"),
        CREATED_DATE=jakarta_now(),
    )
    db.session.add(kegiatan)
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize(kegiatan)})


def _find_kegiatan(kegiatan_id):
    return KesamaptaanKegiatan.query.filter(
        KesamaptaanKegiatan.KEGIATAN_ID == kegiatan_id
    ).first()


def api_kesamaptaan_detail(kegiatan_id):
    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Kesamaptaan tidak ditemukan."}), 404
    return jsonify({"status": "success", "data": _serialize(kegiatan)})


def api_kesamaptaan_update(kegiatan_id):
    if not _can_manage():
        return jsonify({"status": "error", "message": "Anda tidak berwenang mengubah kegiatan Kesamaptaan."}), 403

    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Kesamaptaan tidak ditemukan."}), 404
    if kegiatan.STATUS in ("SELESAI", "BATAL"):
        return jsonify({"status": "error", "message": "Kegiatan yang sudah SELESAI/BATAL tidak dapat diubah."}), 409

    payload = request.get_json(silent=True) or {}
    hari = str(payload.get("hari") or "").strip()
    tanggal_raw = str(payload.get("tanggal") or "").strip()
    jam_raw = str(payload.get("jam") or "").strip()
    if not hari or not tanggal_raw or not jam_raw:
        return jsonify({"status": "error", "message": "Hari, tanggal, dan jam wajib diisi."}), 400

    try:
        kegiatan.TANGGAL = datetime.strptime(tanggal_raw, "%Y-%m-%d").date()
        kegiatan.JAM = datetime.strptime(jam_raw, "%H:%M").time()
    except ValueError:
        return jsonify({"status": "error", "message": "Format tanggal atau jam tidak valid."}), 400

    kegiatan.HARI = hari
    kegiatan.UPDATE_BY = session.get("nip")
    kegiatan.UPDATE_DATE = jakarta_now()
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize(kegiatan)})


def api_kesamaptaan_cancel(kegiatan_id):
    if not _can_manage():
        return jsonify({"status": "error", "message": "Anda tidak berwenang membatalkan kegiatan Kesamaptaan."}), 403

    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Kesamaptaan tidak ditemukan."}), 404
    if kegiatan.STATUS == "SELESAI":
        return jsonify({"status": "error", "message": "Kegiatan yang sudah SELESAI tidak dapat dibatalkan."}), 409

    kegiatan.STATUS = "BATAL"
    kegiatan.QR_ACTIVE = "N"
    kegiatan.UPDATE_BY = session.get("nip")
    kegiatan.UPDATE_DATE = jakarta_now()
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize(kegiatan)})


def api_kesamaptaan_complete(kegiatan_id):
    if not _can_manage():
        return jsonify({"status": "error", "message": "Anda tidak berwenang menyelesaikan kegiatan Kesamaptaan."}), 403

    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Kesamaptaan tidak ditemukan."}), 404
    if kegiatan.STATUS == "BATAL":
        return jsonify({"status": "error", "message": "Kegiatan yang dibatalkan tidak dapat diselesaikan."}), 400
    if kegiatan.STATUS == "SELESAI":
        return jsonify({"status": "success", "data": _serialize(kegiatan), "message": "Kegiatan sudah SELESAI."})

    try:
        kegiatan.STATUS = "SELESAI"
        kegiatan.QR_ACTIVE = "N"
        kegiatan.UPDATE_BY = session.get("nip")
        kegiatan.UPDATE_DATE = jakarta_now()
        target = finalize_pdf(kegiatan)
        return jsonify({
            "status": "success",
            "data": _serialize(kegiatan),
            "message": f"Kegiatan berhasil diselesaikan. PDF tersimpan di central storage.",
            "pdf_path": kegiatan.PDF_PATH,
        })
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menyelesaikan kegiatan dan membuat PDF."}), 500


def api_kesamaptaan_qr(kegiatan_id):
    if not _can_manage():
        return jsonify({"status": "error", "message": "Anda tidak berwenang melihat QR Kesamaptaan."}), 403

    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Kesamaptaan tidak ditemukan."}), 404

    svg, scan_url = build_qr_svg(kegiatan.QR_TOKEN)
    return Response(
        svg,
        mimetype="image/svg+xml",
        headers={"Cache-Control": "no-store", "X-QR-Scan-URL": scan_url},
    )


def api_kesamaptaan_attendance(kegiatan_id):
    if not _can_manage():
        return jsonify({"status": "error", "message": "Anda tidak berwenang melihat daftar hadir."}), 403
    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Kesamaptaan tidak ditemukan."}), 404

    return jsonify({
        "status": "success",
        "data": [
            {
                "no": index,
                "nip": row.NIP,
                "nama": row.NAMA,
                "scanned_date": row.SCANNED_DATE.isoformat(),
                "signature_available": bool(row.SIGNATURE_PATH),
            }
            for index, row in enumerate(attendance_rows(kegiatan_id), start=1)
        ],
    })


def api_kesamaptaan_photos(kegiatan_id):
    if not _can_manage():
        return jsonify({"status": "error", "message": "Anda tidak berwenang mengunggah dokumentasi."}), 403
    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Kesamaptaan tidak ditemukan."}), 404
    if kegiatan.STATUS in ("SELESAI", "BATAL"):
        return jsonify({"status": "error", "message": "Dokumentasi tidak dapat diubah setelah kegiatan ditutup."}), 409

    files = request.files.getlist("photos")
    if not files:
        return jsonify({"status": "error", "message": "Pilih minimal satu foto."}), 400

    try:
        save_photos(kegiatan, files, session.get("nip"))
        # Buat/perbarui PDF segera setelah dokumentasi tersedia sehingga operator
        # dapat mengunduh daftar hadir tanpa menunggu SELESAI.
        finalize_pdf(kegiatan)
        return jsonify({"status": "success", "data": _serialize(kegiatan), "message": "Foto dokumentasi berhasil disimpan."})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menyimpan foto dokumentasi."}), 500


def api_kesamaptaan_signature(kegiatan_id, nip):
    if not session.get("nip"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Kesamaptaan tidak ditemukan."}), 404
    row = KesamaptaanKehadiran.query.filter(
        KesamaptaanKehadiran.KEGIATAN_ID == kegiatan_id,
        KesamaptaanKehadiran.NIP == str(nip).strip(),
        KesamaptaanKehadiran.STATUS == "HADIR",
    ).first()
    if not row or not row.SIGNATURE_PATH:
        return jsonify({"status": "error", "message": "Tanda tangan tidak tersedia."}), 404
    from pathlib import Path
    path = Path(row.SIGNATURE_PATH).resolve()
    root = Path(__import__("config").Config.HRIS_TTD_ROOT).resolve()
    if path != root and root not in path.parents or not path.is_file():
        return jsonify({"status": "error", "message": "File tanda tangan tidak ditemukan."}), 404
    return send_file(path, mimetype="image/png", as_attachment=False, max_age=0)


def api_kesamaptaan_pdf(kegiatan_id):
    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan or not kegiatan.PDF_PATH:
        return jsonify({"status": "error", "message": "PDF Kesamaptaan belum tersedia."}), 404
    from app.services.kesamaptaan_service import pdf_absolute_path
    path = pdf_absolute_path(kegiatan)
    if not path.is_file():
        return jsonify({"status": "error", "message": "File PDF tidak ditemukan di central storage."}), 404
    return send_file(path, mimetype="application/pdf", as_attachment=False, download_name=f"kesamaptaan-{kegiatan_id:03d}.pdf")


def _calendar_internal_authorized():
    from config import Config
    return request.headers.get("X-Calendar-Internal-Key") == Config.CALENDAR_INTERNAL_API_KEY


def api_kesamaptaan_internal_agenda():
    if not _calendar_internal_authorized():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not nip:
        return jsonify({"status": "error", "message": "NIP wajib diisi."}), 400

    rows = (
        KesamaptaanKehadiran.query
        .filter(
            KesamaptaanKehadiran.NIP == nip,
            KesamaptaanKehadiran.STATUS == "HADIR",
        )
        .order_by(KesamaptaanKehadiran.SCANNED_DATE.desc())
        .all()
    )

    data = []
    seen = set()
    for attendance in rows:
        kegiatan = _find_kegiatan(attendance.KEGIATAN_ID)
        if not kegiatan or kegiatan.STATUS != "SELESAI" or not kegiatan.PDF_PATH:
            continue
        if kegiatan.KEGIATAN_ID in seen:
            continue
        seen.add(kegiatan.KEGIATAN_ID)
        data.append({
            "event_id": kegiatan.KEGIATAN_ID,
            "title": kegiatan.JUDUL,
            "description": "Kesamaptaan Pegawai Kantor SAR Surabaya",
            "start": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
            "end": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
            "location": "Kantor SAR Surabaya",
            "status": kegiatan.STATUS,
            "event_type": "KESAMAPTAAN",
            "attendance_at": attendance.SCANNED_DATE.isoformat(),
            "pdf_available": True,
        })

    return jsonify({"status": "success", "data": data})


def api_kesamaptaan_internal_pdf(kegiatan_id):
    if not _calendar_internal_authorized():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    kegiatan = _find_kegiatan(kegiatan_id)
    if not kegiatan or kegiatan.STATUS != "SELESAI" or not kegiatan.PDF_PATH:
        return jsonify({"status": "error", "message": "PDF Kesamaptaan belum tersedia."}), 404

    allowed = KesamaptaanKehadiran.query.filter(
        KesamaptaanKehadiran.KEGIATAN_ID == kegiatan_id,
        KesamaptaanKehadiran.NIP == nip,
        KesamaptaanKehadiran.STATUS == "HADIR",
    ).first()
    if not allowed:
        return jsonify({"status": "error", "message": "Anda tidak terdaftar sebagai peserta Kesamaptaan."}), 403

    from app.services.kesamaptaan_service import pdf_absolute_path
    path = pdf_absolute_path(kegiatan)
    if not path.is_file():
        return jsonify({"status": "error", "message": "File PDF tidak ditemukan di central storage."}), 404

    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"kesamaptaan-{kegiatan_id:03d}.pdf",
        max_age=0,
    )


def api_kesamaptaan_internal_info():
    from config import Config
    if request.headers.get("X-Calendar-Internal-Key") != Config.CALENDAR_INTERNAL_API_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    token = str(request.args.get("token") or "").strip()
    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not token:
        return jsonify({"status": "error", "message": "Token QR wajib diisi."}), 400

    kegiatan = KesamaptaanKegiatan.query.filter(
        KesamaptaanKegiatan.QR_TOKEN == token
    ).first()
    if not kegiatan:
        return jsonify({"status": "error", "message": "QR Kesamaptaan tidak ditemukan."}), 404

    employee = employee_for_nip(nip) if nip else None
    own = KesamaptaanKehadiran.query.filter(
        KesamaptaanKehadiran.KEGIATAN_ID == kegiatan.KEGIATAN_ID,
        KesamaptaanKehadiran.NIP == nip,
        KesamaptaanKehadiran.STATUS == "HADIR",
    ).first() if nip else None

    return jsonify({
        "status": "success",
        "data": {
            "activity_type": "KESAMAPTAAN",
            "event_id": kegiatan.KEGIATAN_ID,
            "title": kegiatan.JUDUL,
            "start": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
            "end": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
            "location": "Kantor SAR Surabaya",
            "status": kegiatan.STATUS,
            "qr_active": kegiatan.QR_ACTIVE == "Y",
            "employee_eligible": bool(employee),
            "employee_attended": bool(own),
            "employee_attendance_at": own.SCANNED_DATE.isoformat() if own else None,
        }
    })


def api_kesamaptaan_internal_employee_attendance():
    from config import Config
    if request.headers.get("X-Calendar-Internal-Key") != Config.CALENDAR_INTERNAL_API_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()
    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not token or not nip:
        return jsonify({"status": "error", "message": "Token QR dan NIP wajib diisi."}), 400

    kegiatan = KesamaptaanKegiatan.query.filter(
        KesamaptaanKegiatan.QR_TOKEN == token
    ).first()
    if not kegiatan:
        return jsonify({"status": "error", "message": "QR Kesamaptaan tidak ditemukan."}), 404

    try:
        attendance, pegawai, created = record_employee_attendance(kegiatan, nip)
        return jsonify({
            "status": "success",
            "created": created,
            "message": "Kehadiran Kesamaptaan berhasil dicatat." if created else "Kehadiran Anda sudah tercatat sebelumnya.",
            "data": {
                "kegiatan_id": kegiatan.KEGIATAN_ID,
                "nip": pegawai.NIP,
                "nama": pegawai.NAMA,
                "scanned_date": attendance.SCANNED_DATE.isoformat(),
            },
        })
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal mencatat kehadiran Kesamaptaan."}), 500
