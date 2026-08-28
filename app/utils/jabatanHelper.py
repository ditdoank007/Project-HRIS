"""
HRIS REBORN
Standard Employee Seniority & Sorting Helper

Single Source of Business Rule untuk menentukan urutan senioritas
pegawai HRIS Reborn.

PRIORITAS SORTING:

1. Eselon
2. Class Jabatan
3. Golongan
4. Tahun Penerimaan
5. Tahun Lahir
6. Tanggal Lahir
7. Nama
8. NIP

CATATAN:

- JABATAN_ID adalah kodefikasi hirarki jabatan,
  BUKAN ranking senioritas.
- Untuk non-eselon, Class Jabatan menjadi prioritas utama.
- Golongan menggunakan MF_GOL.URUTAN.
  Nilai URUTAN semakin kecil = golongan semakin tinggi.
- ASN/PNS:
    TMTCPNS -> tahun penerimaan utama.
    Jika tidak tersedia -> fallback dari NIP.
- Non-ASN:
    tahun penerimaan diambil dari 4 digit pertama
    NIP/FINGER_ID.
- Tahun lahir menggunakan TGL_LAHIR jika tersedia.
  Jika tidak tersedia -> fallback 8 digit pertama NIP.
"""

from datetime import date, datetime


# ============================================================
# SAFE CONVERTER
# ============================================================

def _safe_int(value, default=999999):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# KATEGORI JABATAN
# ============================================================

def get_kategori_jabatan(pegawai):
    """
    Kelompok jabatan HRIS Reborn.

    1 = STRUKTURAL
    2 = FUNGSIONAL
    3 = FUNGSIONAL UMUM

    Untuk sorting senioritas:
    Struktural lebih dahulu.
    Non-eselon kemudian berdasarkan class.
    """

    eselon = str(
        getattr(pegawai, 'ESELON', '') or ''
    ).strip()

    class_id = _safe_int(
        getattr(pegawai, 'CLASS_ID', 0),
        0
    )

    if eselon in ('1', '2', '3', '4'):
        return 1

    if class_id >= 8:
        return 2

    return 3


# ============================================================
# URUT ESELON
# ============================================================

def get_urut_eselon(pegawai):
    """
    Semakin kecil semakin tinggi.

    Eselon 1 -> 1
    Eselon 2 -> 2
    Eselon 3 -> 3
    Eselon 4 -> 4
    Non-eselon -> 99
    """

    mapping = {
        '1': 1,
        '2': 2,
        '3': 3,
        '4': 4,
    }

    return mapping.get(
        str(getattr(pegawai, 'ESELON', '') or '').strip(),
        99
    )


# ============================================================
# CLASS JABATAN
# ============================================================

def get_urut_class(pegawai):
    """
    Class jabatan semakin besar = semakin tinggi.

    Sorting ascending menggunakan nilai negatif,
    sehingga Class 10 berada di atas Class 9.
    """

    class_id = _safe_int(
        getattr(pegawai, 'CLASS_ID', 0),
        0
    )

    return -class_id


# ============================================================
# GOLONGAN
# ============================================================

def get_urut_golongan(pegawai, golongan_map=None):
    """
    Mengambil ranking golongan dari MF_GOL.URUTAN.

    Contoh:

        IV/e = 0
        IV/d = 1
        IV/c = 2
        IV/b = 3
        IV/a = 4

        III/d = 5
        III/c = 6
        III/b = 7
        III/a = 8

    Semakin kecil URUTAN = semakin tinggi golongan.
    """

    gol = str(
        getattr(pegawai, 'GOL', '') or ''
    ).strip()

    if not gol:
        return 999999

    if golongan_map is not None:
        return golongan_map.get(gol, 999999)

    try:
        from app.models.golonganModel import MfGolongan

        row = (
            MfGolongan.query
            .filter(MfGolongan.GOL == gol)
            .first()
        )

        if row and row.URUTAN is not None:
            return row.URUTAN

    except Exception:
        pass

    return 999999


# ============================================================
# EXTRACT YEAR
# ============================================================

def _extract_year_from_value(value):
    """
    Mengambil tahun YYYY dari date/datetime/string.
    """

    if value is None:
        return None

    if isinstance(value, (datetime, date)):
        return value.year

    text = str(value).strip()

    if len(text) >= 4 and text[:4].isdigit():
        year = int(text[:4])

        if 1900 <= year <= 2100:
            return year

    return None


def _extract_year_from_nip(nip):
    """
    Mengambil tahun dari 4 digit pertama NIP/FINGER_ID.
    """

    if not nip:
        return None

    text = str(nip).strip()

    if len(text) < 4:
        return None

    prefix = text[:4]

    if not prefix.isdigit():
        return None

    year = int(prefix)

    if 1900 <= year <= 2100:
        return year

    return None


# ============================================================
# TAHUN PENERIMAAN
# ============================================================

def get_tahun_penerimaan(pegawai):
    """
    Menentukan tahun penerimaan pegawai.

    ASN/PNS:

        1. TMTCPNS
        2. Tahun CPNS dari NIP posisi 9-12

    Non-ASN:

        1. Empat digit pertama FINGER_ID/NIP

    Jika tidak tersedia:
        999999
    """

    # --------------------------------------------------------
    # 1. TMT CPNS
    # --------------------------------------------------------

    tmt_cpns = getattr(
        pegawai,
        'TMTCPNS',
        None
    )

    year = _extract_year_from_value(tmt_cpns)

    if year is not None:
        return year

    # --------------------------------------------------------
    # 2. NIP ASN
    #
    # Format:
    #
    # YYYYMMDD YYYYMMDD NNNN
    #          ^
    #          tahun CPNS
    # --------------------------------------------------------

    nip = getattr(
        pegawai,
        'NIP',
        None
    )

    finger_id = getattr(
        pegawai,
        'FINGER_ID',
        None
    )

    identifier = str(
        nip or finger_id or ''
    ).strip()

    if len(identifier) >= 18 and identifier.isdigit():

        cpns_year = identifier[8:12]

        if cpns_year.isdigit():

            year = int(cpns_year)

            if 1900 <= year <= 2100:
                return year

    # --------------------------------------------------------
    # 3. NON-ASN
    #
    # FINGER_ID/NIP:
    #
    # 20155006
    # ^^^^
    # 2015 = tahun penerimaan
    # --------------------------------------------------------

    year = _extract_year_from_nip(
        finger_id or nip
    )

    if year is not None:
        return year

    return 999999


# ============================================================
# TAHUN LAHIR
# ============================================================

def get_tahun_lahir(pegawai):
    """
    Tahun lahir utama menggunakan TGL_LAHIR.

    Jika kosong:
        fallback ke 4 digit pertama NIP.
    """

    tgl_lahir = getattr(
        pegawai,
        'TGL_LAHIR',
        None
    )

    year = _extract_year_from_value(tgl_lahir)

    if year is not None:
        return year

    nip = getattr(
        pegawai,
        'NIP',
        None
    )

    if nip:

        text = str(nip).strip()

        if len(text) >= 8 and text[:8].isdigit():

            year = int(text[:4])

            if 1900 <= year <= 2100:
                return year

    return 999999


# ============================================================
# TANGGAL LAHIR
# ============================================================

def get_tanggal_lahir(pegawai):
    """
    Jika tahun lahir sama,
    pegawai yang lahir lebih dahulu berada di atas.
    """

    tgl_lahir = getattr(
        pegawai,
        'TGL_LAHIR',
        None
    )

    if isinstance(tgl_lahir, datetime):
        return tgl_lahir.date()

    if isinstance(tgl_lahir, date):
        return tgl_lahir

    return date.max


# ============================================================
# NAMA
# ============================================================

def get_nama_sort(pegawai):
    """
    Sorting nama secara case-insensitive.
    """

    return str(
        getattr(pegawai, 'NAMA', '') or ''
    ).strip().upper()


# ============================================================
# NIP
# ============================================================

def get_nip_sort(pegawai):
    """
    Tie-breaker terakhir.
    """

    return str(
        getattr(pegawai, 'NIP', '') or ''
    ).strip()


# ============================================================
# FINAL SORT KEY
# ============================================================

def pegawai_sort_key(pegawai, golongan_map=None):
    """
    Standard sorting key HRIS Reborn.

    PRIORITAS:

    1. Eselon
    2. Class Jabatan
    3. Golongan
    4. Tahun Penerimaan
    5. Tahun Lahir
    6. Tanggal Lahir
    7. Nama
    8. NIP

    JABATAN_ID tidak digunakan sebagai ranking senioritas.
    """

    return (
        # 1. ESELON
        get_urut_eselon(pegawai),

        # 2. CLASS JABATAN
        get_urut_class(pegawai),

        # 3. GOLONGAN
        get_urut_golongan(
            pegawai,
            golongan_map=golongan_map
        ),

        # 4. TAHUN PENERIMAAN
        get_tahun_penerimaan(pegawai),

        # 5. TAHUN LAHIR
        get_tahun_lahir(pegawai),

        # 6. TANGGAL LAHIR
        get_tanggal_lahir(pegawai),

        # 7. NAMA
        get_nama_sort(pegawai),

        # 8. NIP
        get_nip_sort(pegawai),
    )
