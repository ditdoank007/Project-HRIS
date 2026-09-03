"""
Master Jam Kerja Business Rules
================================

Definisi bisnis HRIS Reborn:

Hari Kerja (HK):
    HK-1 = Senin-Kamis
    HK-2 = Jumat

Shift Kerja (SK):
    SK-1 = HK-1 + Reguler
    SK-2 = HK-1 + Siaga
    SK-3 = HK-2 + Reguler
    SK-4 = HK-2 + Siaga

    Jam masuk dan jam pulang TIDAK ditentukan di helper.
    Jam kerja dibaca dari MF_JAM_KERJA berdasarkan
    TGL_MULAI_BERLAKU dan konfigurasi yang tersimpan di database.

Catatan:
    Database MF_JAM_KERJA masih menggunakan struktur legacy:
        Shift      = kode Hari Kerja
        ShiftKerja = kode jenis Shift Kerja
"""

from datetime import date


# ================================================================
# KODE HARI KERJA
# ================================================================

HK_1 = '1'
HK_2 = '2'

HK_SENIN_KAMIS = HK_1
HK_JUMAT = HK_2


# ================================================================
# KODE SHIFT KERJA
# ================================================================

SK_1 = '1'
SK_2 = '2'
SK_3 = '3'
SK_4 = '4'


# ================================================================
# JENIS PEGAWAI
# ================================================================

PEGAWAI_REGULER = 'REGULER'
PETUGAS_SIAGA = 'SIAGA'


# ================================================================
# LABEL HARI KERJA
# ================================================================

HARI_KERJA_LABEL = {
    HK_1: 'Senin-Kamis',
    HK_2: 'Jumat',
}


# ================================================================
# DEFINISI SHIFT KERJA
# ================================================================

SHIFT_KERJA_DEFINITION = {
    SK_1: {
        'kode': SK_1,
        'hari_kerja': HK_1,
        'jenis': PEGAWAI_REGULER,
    },
    SK_2: {
        'kode': SK_2,
        'hari_kerja': HK_1,
        'jenis': PETUGAS_SIAGA,
    },
    SK_3: {
        'kode': SK_3,
        'hari_kerja': HK_2,
        'jenis': PEGAWAI_REGULER,
    },
    SK_4: {
        'kode': SK_4,
        'hari_kerja': HK_2,
        'jenis': PETUGAS_SIAGA,
    },
}


# ================================================================
# RESOLVER
# ================================================================

def resolve_hari_kerja(tgl_kerja):
    """
    Menentukan kode Hari Kerja berdasarkan tanggal.

    Senin-Kamis -> HK-1
    Jumat       -> HK-2
    """

    if isinstance(tgl_kerja, date):
        weekday = tgl_kerja.weekday()
    else:
        weekday = tgl_kerja.date().weekday()

    if weekday == 4:
        return HK_2

    return HK_1


def resolve_hari_kerja_label(hari_kerja):
    """Mengubah kode HK menjadi label yang mudah dibaca."""

    return HARI_KERJA_LABEL.get(
        str(hari_kerja),
        '-',
    )


def resolve_shift_kerja(hari_kerja, jenis_pegawai):
    """
    Menentukan kode Shift Kerja berdasarkan Hari Kerja
    dan jenis pegawai.

    HK-1 + REGULER -> SK-1
    HK-1 + SIAGA   -> SK-2
    HK-2 + REGULER -> SK-3
    HK-2 + SIAGA   -> SK-4
    """

    hari_kerja = str(hari_kerja)
    jenis_pegawai = str(jenis_pegawai).upper()

    if hari_kerja == HK_1:
        if jenis_pegawai == PEGAWAI_REGULER:
            return SK_1

        if jenis_pegawai == PETUGAS_SIAGA:
            return SK_2

    if hari_kerja == HK_2:
        if jenis_pegawai == PEGAWAI_REGULER:
            return SK_3

        if jenis_pegawai == PETUGAS_SIAGA:
            return SK_4

    return None


def get_shift_kerja_definition(shift_kerja):
    """Mengambil definisi lengkap sebuah Shift Kerja."""

    return SHIFT_KERJA_DEFINITION.get(
        str(shift_kerja),
    )


def is_shift_kerja_siaga(shift_kerja):
    """True jika Shift Kerja merupakan jadwal petugas siaga."""

    return str(shift_kerja) in (SK_2, SK_4)


def is_shift_kerja_reguler(shift_kerja):
    """True jika Shift Kerja merupakan jadwal pegawai reguler."""

    return str(shift_kerja) in (SK_1, SK_3)
