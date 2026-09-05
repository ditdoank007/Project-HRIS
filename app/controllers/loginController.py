from flask import request, jsonify, session, redirect
from werkzeug.security import check_password_hash
import requests
from config import Config
from app.models.pegawaiModel import Pegawai
from app.models.jabatanModel import MfJabatan
from app.models.hrisAuthConfigModel import HrisAuthConfig


BDIP_SSO_URL = Config.BDIP_SSO_URL
HRIS_SSO_CALLBACK = Config.HRIS_SSO_CALLBACK


def _get_auth_config():
    return HrisAuthConfig.query.first()


def login():
    data = request.get_json() or {}

    auth_config = HrisAuthConfig.query.first()
    if not auth_config:
        return jsonify({
            "success": False,
            "message": "Konfigurasi autentikasi HRIS belum tersedia."
        }), 500

    password = (data.get("password") or "").strip()
    remember = bool(data.get("remember"))

    # ============================================================
    # SYSADMIN BOOTSTRAP
    # SYSADMIN selalu login lokal, termasuk ketika AUTH_MODE = SSO.
    # ============================================================
    username = (data.get("username") or data.get("nip") or "").strip()

    if (
        username
        and username == auth_config.SYSADMIN_USERNAME
        and auth_config.SYSADMIN_ENABLED
        and password
        and check_password_hash(auth_config.SYSADMIN_PASSWORD_HASH, password)
    ):
        session.clear()
        session["logged_in"] = True
        session["sysadmin"] = True
        session["username"] = username
        session["nama"] = "SYSADMIN"
        session.permanent = remember

        return jsonify({
            "success": True,
            "message": "Login SYSADMIN berhasil.",
            "user": {
                "username": username,
                "nama": "SYSADMIN",
                "sysadmin": True
            }
        })

    # ============================================================
    # SSO MODE
    #
    # Login HRIS menggunakan username BDIP:
    #     dityo.mahendro
    #
    # NIP/FingerID TIDAK digunakan sebagai username login.
    # Setelah BDIP mengenali user, identity NIP/FingerID dipakai
    # untuk mencari PEGAWAI HRIS.
    # ============================================================
    if auth_config.AUTH_MODE.upper() == "SSO":
        if not username:
            return jsonify({
                "success": False,
                "message": "Username BDIP wajib diisi."
            }), 400

        if not password:
            return jsonify({
                "success": False,
                "message": "Password wajib diisi."
            }), 400

        try:
            verify_url = (
                auth_config.SSO_SERVER.rstrip("/")
                + "/api/auth/verify"
            )

            response = requests.post(
                verify_url,
                json={
                    "username": username,
                    "password": password
                },
                timeout=15
            )

            try:
                result = response.json()
            except Exception:
                result = {}

            if response.status_code != 200 or not result.get("success"):
                return jsonify({
                    "success": False,
                    "message": result.get(
                        "message",
                        "Username atau password BDIP tidak valid."
                    )
                }), 401

            sso_data = result.get("data") or {}

            # BDIP identity fields.
            # Support beberapa variasi casing/property name.
            sso_username = (
                sso_data.get("username")
                or sso_data.get("userName")
                or username
            )

            sso_nip = str(
                sso_data.get("nip")
                or sso_data.get("NIP")
                or ""
            ).strip()

            sso_finger_id = str(
                sso_data.get("fingerId")
                or sso_data.get("fingerID")
                or sso_data.get("FingerID")
                or ""
            ).strip()

            # ====================================================
            # MAP BDIP IDENTITY -> MASTER PEGAWAI HRIS
            #
            # Prioritas:
            #   1. NIP
            #   2. FingerID
            #
            # Setelah ketemu, session["nip"] selalu menggunakan
            # NIP milik PEGAWAI HRIS.
            # ====================================================
            pegawai = None

            if sso_nip:
                pegawai = Pegawai.query.filter(
                    Pegawai.NIP == sso_nip
                ).first()

            if not pegawai and sso_finger_id:
                pegawai = Pegawai.query.filter(
                    Pegawai.FingerID == sso_finger_id
                ).first()

            if not pegawai:
                return jsonify({
                    "success": False,
                    "message": (
                        "User BDIP berhasil terautentikasi, "
                        "tetapi belum ditemukan pada master PEGAWAI HRIS."
                    ),
                    "username": sso_username,
                    "nip": sso_nip or None,
                    "fingerId": sso_finger_id or None
                }), 403

            # ====================================================
            # SESSION HRIS
            #
            # NIP internal HRIS berasal dari PEGAWAI yang berhasil
            # dimapping. Authorization tetap menggunakan NIP.
            # ====================================================
            session.clear()
            session["logged_in"] = True
            session["sysadmin"] = False
            session["username"] = sso_username
            session["sso_username"] = sso_username
            session["nip"] = pegawai.NIP
            session["nama"] = pegawai.NAMA
            session.permanent = remember

            return jsonify({
                "success": True,
                "message": "Login SSO berhasil.",
                "user": {
                    "username": sso_username,
                    "nip": pegawai.NIP,
                    "nama": pegawai.NAMA,
                    "fingerId": sso_finger_id,
                    "sysadmin": False
                }
            })

        except requests.RequestException as exc:
            return jsonify({
                "success": False,
                "message": "Server BDIP/SSO tidak dapat dihubungi."
            }), 502

        except Exception as exc:
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "message": "Terjadi kesalahan saat proses login SSO."
            }), 500

    # ============================================================
    # LOCAL MODE
    #
    # LOCAL tetap menggunakan NIP + password PEGAWAI.
    # ============================================================
    nip = (
        data.get("nip")
        or data.get("username")
        or ""
    ).strip()

    if not nip:
        return jsonify({
            "success": False,
            "message": "NIP wajib diisi."
        }), 400

    if not password:
        return jsonify({
            "success": False,
            "message": "Password wajib diisi."
        }), 400

    pegawai = Pegawai.query.filter(
        Pegawai.NIP == nip
    ).first()

    if not pegawai:
        return jsonify({
            "success": False,
            "message": "NIP atau password salah."
        }), 401

    if str(pegawai.PASS or "") != password:
        return jsonify({
            "success": False,
            "message": "NIP atau password salah."
        }), 401

    session.clear()
    session["logged_in"] = True
    session["sysadmin"] = False
    session["username"] = pegawai.NIP
    session["nip"] = pegawai.NIP
    session["nama"] = pegawai.NAMA
    session.permanent = remember

    return jsonify({
        "success": True,
        "message": "Login berhasil.",
        "user": {
            "username": pegawai.NIP,
            "nip": pegawai.NIP,
            "nama": pegawai.NAMA,
            "sysadmin": False
        }
    })

def sso_callback():
    auth_config = _get_auth_config()

    if not auth_config:
        return jsonify({
            "success": False,
            "message": "Konfigurasi login HRIS belum tersedia."
        }), 500

    if auth_config.AUTH_MODE != "SSO":
        return jsonify({
            "success": False,
            "message": "HRIS tidak sedang menggunakan mode SSO."
        }), 400

    code = request.args.get("code", "").strip()

    if not code:
        return jsonify({
            "success": False,
            "message": "SSO authorization code tidak ditemukan."
        }), 400

    try:
        response = requests.post(
            f"{auth_config.SSO_SERVER}/api/auth/sso/exchange",
            json={
                "code": code,
                "redirectUri": auth_config.SSO_CALLBACK
            },
            timeout=10
        )
    except requests.RequestException:
        return jsonify({
            "success": False,
            "message": "Tidak dapat terhubung ke BDIP SSO."
        }), 502

    if not response.ok:
        return jsonify({
            "success": False,
            "message": "Authorization code SSO tidak valid atau sudah kedaluwarsa."
        }), 401

    result = response.json()
    user = result.get("data", {})

    session.permanent = True
    session["logged_in"] = True
    session["username"] = user.get("username", "")
    session["nama"] = user.get("fullName", "")
    session["email"] = user.get("email", "")
    session["role"] = user.get("role", "")

    return redirect("/")


def logout():
    session.clear()
    return jsonify({
        "success": True,
        "message": "Logout berhasil."
    })
