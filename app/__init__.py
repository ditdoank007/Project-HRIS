# app/__init__.py
from flask import Flask
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

    return app