# app/__init__.py
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
from config import Config

db = SQLAlchemy()

# ============================================================
# IMPORT SEMUA MODEL DI LEVEL MODULE — sebelum create_app()
# Supaya SQLAlchemy bisa resolve semua relationship string
# ============================================================
from app.models.pegawaiModel import Pegawai
from app.models.absensiModel import Absensi
from app.models.kalenderModel import MfKalender
from app.models.unitKerjaModel import MfUnitKerja
from app.models.dinasLuarModel import DinasLuar
from app.models.sprinHeaderModel import SprinHeader
from app.models.classModel import MfClass
from app.models.potModel import MfPot
from app.models.jamKerjaModel import MfJamKerja
from app.models.jabatanModel import MfJabatan
from app.models.groupJabatanModel import MfGroupJabatan
from app.models.subGroupJabatanModel import MfSubGroupJabatan
from app.models.loadFingerModel import MfLoadFinger
from app.models.logTransaksiModel import LogTransaksi
from app.models.logTransaksiBackupModel import LogTransaksiBackup
from app.models.joblistModel import MfJoblist
from app.models.jabatanKegiatanModel import MfJabatanKegiatan
from app.models.tunjanganModel import MfTunjangan
from app.models.userAccountModel import UserAccount
from app.models.formModel import MfForm
from app.models.hakAksesFormModel import HakAksesForm
from app.models.agendaDisposisiModel import AgendaDisposisi, AgendaDisposisiPeserta
from app.models.hrisDocumentModel import HrisDocument
from app.models.agendaRapatMetaModel import AgendaRapatMeta
from app.models.agendaRapatAttendanceModel import AgendaRapatAttendance
from app.models.kesamaptaanKegiatanModel import KesamaptaanKegiatan
from app.models.kesamaptaanKehadiranModel import KesamaptaanKehadiran
from app.models.kesamaptaanDokumentasiModel import KesamaptaanDokumentasi
from app.models.bukuTamuModel import BukuTamu, BukuTamuEntry
from app.models.rekamMedisModel import RekamMedis
from app.models.rekamMedisKegiatanModel import RekamMedisKegiatan
from app.models.rekamMedisPesertaModel import RekamMedisPeserta
from app.models.rekamMedisPetugasModel import RekamMedisPetugas


def create_app():
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    app.config.from_object(Config)

    # === KONFIGURASI SESSION ===
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_PERMANENT'] = True

    db.init_app(app)

    # ============================================================
    # AUTHORIZATION GLOBAL UNTUK TEMPLATE
    # User Account + Hak Akses Form mengendalikan seluruh HRIS.
    # ============================================================
    from app.utils.authorization import (
        has_form_access,
        can_read,
        can_modify,
        is_administrator,
        has_user_account,
        is_hris_user,
        is_hris_operator,
    )

    @app.context_processor
    def inject_authorization():
        return {
            'has_form_access': has_form_access,
            'can_read': can_read,
            'can_modify': can_modify,
            'is_administrator': is_administrator,
            'has_user_account': has_user_account,
            'is_hris_user': is_hris_user,
            'is_hris_operator': is_hris_operator,
        }

    from app.routes.routes import main
    app.register_blueprint(main)

    # ============================================================
    # AUTHENTICATED HTML MUST NOT BE BROWSER-CACHED
    # ============================================================
    # Menu pada HRIS bergantung pada session + HAK_AKSES_FORM.
    # Tanpa header ini, browser dapat menampilkan HTML lama setelah
    # login/logout atau perubahan hak akses sampai hard refresh.
    @app.after_request
    def prevent_authenticated_html_cache(response):
        if session.get('nip') and response.content_type and response.content_type.startswith('text/html'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Vary'] = 'Cookie'
        return response

    return app