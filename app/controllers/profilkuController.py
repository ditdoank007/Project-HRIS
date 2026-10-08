# app/controllers/profilkuController.py
import base64
import os
import re
import secrets
from datetime import datetime

import requests
from flask import current_app, jsonify, render_template, request, send_file, session

from app import db
from app.models.pegawaiModel import Pegawai
from app.models.jabatanModel import MfJabatan
from config import Config


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PROFILE_PHOTO_BYTES = 5 * 1024 * 1024


def _current_pegawai():
    nip = str(session.get("nip") or "").strip()
    if not nip:
        return None
    return Pegawai.query.filter(Pegawai.NIP == nip).first()


def _safe_root(config_key, default):
    root = current_app.config.get(config_key) or default
    return os.path.realpath(root)


def _profile_root():
    return _safe_root("HRIS_PROFILE_ROOT", "/mnt/hris-data/FOTO_PROFIL")


def _ttd_root():
    return _safe_root("HRIS_TTD_ROOT", "/mnt/hris-data/TTD_PEGAWAI")


def _ensure_under(root, path):
    candidate = os.path.realpath(path)
    if candidate != root and not candidate.startswith(root + os.sep):
        raise ValueError("Path storage tidak valid.")
    return candidate


def _photo_path(nip):
    root = _profile_root()
    os.makedirs(root, mode=0o750, exist_ok=True)
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        path = os.path.join(root, f"{nip}{ext}")
        if os.path.isfile(path):
            return path
    return None


def _format_profile_date(value):
    """Normalize DB date/datetime/string values for Profilku."""
    if not value:
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value or value.startswith("0000-00-00"):
            return None
        return value[:10]

    try:
        return value.strftime("%Y-%m-%d")
    except (AttributeError, TypeError, ValueError):
        return None


def _profile_payload(pegawai):
    photo = _photo_path(pegawai.NIP)
    ttd = os.path.join(_ttd_root(), f"{pegawai.NIP}.png")

    jabatan_master = None
    if pegawai.JABATAN_ID not in (None, 0):
        jabatan_master = (
            MfJabatan.query
            .filter(MfJabatan.JABATAN_ID == pegawai.JABATAN_ID)
            .first()
        )
    jabatan_nama = (jabatan_master.NAMA_JABATAN if jabatan_master else None) or pegawai.JABATAN

    return {
        "success": True,
        "data": {
            "nip": pegawai.NIP,
            "nama": pegawai.NAMA,
            "finger_id": pegawai.FINGER_ID,
            "pangkat": pegawai.PANGKAT,
            "gol": pegawai.GOL,
            "jabatan": jabatan_nama,
            "unit_kerja": pegawai.UNIT_KERJA,
            "eselon": pegawai.ESELON,
            "tgl_masuk": _format_profile_date(pegawai.TGL_MASUK),
            "status_peg": pegawai.STATUS_PEG,
            "is_keluar": pegawai.IS_KELUAR,
            "tgl_keluar": _format_profile_date(pegawai.TGL_KELUAR),
            "tgl_lahir": _format_profile_date(pegawai.TGL_LAHIR),
            "jenis_kel": pegawai.JENIS_KEL,
            "tempat_lahir": pegawai.TEMPAT_LAHIR,
            "agama": pegawai.AGAMA,
            "status_perkawinan": pegawai.STATUS_PERKAWINAN,
            "hobi": pegawai.HOBI,
            "no_telp": pegawai.NO_TELP,
            "email": pegawai.MAIL,
            "alamat": pegawai.ALAMAT,
            "kelurahan": pegawai.KELURAHAN,
            "kecamatan": pegawai.KECAMATAN,
            "kota": pegawai.KOTA,
            "no_ktp": pegawai.NO_KTP,
            "no_npwp": pegawai.NO_NPWP,
            "tmt_cpns": _format_profile_date(pegawai.TMTCPNS),
            "tmt_pns": _format_profile_date(pegawai.TMTPNS),
            "alasan_keluar": pegawai.ALASAN_KELUAR,
            "gol_recruit": pegawai.GOL_RECRUIT,
            "is_vip": pegawai.IS_VIP,
            "tmt_class": _format_profile_date(pegawai.TMT_CLASS),
            "tmt_pangkat": _format_profile_date(pegawai.TMTPANGKAT),
            "tmt_jabatan": _format_profile_date(pegawai.TMT_JABATAN),
            "photo_url": "/api/profilku/photo" if photo else None,
            "signature_exists": os.path.isfile(ttd),
        },
    }


def profilku():
    pegawai = _current_pegawai()
    if not pegawai:
        return ("Data pegawai tidak ditemukan.", 404)
    return render_template("pages/profilku.html", pegawai=pegawai)


def api_profilku():
    pegawai = _current_pegawai()
    if not pegawai:
        return jsonify({"success": False, "message": "Data pegawai tidak ditemukan."}), 404
    return jsonify(_profile_payload(pegawai))


def api_profilku_update():
    pegawai = _current_pegawai()
    if not pegawai:
        return jsonify({"success": False, "message": "Data pegawai tidak ditemukan."}), 404

    payload = request.get_json(silent=True) or {}
    allowed = {
        "no_telp": "NO_TELP",
        "email": "MAIL",
        "alamat": "ALAMAT",
        "kelurahan": "KELURAHAN",
        "kecamatan": "KECAMATAN",
        "kota": "KOTA",
    }

    try:
        for key, attr in allowed.items():
            if key in payload:
                value = str(payload.get(key) or "").strip()
                setattr(pegawai, attr, value[:100] if key == "email" else value[:50])

        pegawai.UPDATE_BY = str(session.get("nip") or "")[:50]
        pegawai.UPDATE_DATE = datetime.now()
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Profil berhasil disimpan.",
            "data": _profile_payload(pegawai)["data"],
        })
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Gagal menyimpan Profilku")
        return jsonify({"success": False, "message": "Gagal menyimpan profil."}), 500


def api_profilku_photo():
    pegawai = _current_pegawai()
    if not pegawai:
        return jsonify({"success": False, "message": "Data pegawai tidak ditemukan."}), 404

    photo = _photo_path(pegawai.NIP)
    if not photo:
        return ("", 404)
    return send_file(photo, conditional=True)


def api_profilku_photo_upload():
    pegawai = _current_pegawai()
    if not pegawai:
        return jsonify({"success": False, "message": "Data pegawai tidak ditemukan."}), 404

    file = request.files.get("photo")
    if not file or not file.filename:
        return jsonify({"success": False, "message": "Foto wajib dipilih."}), 400

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({"success": False, "message": "Format foto harus JPG, JPEG, PNG, atau WEBP."}), 400

    content = file.read(MAX_PROFILE_PHOTO_BYTES + 1)
    if len(content) > MAX_PROFILE_PHOTO_BYTES:
        return jsonify({"success": False, "message": "Ukuran foto maksimal 5 MB."}), 400
    if not content:
        return jsonify({"success": False, "message": "Foto kosong."}), 400

    root = _profile_root()
    os.makedirs(root, mode=0o750, exist_ok=True)

    # Hanya satu foto aktif per NIP.
    for old_ext in ALLOWED_IMAGE_EXTENSIONS:
        old = _ensure_under(root, os.path.join(root, f"{pegawai.NIP}{old_ext}"))
        if os.path.isfile(old):
            os.unlink(old)

    target = _ensure_under(root, os.path.join(root, f"{pegawai.NIP}{ext}"))
    temp = target + f".{secrets.token_hex(8)}.tmp"
    try:
        with open(temp, "wb") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

    return jsonify({
        "success": True,
        "message": "Foto profil berhasil disimpan.",
        "photo_url": "/api/profilku/photo",
    })


def api_profilku_password():
    pegawai = _current_pegawai()
    if not pegawai:
        return jsonify({"success": False, "message": "Data pegawai tidak ditemukan."}), 404

    payload = request.get_json(silent=True) or {}
    new_password = str(payload.get("new_password") or "")
    confirm = str(payload.get("confirm_password") or "")

    if len(new_password) < 8:
        return jsonify({"success": False, "message": "Password baru minimal 8 karakter."}), 400
    if new_password != confirm:
        return jsonify({"success": False, "message": "Konfirmasi password tidak sama."}), 400

    # Mode SSO: password sumber identitas ada di BDIP/OpenLDAP.
    if str(Config.AUTH_MODE or "").upper() == "SSO":
        username = str(session.get("sso_username") or session.get("username") or "").strip()
        if not username:
            return jsonify({"success": False, "message": "Username SSO tidak ditemukan."}), 401

        try:
            response = requests.post(
                f"{Config.BDIP_SSO_URL.rstrip('/')}/api/users/{requests.utils.quote(username, safe='')}/reset-password",
                json={"newPassword": new_password},
                timeout=15,
            )
            data = response.json() if response.content else {}
            if response.status_code != 200 or not data.get("success", False):
                return jsonify({
                    "success": False,
                    "message": data.get("message") or "Gagal mereset password BDIP.",
                }), response.status_code or 502
        except requests.RequestException:
            current_app.logger.exception("BDIP password reset unavailable")
            return jsonify({"success": False, "message": "Server BDIP tidak dapat dihubungi."}), 502
    else:
        # Compatibility untuk mode LOCAL legacy HRIS.
        pegawai.PASS = new_password
        pegawai.UPDATE_BY = str(session.get("nip") or "")[:50]
        pegawai.UPDATE_DATE = datetime.now()
        db.session.commit()

    return jsonify({"success": True, "message": "Password berhasil diubah."})


def _decode_signature_data_url(data_url):
    data_url = str(data_url or "").strip()
    match = re.fullmatch(r"data:image/png;base64,([A-Za-z0-9+/=\s]+)", data_url)
    if not match:
        raise ValueError("Format tanda tangan tidak valid.")

    encoded = re.sub(r"\s+", "", match.group(1))
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("Data tanda tangan tidak valid.") from exc

    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Ukuran tanda tangan maksimal 2 MB.")

    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("File tanda tangan bukan PNG valid.")

    return raw


def api_profilku_signature_file():
    pegawai = _current_pegawai()
    if not pegawai:
        return jsonify({"success": False, "message": "Data pegawai tidak ditemukan."}), 404

    target = os.path.join(_ttd_root(), f"{pegawai.NIP}.png")
    if not os.path.isfile(target):
        return ("", 404)
    return send_file(target, mimetype="image/png", conditional=True)


def api_profilku_signature():
    pegawai = _current_pegawai()
    if not pegawai:
        return jsonify({"success": False, "message": "Data pegawai tidak ditemukan."}), 404

    payload = request.get_json(silent=True) or {}
    try:
        raw = _decode_signature_data_url(payload.get("signature"))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    root = _ttd_root()
    os.makedirs(root, mode=0o750, exist_ok=True)
    target = _ensure_under(root, os.path.join(root, f"{pegawai.NIP}.png"))
    temp = target + f".{secrets.token_hex(8)}.tmp"

    try:
        with open(temp, "wb") as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

    return jsonify({
        "success": True,
        "message": "Perubahan tanda tangan berhasil disimpan.",
        "filename": f"{pegawai.NIP}.png",
    })


def _internal_nip():
    expected = str(Config.CALENDAR_INTERNAL_API_KEY or "").strip()
    supplied = str(request.headers.get("X-Calendar-Internal-Key") or "").strip()
    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not expected or not secrets.compare_digest(expected, supplied):
        return None, ("Forbidden", 403)
    if not nip:
        return None, ("NIP wajib", 400)
    pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
    if not pegawai:
        return None, ("Not Found", 404)
    return pegawai, None


def api_internal_profile():
    pegawai, error = _internal_nip()
    if error:
        return error
    return jsonify(_profile_payload(pegawai))


def api_internal_profile_update():
    pegawai, error = _internal_nip()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    allowed = {
        "no_telp": "NO_TELP",
        "email": "MAIL",
        "alamat": "ALAMAT",
        "kelurahan": "KELURAHAN",
        "kecamatan": "KECAMATAN",
        "kota": "KOTA",
    }
    try:
        for key, attr in allowed.items():
            if key in payload:
                value = str(payload.get(key) or "").strip()
                setattr(pegawai, attr, value[:100] if key == "email" else value[:50])
        pegawai.UPDATE_BY = f"CALENDAR:{pegawai.NIP}"[:50]
        pegawai.UPDATE_DATE = datetime.now()
        db.session.commit()
        return jsonify(_profile_payload(pegawai))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Gagal menyimpan Profilku dari Calendar")
        return jsonify({"success": False, "message": "Gagal menyimpan profil."}), 500


def api_internal_profile_photo_upload():
    # Reuse the same validation/storage rules, but take NIP from the trusted
    # Calendar internal headers rather than the browser session.
    pegawai, error = _internal_nip()
    if error:
        return error
    file = request.files.get("photo")
    if not file or not file.filename:
        return jsonify({"success": False, "message": "Foto wajib dipilih."}), 400
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({"success": False, "message": "Format foto harus JPG, JPEG, PNG, atau WEBP."}), 400
    content = file.read(MAX_PROFILE_PHOTO_BYTES + 1)
    if len(content) > MAX_PROFILE_PHOTO_BYTES or not content:
        return jsonify({"success": False, "message": "Ukuran foto tidak valid. Maksimal 5 MB."}), 400

    root = _profile_root()
    os.makedirs(root, mode=0o750, exist_ok=True)
    for old_ext in ALLOWED_IMAGE_EXTENSIONS:
        old = _ensure_under(root, os.path.join(root, f"{pegawai.NIP}{old_ext}"))
        if os.path.isfile(old):
            os.unlink(old)
    target = _ensure_under(root, os.path.join(root, f"{pegawai.NIP}{ext}"))
    temp = target + f".{secrets.token_hex(8)}.tmp"
    try:
        with open(temp, "wb") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return jsonify({"success": True, "message": "Foto profil berhasil disimpan."})


def api_internal_profile_password():
    pegawai, error = _internal_nip()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    new_password = str(payload.get("new_password") or "")
    confirm = str(payload.get("confirm_password") or "")
    if len(new_password) < 8 or new_password != confirm:
        return jsonify({"success": False, "message": "Password minimal 8 karakter dan konfirmasi harus sama."}), 400

    if str(Config.AUTH_MODE or "").upper() == "SSO":
        username = str(payload.get("username") or "").strip()
        if not username:
            return jsonify({"success": False, "message": "Username SSO tidak ditemukan."}), 400
        try:
            response = requests.post(
                f"{Config.BDIP_SSO_URL.rstrip('/')}/api/users/{requests.utils.quote(username, safe='')}/reset-password",
                json={"newPassword": new_password},
                timeout=15,
            )
            data = response.json() if response.content else {}
            if response.status_code != 200 or not data.get("success", False):
                return jsonify({"success": False, "message": data.get("message") or "Gagal mereset password BDIP."}), response.status_code or 502
        except requests.RequestException:
            current_app.logger.exception("BDIP password reset unavailable")
            return jsonify({"success": False, "message": "Server BDIP tidak dapat dihubungi."}), 502
    else:
        pegawai.PASS = new_password
        pegawai.UPDATE_BY = f"CALENDAR:{pegawai.NIP}"[:50]
        pegawai.UPDATE_DATE = datetime.now()
        db.session.commit()
    return jsonify({"success": True, "message": "Password berhasil diubah."})


def api_internal_profile_signature_file():
    pegawai, error = _internal_nip()
    if error:
        return error

    target = os.path.join(_ttd_root(), f"{pegawai.NIP}.png")
    if not os.path.isfile(target):
        return ("", 404)
    return send_file(target, mimetype="image/png", conditional=True)


def api_internal_profile_signature():
    pegawai, error = _internal_nip()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    try:
        raw = _decode_signature_data_url(payload.get("signature"))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    root = _ttd_root()
    os.makedirs(root, mode=0o750, exist_ok=True)
    target = _ensure_under(root, os.path.join(root, f"{pegawai.NIP}.png"))
    temp = target + f".{secrets.token_hex(8)}.tmp"

    try:
        with open(temp, "wb") as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

    return jsonify({
        "success": True,
        "message": "Perubahan tanda tangan berhasil disimpan.",
        "filename": f"{pegawai.NIP}.png",
    })


def api_internal_profile_photo():
    expected = str(Config.CALENDAR_INTERNAL_API_KEY or "").strip()
    supplied = str(request.headers.get("X-Calendar-Internal-Key") or "").strip()
    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()

    if not expected or not secrets.compare_digest(expected, supplied):
        return ("Forbidden", 403)
    if not nip:
        return ("NIP wajib", 400)

    pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
    if not pegawai:
        return ("Not Found", 404)

    photo = _photo_path(pegawai.NIP)
    if not photo:
        return ("", 404)
    return send_file(photo, conditional=True)
