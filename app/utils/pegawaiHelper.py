"""
Helper Business Rule Pegawai HRIS Reborn

HRIS Reborn:
    IS_KELUAR = '0'  -> Aktif
    IS_KELUAR = '1'  -> Tidak aktif

Legacy HRIS 2013:
    ISKELUAR = 'N'   -> Aktif
    ISKELUAR = 'Y'   -> Tidak aktif

Database HRIS Reborn adalah sumber utama.
Legacy hanya sebagai kompatibilitas.
"""


def normalize_status_keluar(value):
    """
    Normalisasi nilai status pegawai.

    Return:
        ACTIVE
        INACTIVE
    """

    if value is None:
        return 'UNKNOWN'

    value = str(value).strip().upper()

    if value in ('0', 'N'):
        return 'ACTIVE'

    if value in ('1', 'Y'):
        return 'INACTIVE'

    return 'UNKNOWN'


def is_pegawai_aktif(pegawai):
    """
    Mengecek apakah pegawai masih aktif.
    """

    return normalize_status_keluar(
        pegawai.IS_KELUAR
    ) == 'ACTIVE'


def is_pegawai_keluar(pegawai):
    """
    Mengecek apakah pegawai sudah keluar.
    """

    return normalize_status_keluar(
        pegawai.IS_KELUAR
    ) == 'INACTIVE'


def is_pegawai_aktif_periode(
    pegawai,
    tgl_awal,
    tgl_akhir
):
    """
    Mengecek pegawai aktif pada periode laporan.

    Mendukung:
    HRIS Reborn:
        0 = aktif
        1 = keluar

    Legacy:
        N = aktif
        Y = keluar
    """

    status = normalize_status_keluar(
        pegawai.IS_KELUAR
    )

    # Belum masuk saat periode laporan
    if pegawai.TGL_MASUK:
        if pegawai.TGL_MASUK.date() > tgl_akhir.date():
            return False

    # Masih aktif
    if status == 'ACTIVE':
        return True

    # Sudah keluar tapi tanggal keluarnya
    # masih setelah awal periode laporan
    if status == 'INACTIVE':

        if pegawai.TGL_KELUAR:
            return (
                pegawai.TGL_KELUAR.date()
                >= tgl_awal.date()
            )

    return False
