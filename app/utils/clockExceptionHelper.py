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
        .order_by(
            # 1. Urut jabatan
            db.case(
                (MfJabatan.URUT_JABATAN.is_(None), 1),
                else_=0
            ).asc(),

            MfJabatan.URUT_JABATAN.asc(),

            # 2. Class terbesar dahulu
            Pegawai.CLASS_ID.desc(),

            # 3. Eselon
            MfEselon.URUT_ESELON.asc(),

            # 4. Golongan
            MfGolongan.URUTAN.asc(),

            # 5. NIP
            Pegawai.NIP.asc(),

            # 6. Nama
            Pegawai.NAMA.asc()
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


    return {
        "kalender": kalender_rows,
        "absensi": absensi_rows,
        "pegawai": pegawai_list
    }
