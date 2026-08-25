"""
Helper Rekap Absensi All HRIS Reborn

Business Rule:

1. PEGAWAI menjadi sumber daftar pegawai.
2. ABSENSI menjadi sumber transaksi finger.
3. Pegawai tanpa transaksi finger tetap muncul.
4. Status pegawai mengikuti pegawaiHelper.
5. Helper ini dipakai bersama:
   - VIEW DATA
   - EXPORT EXCEL
   - EXPORT PDF
"""

from app import db

from app.models.pegawaiModel import Pegawai
from app.models.absensiModel import Absensi
from app.models.dinasLuarModel import DinasLuar
from app.models.kalenderModel import MfKalender
from app.models.unitKerjaModel import MfUnitKerja
from app.models.jabatanModel import MfJabatan
from app.models.eselonModel import MfEselon
from app.models.golonganModel import MfGolongan

from app.utils.pegawaiHelper import is_pegawai_aktif_periode



def generate_rekap_absensi_all_data(
    unit_ids,
    tgl_awal,
    tgl_akhir
):
    """
    Generate data dasar Rekap Absensi All.

    Return:

    {
        kalender: [],
        pegawai: [],
        absensi: []
    }
    """


    # ==============================
    # KALENDER
    # ==============================

    kalender_rows = (
        MfKalender.query
        .filter(
            MfKalender.TGL_KERJA >= tgl_awal
        )
        .filter(
            MfKalender.TGL_KERJA <= tgl_akhir
        )
        .order_by(
            MfKalender.TGL_KERJA.asc()
        )
        .all()
    )


    # ==============================
    # PEGAWAI
    # ==============================

    pegawai_rows = (
        Pegawai.query
        .filter(
            Pegawai.UNIT_KERJA_ID.in_(unit_ids)
        )
        .filter(
            Pegawai.TGL_MASUK <= tgl_akhir
        )
        .all()
    )


    pegawai_rows = [
        p for p in pegawai_rows
        if is_pegawai_aktif_periode(
            p,
            tgl_awal,
            tgl_akhir
        )
    ]


    # ============================================================
    # HRIS REBORN REPORT SORTING RULE
    #
    # Urutan resmi laporan:
    #
    # 1. Eselon
    # 2. Jabatan Struktural
    # 3. Class Jabatan
    # 4. Golongan
    # 5. NIP
    #
    # Sama dengan modul Data Absensi.
    # ============================================================

    jabatan_map = {
        x.JABATAN_ID: x.URUT_JABATAN
        for x in MfJabatan.query.all()
    }


    eselon_map = {
        x.ESELON: x.URUT_ESELON
        for x in MfEselon.query.all()
    }


    golongan_map = {
        x.GOL: x.URUTAN
        for x in MfGolongan.query.all()
    }


    pegawai_rows = sorted(
        pegawai_rows,

        key=lambda p: (

            eselon_map.get(
                p.ESELON,
                999
            ),

            jabatan_map.get(
                p.JABATAN_ID,
                999
            ),

            -(p.CLASS_ID or 0),

            golongan_map.get(
                p.GOL,
                999
            ),

            p.NIP or ''

        )
    )


    # ==============================
    # ABSENSI FINGER
    #
    # Connector resmi:
    #
    # ABSENSI.FINGER_ID
    #       |
    #       v
    # PEGAWAI.FINGER_ID
    #
    # ==============================

    absensi_rows = (
        db.session.query(
            Absensi,
            Pegawai
        )
        .join(
            Pegawai,
            Absensi.FINGER_ID ==
            Pegawai.FINGER_ID
        )
        .filter(
            Absensi.TGL_KERJA >= tgl_awal
        )
        .filter(
            Absensi.TGL_KERJA <= tgl_akhir
        )
        .filter(
            Pegawai.UNIT_KERJA_ID.in_(unit_ids)
        )
        .all()
    )


    # ==============================
    # DINAS LUAR
    #
    # Connector:
    #
    # DINAS_LUAR.FINGER_ID
    #        |
    #        v
    # PEGAWAI.FINGER_ID
    #
    # Dipakai oleh:
    # absensiNormalisasiHelper
    #
    # ==============================

    dinas_luar_rows = (
        db.session.query(
            DinasLuar,
            Pegawai
        )
        .join(
            Pegawai,
            DinasLuar.FINGER_ID ==
            Pegawai.FINGER_ID
        )
        .filter(
            Pegawai.UNIT_KERJA_ID.in_(unit_ids)
        )
        .filter(
            DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_akhir
        )
        .filter(
            DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_awal
        )
        .all()
    )


    return {

        "kalender": kalender_rows,

        "pegawai": pegawai_rows,

        "absensi": absensi_rows,

        "dinas_luar": dinas_luar_rows

    }
