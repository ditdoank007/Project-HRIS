from datetime import datetime
import re
from io import BytesIO

import qrcode
from qrcode.image.svg import SvgPathImage
from flask import jsonify, render_template, request, session, Response, send_file

from app import db
from config import Config
from app.models.pegawaiModel import Pegawai
from app.models.rekamMedisKegiatanModel import RekamMedisKegiatan
from app.models.rekamMedisModel import RekamMedis
from app.models.rekamMedisPesertaModel import RekamMedisPeserta
from app.models.rekamMedisPetugasModel import RekamMedisPetugas
from app.controllers.hrisOperationalController import operational_pegawai_query
from app.utils.pegawaiHelper import search_operational_pegawai
from app.utils.authorization import has_form_access, is_administrator


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


def _petugas(kegiatan_id):
    return [
        x.to_dict()
        for x in RekamMedisPetugas.query
        .filter(RekamMedisPetugas.KEGIATAN_ID == kegiatan_id)
        .order_by(RekamMedisPetugas.PETUGAS_ID.asc())
        .all()
    ]


def _peserta(kegiatan_id):
    return (
        RekamMedisPeserta.query
        .filter(RekamMedisPeserta.KEGIATAN_ID == kegiatan_id)
        .order_by(RekamMedisPeserta.SCANNED_AT.asc(), RekamMedisPeserta.NAMA.asc())
        .all()
    )


def _serialize(kegiatan):
    rows = _peserta(kegiatan.KEGIATAN_ID)
    selesai = sum(1 for x in rows if x.STATUS_PEMERIKSAAN == "SELESAI")
    return kegiatan.to_dict(
        total=len(rows),
        selesai=selesai,
        menunggu=len(rows) - selesai,
        petugas=_petugas(kegiatan.KEGIATAN_ID),
    )


def _find_kegiatan(kegiatan_id, jenis=None):
    query = RekamMedisKegiatan.query.filter(RekamMedisKegiatan.KEGIATAN_ID == kegiatan_id)
    if jenis:
        query = query.filter(RekamMedisKegiatan.JENIS == jenis)
    return query.first()


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


def _clean_petugas(payload):
    raw = payload.get("petugas_medis") or []
    if not isinstance(raw, list):
        raw = [raw]
    result = []
    seen = set()
    for item in raw:
        if isinstance(item, dict):
            nama = str(item.get("nama") or "").strip()
            nip = str(item.get("nip") or "").strip() or None
        else:
            nama = str(item or "").strip()
            nip = None
        if not nama:
            continue
        key = (nip or "", nama.casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append({"nama": nama, "nip": nip})
    return result


def api_rekam_medis_petugas_search():
    keyword = str(request.args.get("q") or "").strip()
    if len(keyword) < 1:
        return jsonify({"status": "success", "data": []})

    rows = search_operational_pegawai(keyword, limit=15)
    return jsonify({
        "status": "success",
        "data": [
            {
                "nip": row.NIP,
                "nama": row.NAMA or "",
                "sumber": "PEGAWAI",
            }
            for row in rows
        ],
    })


def _parse_schedule(payload):
    judul = str(payload.get("judul") or "").strip()
    lokasi = str(payload.get("lokasi") or "").strip()
    tanggal = str(payload.get("tanggal") or "").strip()
    jam = str(payload.get("jam") or "").strip()
    if not judul:
        raise ValueError("Judul Rekam Medis wajib diisi.")
    if not tanggal or not jam:
        raise ValueError("Tanggal dan jam wajib diisi.")
    try:
        tanggal_obj = datetime.strptime(tanggal, "%Y-%m-%d").date()
        jam_obj = datetime.strptime(jam, "%H:%M").time()
    except ValueError:
        raise ValueError("Format tanggal atau jam tidak valid.")
    return judul, lokasi, tanggal_obj, jam_obj


def _save(jenis):
    payload = request.get_json(silent=True) or {}
    try:
        judul, lokasi, tanggal_obj, jam_obj = _parse_schedule(payload)
        petugas = _clean_petugas(payload)
        if not petugas:
            raise ValueError("Minimal satu Petugas Medis wajib diisi.")

        kegiatan = RekamMedisKegiatan(
            JENIS=jenis,
            JUDUL=judul,
            LOKASI=lokasi or None,
            TANGGAL=tanggal_obj,
            JAM=jam_obj,
            STATUS="TERJADWAL",
            QR_TOKEN=RekamMedisKegiatan.new_token(),
            QR_ACTIVE="Y",
            CREATED_BY=session.get("nip") or "system",
        )
        db.session.add(kegiatan)
        db.session.flush()

        for petugas_item in petugas:
            db.session.add(RekamMedisPetugas(
                KEGIATAN_ID=kegiatan.KEGIATAN_ID,
                NAMA_PETUGAS=petugas_item["nama"],
                NIP=petugas_item["nip"],
            ))

        db.session.commit()
        return jsonify({"status": "success", "data": _serialize(kegiatan)})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menyimpan kegiatan Rekam Medis."}), 500


def api_rekam_medis_kegiatan_pegawai_save():
    return _save("PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_save():
    return _save("NON_PEGAWAI")


def _detail(kegiatan_id, jenis):
    kegiatan = _find_kegiatan(kegiatan_id, jenis)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Rekam Medis tidak ditemukan."}), 404
    return jsonify({
        "status": "success",
        "data": {
            **_serialize(kegiatan),
            "peserta": [x.to_dict() for x in _peserta(kegiatan_id)],
        },
    })


def api_rekam_medis_kegiatan_pegawai_detail(kegiatan_id):
    return _detail(kegiatan_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_detail(kegiatan_id):
    return _detail(kegiatan_id, "NON_PEGAWAI")


def _update(kegiatan_id, jenis):
    kegiatan = _find_kegiatan(kegiatan_id, jenis)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan Rekam Medis tidak ditemukan."}), 404
    if kegiatan.STATUS in ("SELESAI", "BATAL"):
        return jsonify({"status": "error", "message": "Kegiatan yang sudah SELESAI/BATAL tidak dapat diubah."}), 409

    payload = request.get_json(silent=True) or {}
    try:
        judul, lokasi, tanggal_obj, jam_obj = _parse_schedule(payload)
        petugas = _clean_petugas(payload)
        if not petugas:
            raise ValueError("Minimal satu Petugas Medis wajib diisi.")

        kegiatan.JUDUL = judul
        kegiatan.LOKASI = lokasi or None
        kegiatan.TANGGAL = tanggal_obj
        kegiatan.JAM = jam_obj
        kegiatan.UPDATED_BY = session.get("nip") or "system"
        kegiatan.UPDATED_AT = datetime.utcnow()

        RekamMedisPetugas.query.filter(
            RekamMedisPetugas.KEGIATAN_ID == kegiatan_id
        ).delete(synchronize_session=False)

        for petugas_item in petugas:
            db.session.add(RekamMedisPetugas(
                KEGIATAN_ID=kegiatan_id,
                NAMA_PETUGAS=petugas_item["nama"],
                NIP=petugas_item["nip"],
            ))

        db.session.commit()
        return jsonify({"status": "success", "data": _serialize(kegiatan)})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal mengubah jadwal Rekam Medis."}), 500


def api_rekam_medis_kegiatan_pegawai_update(kegiatan_id):
    return _update(kegiatan_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_update(kegiatan_id):
    return _update(kegiatan_id, "NON_PEGAWAI")


def _cancel(kegiatan_id, jenis):
    kegiatan = _find_kegiatan(kegiatan_id, jenis)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan tidak ditemukan."}), 404
    if kegiatan.STATUS == "SELESAI":
        return jsonify({"status": "error", "message": "Kegiatan yang sudah SELESAI tidak dapat dibatalkan."}), 409
    kegiatan.STATUS = "BATAL"
    kegiatan.QR_ACTIVE = "N"
    kegiatan.UPDATED_BY = session.get("nip") or "system"
    kegiatan.UPDATED_AT = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize(kegiatan)})


def api_rekam_medis_kegiatan_pegawai_cancel(kegiatan_id):
    return _cancel(kegiatan_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_cancel(kegiatan_id):
    return _cancel(kegiatan_id, "NON_PEGAWAI")


def _complete(kegiatan_id, jenis):
    kegiatan = _find_kegiatan(kegiatan_id, jenis)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan tidak ditemukan."}), 404
    if kegiatan.STATUS == "BATAL":
        return jsonify({"status": "error", "message": "Kegiatan yang dibatalkan tidak dapat diselesaikan."}), 409

    rows = _peserta(kegiatan_id)
    if not rows:
        return jsonify({"status": "error", "message": "Belum ada pegawai yang melakukan scan QR Code."}), 400
    pending = [x for x in rows if x.STATUS_PEMERIKSAAN != "SELESAI"]
    if pending:
        return jsonify({
            "status": "error",
            "message": f"Masih ada {len(pending)} pegawai yang belum diperiksa.",
        }), 400

    kegiatan.STATUS = "SELESAI"
    kegiatan.QR_ACTIVE = "N"
    kegiatan.UPDATED_BY = session.get("nip") or "system"
    kegiatan.UPDATED_AT = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize(kegiatan)})


def api_rekam_medis_kegiatan_pegawai_complete(kegiatan_id):
    return _complete(kegiatan_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_complete(kegiatan_id):
    return _complete(kegiatan_id, "NON_PEGAWAI")


def _build_medical_qr(kegiatan):
    base_url = str(Config.CALENDAR_PUBLIC_BASE_URL or "https://calendar.sarsurabaya.id").rstrip("/")
    scan_url = f"{base_url}/rekam-medis-qrcode?token={kegiatan.QR_TOKEN}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(scan_url)
    qr.make(fit=True)

    output = BytesIO()
    qr.make_image(image_factory=SvgPathImage).save(output)
    output.seek(0)
    return output.read(), scan_url


def _qr(kegiatan_id, jenis):
    kegiatan = _find_kegiatan(kegiatan_id, jenis)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan tidak ditemukan."}), 404
    if kegiatan.STATUS in ("SELESAI", "BATAL") or kegiatan.QR_ACTIVE != "Y":
        return jsonify({"status": "error", "message": "QR Code kegiatan sudah tidak aktif."}), 409

    svg, scan_url = _build_medical_qr(kegiatan)
    return Response(
        svg,
        mimetype="image/svg+xml",
        headers={"Cache-Control": "no-store", "X-QR-Scan-URL": scan_url},
    )


def api_rekam_medis_kegiatan_pegawai_qr(kegiatan_id):
    return _qr(kegiatan_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_qr(kegiatan_id):
    return _qr(kegiatan_id, "NON_PEGAWAI")


def _calendar_authorized():
    supplied = request.headers.get("X-Calendar-Internal-Key")
    expected = Config.CALENDAR_INTERNAL_API_KEY
    return bool(supplied and expected and supplied == expected)


def _medical_kegiatan_from_token(token):
    return RekamMedisKegiatan.query.filter(
        RekamMedisKegiatan.QR_TOKEN == str(token or "").strip()
    ).first()


def api_calendar_rekam_medis_info():
    if not _calendar_authorized():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    token = str(request.args.get("token") or "").strip()
    if not token or len(token) > 150:
        return jsonify({"status": "error", "message": "Token QR tidak valid."}), 400

    kegiatan = _medical_kegiatan_from_token(token)
    if not kegiatan:
        return jsonify({"status": "error", "message": "QR Rekam Medis tidak ditemukan."}), 404

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip() or None
    employee = (
        operational_pegawai_query()
        .filter(Pegawai.NIP == nip)
        .first()
    ) if nip else None

    existing_employee = RekamMedisPeserta.query.filter(
        RekamMedisPeserta.KEGIATAN_ID == kegiatan.KEGIATAN_ID,
        RekamMedisPeserta.JENIS_PESERTA == "PEGAWAI",
        RekamMedisPeserta.NIP == nip,
    ).first() if nip else None

    return jsonify({
        "status": "success",
        "data": {
            "activity_type": "REKAM_MEDIS",
            "participant_mode": kegiatan.JENIS,
            "event_id": kegiatan.KEGIATAN_ID,
            "title": kegiatan.JUDUL,
            "start": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
            "end": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
            "location": kegiatan.LOKASI or "Kantor SAR Surabaya",
            "status": kegiatan.STATUS,
            "qr_active": kegiatan.QR_ACTIVE == "Y",
            "employee_eligible": bool(employee),
            "employee_attended": bool(existing_employee),
            "employee_attendance_at": existing_employee.SCANNED_AT.isoformat() if existing_employee else None,
        },
    })


def api_calendar_rekam_medis_employee():
    if not _calendar_authorized():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()
    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not token or not nip:
        return jsonify({"status": "error", "message": "Token QR dan NIP pegawai wajib diisi."}), 400

    kegiatan = _medical_kegiatan_from_token(token)
    if not kegiatan:
        return jsonify({"status": "error", "message": "QR Rekam Medis tidak ditemukan."}), 404
    if kegiatan.STATUS in ("SELESAI", "BATAL") or kegiatan.QR_ACTIVE != "Y":
        return jsonify({"status": "error", "message": "Pendaftaran pemeriksaan sudah ditutup."}), 409
    if kegiatan.JENIS != "PEGAWAI":
        return jsonify({"status": "error", "message": "QR ini diperuntukkan bagi peserta non pegawai."}), 400

    pegawai = operational_pegawai_query().filter(Pegawai.NIP == nip).first()
    if not pegawai:
        return jsonify({"status": "error", "message": "Akun bukan Pegawai Operasional HRIS atau unit kerja sudah tidak aktif."}), 403

    peserta = RekamMedisPeserta.query.filter(
        RekamMedisPeserta.KEGIATAN_ID == kegiatan.KEGIATAN_ID,
        RekamMedisPeserta.JENIS_PESERTA == "PEGAWAI",
        RekamMedisPeserta.NIP == pegawai.NIP,
    ).first()

    created = False
    if not peserta:
        peserta = RekamMedisPeserta(
            KEGIATAN_ID=kegiatan.KEGIATAN_ID,
            JENIS_PESERTA="PEGAWAI",
            NIP=pegawai.NIP,
            NAMA=pegawai.NAMA,
            UNIT_KERJA=pegawai.UNIT_KERJA,
            EMAIL=pegawai.MAIL,
            NO_HANDPHONE=pegawai.NO_TELP,
            STATUS_PEMERIKSAAN="MENUNGGU",
        )
        db.session.add(peserta)
        db.session.commit()
        created = True

    return jsonify({
        "status": "success",
        "created": created,
        "data": peserta.to_dict(),
        "message": "Scan QR berhasil. Anda sudah masuk daftar peserta pemeriksaan." if created else "Anda sudah terdaftar dalam daftar peserta pemeriksaan.",
    })


def api_calendar_rekam_medis_guest():
    if not _calendar_authorized():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()
    nik = str(payload.get("nik") or "").strip()
    nama = str(payload.get("nama") or "").strip()
    jenis_kelamin = str(payload.get("jenis_kelamin") or "").strip().upper()
    instansi = str(payload.get("instansi") or "").strip()
    email = str(payload.get("email") or "").strip()
    no_handphone = str(payload.get("no_handphone") or "").strip()
    tanda_tangan = str(payload.get("tanda_tangan") or "").strip()

    if not token:
        return jsonify({"status": "error", "message": "Token QR wajib diisi."}), 400
    if not re.fullmatch(r"\\d{16}", nik):
        return jsonify({"status": "error", "message": "NIK wajib 16 digit angka."}), 400
    if not nama:
        return jsonify({"status": "error", "message": "Nama Lengkap wajib diisi."}), 400
    if jenis_kelamin not in ("L", "P"):
        return jsonify({"status": "error", "message": "Jenis kelamin wajib dipilih L atau P."}), 400
    if not instansi:
        return jsonify({"status": "error", "message": "Instansi / Organisasi wajib diisi."}), 400
    if not email:
        return jsonify({"status": "error", "message": "Email wajib diisi."}), 400
    if not no_handphone:
        return jsonify({"status": "error", "message": "No. Handphone wajib diisi."}), 400
    if not tanda_tangan or len(tanda_tangan) > 750000:
        return jsonify({"status": "error", "message": "Tanda tangan wajib diisi dan ukurannya tidak valid."}), 400

    kegiatan = _medical_kegiatan_from_token(token)
    if not kegiatan:
        return jsonify({"status": "error", "message": "QR Rekam Medis tidak ditemukan."}), 404
    if kegiatan.STATUS in ("SELESAI", "BATAL") or kegiatan.QR_ACTIVE != "Y":
        return jsonify({"status": "error", "message": "Pendaftaran pemeriksaan sudah ditutup."}), 409
    if kegiatan.JENIS != "NON_PEGAWAI":
        return jsonify({"status": "error", "message": "QR ini diperuntukkan bagi pegawai Kantor SAR Surabaya."}), 400

    peserta = RekamMedisPeserta.query.filter(
        RekamMedisPeserta.KEGIATAN_ID == kegiatan.KEGIATAN_ID,
        RekamMedisPeserta.JENIS_PESERTA == "NON_PEGAWAI",
        RekamMedisPeserta.NIK == nik,
    ).first()

    created = False
    if not peserta:
        peserta = RekamMedisPeserta(
            KEGIATAN_ID=kegiatan.KEGIATAN_ID,
            JENIS_PESERTA="NON_PEGAWAI",
            NIK=nik,
            JENIS_KELAMIN=jenis_kelamin,
            NAMA=nama,
            INSTANSI=instansi,
            EMAIL=email,
            NO_HANDPHONE=no_handphone,
            TANDA_TANGAN=tanda_tangan,
            STATUS_PEMERIKSAAN="MENUNGGU",
        )
        db.session.add(peserta)
        db.session.commit()
        created = True

    return jsonify({
        "status": "success",
        "created": created,
        "data": peserta.to_dict(),
        "message": "Pendaftaran peserta berhasil. Anda sudah masuk daftar pemeriksaan." if created else "Peserta dengan NIK tersebut sudah terdaftar pada pemeriksaan ini.",
    })


def api_rekam_medis_scan(token):
    kegiatan = RekamMedisKegiatan.query.filter(
        RekamMedisKegiatan.QR_TOKEN == str(token).strip()
    ).first()

    if not kegiatan:
        return render_template(
            "pages/dashboard_4/Rekam Medis Scan.html",
            success=False,
            message="QR Code Rekam Medis tidak ditemukan.",
        ), 404

    if kegiatan.STATUS in ("SELESAI", "BATAL") or kegiatan.QR_ACTIVE != "Y":
        return render_template(
            "pages/dashboard_4/Rekam Medis Scan.html",
            success=False,
            message="Pendaftaran pemeriksaan untuk kegiatan ini sudah ditutup.",
            kegiatan=kegiatan,
        ), 409

    nip = str(session.get("nip") or "").strip()
    pegawai = (
        operational_pegawai_query()
        .filter(Pegawai.NIP == nip)
        .first()
    )
    if not pegawai:
        return render_template(
            "pages/dashboard_4/Rekam Medis Scan.html",
            success=False,
            message="Akun Anda bukan Pegawai Operasional HRIS atau Unit Kerja Anda sudah tidak aktif.",
            kegiatan=kegiatan,
        ), 403

    existing = RekamMedisPeserta.query.filter(
        RekamMedisPeserta.KEGIATAN_ID == kegiatan.KEGIATAN_ID,
        RekamMedisPeserta.JENIS_PESERTA == "PEGAWAI",
        RekamMedisPeserta.NIP == pegawai.NIP,
    ).first()

    if existing:
        peserta = existing
        already = True
    else:
        peserta = RekamMedisPeserta(
            KEGIATAN_ID=kegiatan.KEGIATAN_ID,
            JENIS_PESERTA="PEGAWAI",
            NIP=pegawai.NIP,
            NAMA=pegawai.NAMA,
            UNIT_KERJA=pegawai.UNIT_KERJA,
            EMAIL=pegawai.MAIL,
            NO_HANDPHONE=pegawai.NO_TELP,
            STATUS_PEMERIKSAAN="MENUNGGU",
        )
        db.session.add(peserta)
        db.session.commit()
        already = False

    return render_template(
        "pages/dashboard_4/Rekam Medis Scan.html",
        success=True,
        already=already,
        kegiatan=kegiatan,
        peserta=peserta,
        message="Anda sudah terdaftar dalam daftar peserta pemeriksaan." if already
        else "Scan QR berhasil. Anda sudah masuk daftar peserta pemeriksaan.",
    )


def _participant_detail(kegiatan_id, peserta_id, jenis):
    kegiatan = _find_kegiatan(kegiatan_id, jenis)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan tidak ditemukan."}), 404
    peserta = RekamMedisPeserta.query.filter(
        RekamMedisPeserta.PESERTA_ID == peserta_id,
        RekamMedisPeserta.KEGIATAN_ID == kegiatan_id,
        RekamMedisPeserta.JENIS_PESERTA == jenis,
    ).first()
    if not peserta:
        return jsonify({"status": "error", "message": "Peserta tidak ditemukan."}), 404

    rekam = RekamMedis.query.filter(RekamMedis.REKAM_ID == peserta.REKAM_ID).first() if peserta.REKAM_ID else None
    data = peserta.to_dict()
    data["pemeriksaan"] = {
        "tekanan_darah": rekam.TEKANAN_DARAH if rekam else "",
        "nadi": rekam.NADI if rekam else "",
        "frekuensi_nafas": rekam.FREKUENSI_NAFAS if rekam else "",
        "suhu": str(rekam.SUHU) if rekam and rekam.SUHU is not None else "",
        "spo2": rekam.SPO2 if rekam else "",
        "keluhan": rekam.KELUHAN if rekam else "",
        "tindakan": rekam.TINDAKAN if rekam else "",
        "hasil_kebugaran": rekam.HASIL_KEBUGARAN if rekam else "",
        "pemeriksa": rekam.PEMERIKSA if rekam else "",
    }
    return jsonify({"status": "success", "data": data, "petugas_medis": _petugas(kegiatan_id)})


def api_rekam_medis_kegiatan_pegawai_peserta_detail(kegiatan_id, peserta_id):
    return _participant_detail(kegiatan_id, peserta_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_peserta_detail(kegiatan_id, peserta_id):
    return _participant_detail(kegiatan_id, peserta_id, "NON_PEGAWAI")


def _save_exam(kegiatan_id, peserta_id, jenis):
    kegiatan = _find_kegiatan(kegiatan_id, jenis)
    if not kegiatan:
        return jsonify({"status": "error", "message": "Kegiatan tidak ditemukan."}), 404
    if kegiatan.STATUS in ("SELESAI", "BATAL"):
        return jsonify({"status": "error", "message": "Pemeriksaan sudah ditutup."}), 409

    peserta = RekamMedisPeserta.query.filter(
        RekamMedisPeserta.PESERTA_ID == peserta_id,
        RekamMedisPeserta.KEGIATAN_ID == kegiatan_id,
        RekamMedisPeserta.JENIS_PESERTA == jenis,
    ).first()
    if not peserta:
        return jsonify({"status": "error", "message": "Peserta tidak ditemukan."}), 404

    payload = request.get_json(silent=True) or {}
    required = {
        "tekanan_darah": str(payload.get("tekanan_darah") or "").strip(),
        "nadi": str(payload.get("nadi") or "").strip(),
        "frekuensi_nafas": str(payload.get("frekuensi_nafas") or "").strip(),
        "suhu": str(payload.get("suhu") or "").strip(),
        "spo2": str(payload.get("spo2") or "").strip(),
        "hasil_kebugaran": str(payload.get("hasil_kebugaran") or "").strip().upper(),
        "pemeriksa": str(payload.get("pemeriksa") or "").strip(),
    }
    if any(not value for value in required.values()):
        return jsonify({"status": "error", "message": "Semua parameter pemeriksaan utama wajib diisi."}), 400
    if required["hasil_kebugaran"] not in ("FIT", "UNFIT"):
        return jsonify({"status": "error", "message": "Hasil Kebugaran harus FIT atau UNFIT."}), 400

    petugas_names = {x["nama"] for x in _petugas(kegiatan_id)}
    if petugas_names and required["pemeriksa"] not in petugas_names:
        return jsonify({"status": "error", "message": "Pemeriksa harus dipilih dari Petugas Medis kegiatan."}), 400

    try:
        nadi = int(required["nadi"])
        nafas = int(required["frekuensi_nafas"])
        spo2 = int(required["spo2"])
        suhu = float(required["suhu"])
    except ValueError:
        return jsonify({"status": "error", "message": "Nadi, frekuensi nafas, suhu, dan SpO2 harus berupa angka."}), 400

    if not 0 <= spo2 <= 100:
        return jsonify({"status": "error", "message": "SpO2 harus berada pada 0 sampai 100."}), 400

    rekam = RekamMedis.query.filter(RekamMedis.REKAM_ID == peserta.REKAM_ID).first() if peserta.REKAM_ID else None
    if not rekam:
        rekam = RekamMedis(
            JENIS_PASIEN="PEGAWAI" if jenis == "PEGAWAI" else "NON_PEGAWAI",
            NIP=peserta.NIP,
            NIK=peserta.NIK,
            NAMA=peserta.NAMA,
            UNIT_KERJA=peserta.UNIT_KERJA,
            INSTANSI=peserta.INSTANSI,
            EMAIL=peserta.EMAIL,
            NO_HANDPHONE=peserta.NO_HANDPHONE,
            CREATED_BY=session.get("nip") or "system",
        )
        db.session.add(rekam)
        db.session.flush()

    rekam.TEKANAN_DARAH = required["tekanan_darah"]
    rekam.NADI = nadi
    rekam.FREKUENSI_NAFAS = nafas
    rekam.SUHU = suhu
    rekam.SPO2 = spo2
    rekam.KELUHAN = str(payload.get("keluhan") or "").strip() or None
    rekam.TINDAKAN = str(payload.get("tindakan") or "").strip() or None
    rekam.HASIL_KEBUGARAN = required["hasil_kebugaran"]
    rekam.PEMERIKSA = required["pemeriksa"]
    rekam.UPDATED_AT = datetime.utcnow()

    peserta.REKAM_ID = rekam.REKAM_ID
    peserta.STATUS_PEMERIKSAAN = "SELESAI"
    peserta.UPDATED_AT = datetime.utcnow()

    db.session.commit()
    return jsonify({"status": "success", "data": peserta.to_dict()})


def api_rekam_medis_kegiatan_pegawai_peserta_save(kegiatan_id, peserta_id):
    return _save_exam(kegiatan_id, peserta_id, "PEGAWAI")


def api_rekam_medis_kegiatan_non_pegawai_peserta_save(kegiatan_id, peserta_id):
    return _save_exam(kegiatan_id, peserta_id, "NON_PEGAWAI")


def _export_rows(kegiatan_id, jenis):
    kegiatan = _find_kegiatan(kegiatan_id, jenis)
    if not kegiatan:
        raise ValueError("Kegiatan tidak ditemukan.")
    rows = _peserta(kegiatan_id)
    if not rows:
        raise ValueError("Belum ada peserta yang scan QR.")
    pending = [x for x in rows if x.STATUS_PEMERIKSAAN != "SELESAI"]
    if pending:
        raise ValueError("Ekspor hanya tersedia setelah seluruh pegawai yang scan selesai diperiksa.")

    result = []
    for peserta in rows:
        rekam = RekamMedis.query.filter(RekamMedis.REKAM_ID == peserta.REKAM_ID).first()
        result.append((peserta, rekam))
    return kegiatan, result


def api_rekam_medis_kegiatan_pegawai_export_excel(kegiatan_id):
    try:
        kegiatan, rows = _export_rows(kegiatan_id, "PEGAWAI")
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment

        wb = Workbook()
        ws = wb.active
        ws.title = "Rekam Medis Pegawai"
        headers = ["No", "Nama", "NIP", "Unit Kerja", "Tanggal", "Tekanan Darah", "Nadi", "Frekuensi Nafas", "Suhu", "SpO2", "Keluhan", "Tindakan", "Hasil", "Pemeriksa"]
        ws.append(["Kegiatan", kegiatan.JUDUL])
        ws.append(["Lokasi", kegiatan.LOKASI or "-"])
        ws.append(["Tanggal", kegiatan.TANGGAL.strftime("%d-%m-%Y")])
        ws.append([])
        ws.append(headers)
        for i, (peserta, rekam) in enumerate(rows, 1):
            ws.append([
                i, peserta.NAMA, peserta.NIP, peserta.UNIT_KERJA or "-",
                kegiatan.TANGGAL.strftime("%d-%m-%Y"),
                rekam.TEKANAN_DARAH if rekam else "-",
                rekam.NADI if rekam else "-",
                rekam.FREKUENSI_NAFAS if rekam else "-",
                float(rekam.SUHU) if rekam and rekam.SUHU is not None else "-",
                rekam.SPO2 if rekam else "-",
                rekam.KELUHAN if rekam else "-",
                rekam.TINDAKAN if rekam else "-",
                rekam.HASIL_KEBUGARAN if rekam else "-",
                rekam.PEMERIKSA if rekam else "-",
            ])
        for cell in ws[5]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")
        for col in ws.columns:
            letter = col[0].column_letter
            ws.column_dimensions[letter].width = min(max(max(len(str(c.value or "")) for c in col) + 2, 12), 35)

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"rekam-medis-pegawai-{kegiatan.KEGIATAN_ID}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


def api_rekam_medis_kegiatan_pegawai_export_pdf(kegiatan_id):
    try:
        kegiatan, rows = _export_rows(kegiatan_id, "PEGAWAI")
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=8*mm, leftMargin=8*mm, topMargin=8*mm, bottomMargin=8*mm)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("REKAM MEDIS PEGAWAI", styles["Title"]),
            Paragraph(f"Kegiatan: {kegiatan.JUDUL}", styles["Normal"]),
            Paragraph(f"Lokasi: {kegiatan.LOKASI or '-'} · {kegiatan.TANGGAL.strftime('%d-%m-%Y')} {kegiatan.JAM.strftime('%H:%M')} WIB", styles["Normal"]),
            Spacer(1, 5*mm),
        ]
        data = [["No", "Nama", "NIP", "Unit", "TD", "Nadi", "Nafas", "Suhu", "SpO2", "Hasil", "Pemeriksa"]]
        for i, (peserta, rekam) in enumerate(rows, 1):
            data.append([
                str(i), peserta.NAMA or "-", peserta.NIP or "-", peserta.UNIT_KERJA or "-",
                rekam.TEKANAN_DARAH if rekam else "-",
                str(rekam.NADI if rekam else "-"),
                str(rekam.FREKUENSI_NAFAS if rekam else "-"),
                str(rekam.SUHU if rekam else "-"),
                str(rekam.SPO2 if rekam else "-"),
                rekam.HASIL_KEBUGARAN if rekam else "-",
                rekam.PEMERIKSA if rekam else "-",
            ])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e9eef5")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(table)
        doc.build(story)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"rekam-medis-pegawai-{kegiatan.KEGIATAN_ID}.pdf", mimetype="application/pdf")
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
