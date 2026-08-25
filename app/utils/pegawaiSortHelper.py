"""
HRIS REBORN
Central Employee Sorting Rule

Urutan final:

1. Eselon
2. Urut Jabatan
3. Class Jabatan descending
4. NIP ascending

Rule ini menjadi Single Source of Sorting
untuk laporan HRIS Reborn.
"""

from app.models.eselonModel import MfEselon
from app.models.jabatanModel import MfJabatan


def _safe_int(value, default=999999):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sort_pegawai_rows(pegawai_rows):
    """
    Sort pegawai berdasarkan rule HRIS Reborn.

    Prioritas:

    Eselon:
        1 -> 2 -> 3 -> 4

    Jabatan:
        menggunakan URUT_JABATAN dari MF_JABATAN

    Class:
        tertinggi -> terendah

    NIP:
        ascending
    """

    # =========================================================
    # MASTER ESELON
    # =========================================================

    eselon_map = {}

    for row in MfEselon.query.all():

        key = str(row.ESELON).strip()

        eselon_map[key] = (
            row.URUT_ESELON
            if row.URUT_ESELON is not None
            else _safe_int(row.ESELON)
        )


    # =========================================================
    # MASTER JABATAN
    # =========================================================

    jabatan_map = {}

    for row in MfJabatan.query.all():

        jabatan_map[row.JABATAN_ID] = (
            row.URUT_JABATAN
            if row.URUT_JABATAN is not None
            else 999999
        )


    # =========================================================
    # SORT FINAL
    # =========================================================

    def sort_key(p):

        eselon_key = str(
            p.ESELON
            if p.ESELON is not None
            else ''
        ).strip()

        urut_eselon = eselon_map.get(
            eselon_key,
            _safe_int(eselon_key)
        )


        urut_jabatan = jabatan_map.get(
            p.JABATAN_ID,
            999999
        )


        class_id = (
            p.CLASS_ID
            if p.CLASS_ID is not None
            else 0
        )


        nip = str(
            p.NIP
            if p.NIP is not None
            else ''
        ).strip()


        return (
            urut_eselon,
            urut_jabatan,
            -_safe_int(class_id, 0),
            nip
        )


    return sorted(
        pegawai_rows,
        key=sort_key
    )
