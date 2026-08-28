"""
HRIS REBORN
Central Employee Sorting Entry Point

File ini adalah SINGLE ENTRY POINT untuk sorting pegawai.

Business Rule sorting sebenarnya berada di:

    app.utils.jabatanHelper.pegawai_sort_key

Jangan membuat aturan sorting baru di controller.

Semua modul HRIS yang membutuhkan daftar pegawai
harus menggunakan:

    sort_pegawai_rows(pegawai_rows)
"""

from app.models.golonganModel import MfGolongan
from app.utils.jabatanHelper import pegawai_sort_key


def _build_golongan_map():
    """
    Membuat mapping:

        kode golongan -> URUTAN

    Contoh:

        IV/e -> 0
        IV/d -> 1
        ...
        III/d -> 5
        ...
        I/a -> 16

    Semakin kecil URUTAN = semakin tinggi golongan.
    """

    rows = MfGolongan.query.all()

    return {
        str(row.GOL or '').strip(): (
            row.URUTAN
            if row.URUTAN is not None
            else 999999
        )
        for row in rows
    }


def sort_pegawai_rows(pegawai_rows):
    """
    STANDARD SORTING PEGAWAI HRIS REBORN.

    Seluruh modul HRIS menggunakan fungsi ini.

    Rule:

    1. Eselon
    2. Class Jabatan
    3. Golongan
    4. Tahun Penerimaan
    5. Tahun Lahir
    6. Tanggal Lahir
    7. Nama
    8. NIP
    """

    if not pegawai_rows:
        return []

    golongan_map = _build_golongan_map()

    return sorted(
        pegawai_rows,
        key=lambda pegawai: pegawai_sort_key(
            pegawai,
            golongan_map=golongan_map
        )
    )
