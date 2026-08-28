"""
Business Rule Pegawai HRIS Reborn.

============================================================
STATUS PEGAWAI
============================================================

IS_KELUAR:

    N = Pegawai aktif
    Y = Pegawai keluar / tidak aktif

Database HRIS Reborn menggunakan Y/N sebagai
Single Source of Truth untuk status keluar pegawai.


============================================================
PEGAWAI OPERASIONAL
============================================================

Pegawai Operasional adalah pegawai yang:

    Pegawai.IS_KELUAR = 'N'

dan berada pada Unit Kerja:

    MfUnitKerja.IS_USE = 'Y'

Dengan demikian:

    PEGAWAI OPERASIONAL
        =
    IS_KELUAR = 'N'
        AND
    UNIT_KERJA.IS_USE = 'Y'


============================================================
CATATAN
============================================================

Data pegawai dan data Unit Kerja tidak dihapus ketika
statusnya menjadi tidak aktif.

Unit Kerja dikendalikan melalui:

    MF_UNIT_KERJA.IS_USE

Helper ini menjadi pusat Business Rule Pegawai.

Modul lama yang membutuhkan aturan "aktif pada periode"
tetap menggunakan:

    is_pegawai_aktif_periode()

Aturan periode tidak dicampur dengan status operasional
Unit Kerja agar histori laporan tetap aman.
"""

from app.models.pegawaiModel import Pegawai
from app.models.unitKerjaModel import MfUnitKerja
from app.utils.pegawaiSortHelper import sort_pegawai_rows


# ============================================================
# STATUS PEGAWAI
# ============================================================

def normalize_status_keluar(value):
    """
    Normalisasi nilai status pegawai.

    Return:
        ACTIVE
        INACTIVE
        UNKNOWN
    """

    if value is None:
        return 'UNKNOWN'

    value = str(value).strip().upper()

    if value == 'N':
        return 'ACTIVE'

    if value == 'Y':
        return 'INACTIVE'

    return 'UNKNOWN'


def is_pegawai_aktif(pegawai):
    """
    Mengecek apakah pegawai masih aktif.

    Catatan:
    Fungsi ini hanya memeriksa status IS_KELUAR.

    Tidak memeriksa status Unit Kerja.
    """

    if pegawai is None:
        return False

    return normalize_status_keluar(
        pegawai.IS_KELUAR
    ) == 'ACTIVE'


def is_pegawai_keluar(pegawai):
    """
    Mengecek apakah pegawai sudah keluar.

    Catatan:
    Fungsi ini hanya memeriksa status IS_KELUAR.
    """

    if pegawai is None:
        return False

    return normalize_status_keluar(
        pegawai.IS_KELUAR
    ) == 'INACTIVE'


# ============================================================
# PEGAWAI AKTIF PADA PERIODE
# ============================================================

def is_pegawai_aktif_periode(
    pegawai,
    tgl_awal,
    tgl_akhir
):
    """
    Mengecek apakah pegawai aktif pada periode tertentu.

    Business Rule:

    1. Pegawai yang belum masuk sampai akhir periode
       tidak dihitung.

    2. Pegawai yang masih aktif (IS_KELUAR = N)
       dihitung.

    3. Pegawai yang sudah keluar (IS_KELUAR = Y)
       tetap dihitung apabila tanggal keluarnya
       berada pada atau setelah tanggal awal periode.

    Fungsi ini sengaja tidak memeriksa IS_USE Unit Kerja.

    Alasannya:
    laporan historis harus dapat mengambil data pegawai
    berdasarkan kondisi pada periode yang dilaporkan.
    """

    if pegawai is None:
        return False

    status = normalize_status_keluar(
        pegawai.IS_KELUAR
    )

    # --------------------------------------------------------
    # Belum masuk saat periode laporan
    # --------------------------------------------------------

    if pegawai.TGL_MASUK:
        if pegawai.TGL_MASUK.date() > tgl_akhir.date():
            return False

    # --------------------------------------------------------
    # Masih aktif
    # --------------------------------------------------------

    if status == 'ACTIVE':
        return True

    # --------------------------------------------------------
    # Sudah keluar tetapi masih termasuk periode laporan
    # --------------------------------------------------------

    if status == 'INACTIVE':

        if pegawai.TGL_KELUAR:
            return (
                pegawai.TGL_KELUAR.date()
                >= tgl_awal.date()
            )

    return False


# ============================================================
# UNIT KERJA PEGAWAI
# ============================================================

def get_pegawai_unit(pegawai):
    """
    Mengambil Unit Kerja seorang pegawai.

    Return:
        MfUnitKerja
        atau None jika tidak ditemukan.
    """

    if pegawai is None:
        return None

    if pegawai.UNIT_KERJA_ID is None:
        return None

    return (
        MfUnitKerja.query
        .filter(
            MfUnitKerja.UNIT_KERJA_ID
            == pegawai.UNIT_KERJA_ID
        )
        .first()
    )


def is_unit_pegawai_aktif(pegawai):
    """
    Mengecek apakah Unit Kerja pegawai masih aktif digunakan HRIS.

    Return:
        True  -> Unit IS_USE = Y
        False -> Unit tidak ditemukan / IS_USE != Y
    """

    unit = get_pegawai_unit(pegawai)

    if unit is None:
        return False

    return unit.IS_USE == 'Y'


# ============================================================
# PEGAWAI OPERASIONAL
# ============================================================

def is_operational_pegawai(pegawai):
    """
    Mengecek apakah pegawai termasuk populasi operasional HRIS.

    Syarat:

        IS_KELUAR = 'N'
        AND
        Unit Kerja IS_USE = 'Y'
    """

    if pegawai is None:
        return False

    return (
        is_pegawai_aktif(pegawai)
        and is_unit_pegawai_aktif(pegawai)
    )


def get_operational_pegawai_query():
    """
    Menghasilkan SQLAlchemy Query untuk Pegawai Operasional.

    Definisi:

        Pegawai.IS_KELUAR = 'N'
        AND
        MfUnitKerja.IS_USE = 'Y'

    Return:
        SQLAlchemy Query object

    Contoh:

        query = get_operational_pegawai_query()

        rows = (
            query
            .order_by(Pegawai.NAMA.asc())
            .all()
        )
    """

    return (
        Pegawai.query
        .join(
            MfUnitKerja,
            Pegawai.UNIT_KERJA_ID
            == MfUnitKerja.UNIT_KERJA_ID
        )
        .filter(
            Pegawai.IS_KELUAR == 'N',
            MfUnitKerja.IS_USE == 'Y'
        )
    )


def get_operational_pegawai_rows():
    """
    Mengambil seluruh Pegawai Operasional HRIS.

    Return:
        list[Pegawai]
    """

    return (
        get_operational_pegawai_query()
        .order_by(
            Pegawai.NAMA.asc(),
            Pegawai.NIP.asc()
        )
        .all()
    )


def get_operational_pegawai_nips():
    """
    Mengambil NIP seluruh Pegawai Operasional.

    Return:
        list[str]
    """

    return [
        str(pegawai.NIP)
        for pegawai in get_operational_pegawai_rows()
        if pegawai.NIP is not None
    ]


def get_operational_pegawai_count():
    """
    Mengambil jumlah Pegawai Operasional HRIS.

    Return:
        int
    """

    return get_operational_pegawai_query().count()


# ============================================================
# STATUS OPERASIONAL PEGAWAI
# ============================================================

def get_operational_status(pegawai):
    """
    Menghasilkan informasi status operasional pegawai.

    Return:

        {
            'is_pegawai_aktif': bool,
            'is_unit_aktif': bool,
            'is_operational': bool,
            'unit_kerja_id': str | None,
        }
    """

    if pegawai is None:
        return {
            'is_pegawai_aktif': False,
            'is_unit_aktif': False,
            'is_operational': False,
            'unit_kerja_id': None,
        }

    is_pegawai_aktif_value = is_pegawai_aktif(
        pegawai
    )

    is_unit_aktif_value = is_unit_pegawai_aktif(
        pegawai
    )

    return {
        'is_pegawai_aktif': is_pegawai_aktif_value,
        'is_unit_aktif': is_unit_aktif_value,
        'is_operational': (
            is_pegawai_aktif_value
            and is_unit_aktif_value
        ),
        'unit_kerja_id': (
            str(pegawai.UNIT_KERJA_ID)
            if pegawai.UNIT_KERJA_ID is not None
            else None
        ),
    }


# ============================================================
# AUTOCOMPLETE PEGAWAI
# ============================================================

def search_operational_pegawai(keyword, limit=15):
    """
    Pencarian Pegawai Operasional untuk autocomplete HRIS Reborn.

    Business Rule:

        Pegawai.IS_KELUAR = 'N'
        AND
        MfUnitKerja.IS_USE = 'Y'

    Standar pencarian:

        - Minimal 1 karakter
        - Case insensitive
        - Pencarian sebagian nama
        - Tidak harus mengetik nama dari awal
        - Menggunakan STANDARD PEGAWAI SORTING
        - Maksimal sesuai parameter limit

    Standard Sorting:

        1. Eselon
        2. Urut Jabatan
        3. Class Jabatan descending
        4. NIP ascending

    Return:
        list[Pegawai]
    """

    keyword = str(keyword or '').strip()

    if not keyword:
        return []

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 15

    if limit <= 0:
        limit = 15

    # Batas aman agar autocomplete tidak pernah
    # mengambil data terlalu banyak.
    limit = min(limit, 50)

    # ========================================================
    # FILTER PEGAWAI OPERASIONAL
    # ========================================================

    pegawai_rows = (
        Pegawai.query
        .join(
            MfUnitKerja,
            Pegawai.UNIT_KERJA_ID
            == MfUnitKerja.UNIT_KERJA_ID
        )
        .filter(
            Pegawai.IS_KELUAR == 'N',
            MfUnitKerja.IS_USE == 'Y',
            Pegawai.NAMA.ilike(f'%{keyword}%')
        )
        .all()
    )

    # ========================================================
    # STANDARD SORTING PEGAWAI
    #
    # Single Source of Sorting:
    #
    #   Eselon
    #   Urut Jabatan
    #   Class Jabatan DESC
    #   NIP ASC
    # ========================================================

    pegawai_rows = sort_pegawai_rows(
        pegawai_rows
    )

    # ========================================================
    # LIMIT DITERAPKAN SETELAH SORTING
    # ========================================================

    return pegawai_rows[:limit]


def search_operational_pegawai_data(keyword, limit=15):
    """
    Menghasilkan data sederhana untuk kebutuhan API autocomplete.

    Return:

        [
            {
                'nip': '...',
                'nama': '...'
            }
        ]

    Sumber jabatan resmi tetap MF_JABATAN dan akan
    ditambahkan pada endpoint yang membutuhkan jabatan.
    """

    pegawai_list = search_operational_pegawai(
        keyword,
        limit=limit
    )

    return [
        {
            'nip': pegawai.NIP,
            'nama': pegawai.NAMA or '',
        }
        for pegawai in pegawai_list
    ]

# ============================================================
# HRIS REBORN — UNIT KERJA AKTIF
# ============================================================

def get_active_unit_rows():
    """
    Mengambil Unit Kerja yang aktif digunakan HRIS.

    Business Rule:
        IS_AKTIF = 'Y' -> unit operasional
        IS_AKTIF = 'N' -> unit nonaktif / tidak ditampilkan
                       pada dropdown operasional.

    Master Unit Kerja TIDAK menggunakan helper ini karena
    Master Unit Kerja harus tetap dapat melihat unit aktif
    maupun nonaktif.
    """
    from app.models.unitKerjaModel import MfUnitKerja

    return (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_AKTIF == 'Y')
        .order_by(
            MfUnitKerja.URUT_REPORT.asc(),
            MfUnitKerja.NAMA_UNIT_KERJA.asc()
        )
        .all()
    )
