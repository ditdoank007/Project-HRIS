"""
Helper Rekap Clock Exception HRIS Reborn

Sumber data:
- Kalender
- Absensi finger
- Pegawai aktif periode

Dipakai oleh:
- VIEW DATA
- EXPORT EXCEL
- EXPORT PDF
"""


def generate_clock_exception_data(
    unit_ids,
    tgl_awal,
    tgl_akhir
):
    """
    Generate dataset Rekap Clock Exception.

    Return:
        dict siap ditampilkan/export
    """

    from app import db
    from app.models.pegawaiModel import Pegawai
    from app.models.absensiModel import Absensi
    from app.models.kalenderModel import MfKalender
    from app.models.unitKerjaModel import MfUnitKerja
    from app.models.jabatanModel import MfJabatan
    from app.models.eselonModel import MfEselon
    from app.models.golonganModel import MfGolongan
    from app.utils.pegawaiHelper import is_pegawai_aktif_periode
    from app.utils.pegawaiSortHelper import sort_pegawai_rows


    kalender_rows = (
        MfKalender.query
        .filter(
            MfKalender.TGL_KERJA.between(
                tgl_awal,
                tgl_akhir
            )
        )
        .order_by(
            MfKalender.TGL_KERJA.asc()
        )
        .all()
    )


    absensi_rows = (
        db.session.query(
            Absensi,
            Pegawai,
            MfUnitKerja
        )
        .join(
            Pegawai,
            Absensi.FINGER_ID == Pegawai.FINGER_ID
        )
        .join(
            MfUnitKerja,
            Pegawai.UNIT_KERJA_ID ==
            MfUnitKerja.UNIT_KERJA_ID
        )
        .filter(
            Absensi.TGL_KERJA.between(
                tgl_awal,
                tgl_akhir
            )
        )
        .filter(
            Pegawai.UNIT_KERJA_ID.in_(unit_ids)
        )
        .all()
    )


    pegawai_list = (
        Pegawai.query
        .outerjoin(
            MfJabatan,
            Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID
        )
        .outerjoin(
            MfEselon,
            Pegawai.ESELON == MfEselon.ESELON
        )
        .outerjoin(
            MfGolongan,
            Pegawai.GOL == MfGolongan.GOL
        )
        .filter(
            Pegawai.UNIT_KERJA_ID.in_(unit_ids)
        )
        .filter(
            Pegawai.TGL_MASUK <= tgl_akhir
        )
        .all()
    )


    pegawai_list = [
        p for p in pegawai_list
        if is_pegawai_aktif_periode(
            p,
            tgl_awal,
            tgl_akhir
        )
    ]


    # ============================================================
    # STANDARD SORTING HRIS REBORN
    #
    # Jangan membuat rule sorting lokal di modul.
    # Seluruh laporan menggunakan pegawaiSortHelper.
    # ============================================================

    pegawai_list = sort_pegawai_rows(
        pegawai_list
    )


    return {
        "kalender": kalender_rows,
        "absensi": absensi_rows,
        "pegawai": pegawai_list
    }
