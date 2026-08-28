"""
Helper Business Rule Unit Kerja HRIS Reborn.

Single Source of Truth:

    MF_UNIT_KERJA.isUse = 'Y'
        -> Unit aktif / digunakan HRIS

    MF_UNIT_KERJA.isUse = 'N'
        -> Unit nonaktif / tidak digunakan HRIS

Catatan:
- Tidak mengubah database.
- Tidak mengubah data pegawai.
- Digunakan oleh modul yang membutuhkan daftar unit aktif.
"""

from app.models.unitKerjaModel import MfUnitKerja


def get_active_unit_rows():
    """
    Mengambil seluruh Unit Kerja yang aktif digunakan HRIS.

    Return:
        list[MfUnitKerja]
    """

    return (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_USE == 'Y')
        .order_by(
            MfUnitKerja.URUT_REPORT.asc(),
            MfUnitKerja.NAMA_UNIT_KERJA.asc()
        )
        .all()
    )


def get_active_unit_ids():
    """
    Mengambil ID seluruh Unit Kerja aktif.

    Return:
        list[str]

    Contoh:
        ['1', '2', '3', '4', ...]
    """

    return [
        str(unit.UNIT_KERJA_ID)
        for unit in get_active_unit_rows()
        if unit.UNIT_KERJA_ID is not None
    ]


def is_unit_active(unit_kerja_id):
    """
    Mengecek apakah satu Unit Kerja aktif.

    Return:
        True  -> IS_USE = 'Y'
        False -> selain 'Y'
    """

    if unit_kerja_id is None:
        return False

    unit_id = str(unit_kerja_id).strip()

    if not unit_id:
        return False

    return (
        MfUnitKerja.query
        .filter(
            MfUnitKerja.UNIT_KERJA_ID == unit_id,
            MfUnitKerja.IS_USE == 'Y'
        )
        .first()
        is not None
    )
