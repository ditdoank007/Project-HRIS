"""
Helper Business Rule Jabatan HRIS Reborn

Hirarki ASN:

1. Jabatan Struktural
   Eselon 1 - 4

2. Jabatan Fungsional
   Class Jabatan tinggi tanpa eselon

3. Jabatan Fungsional Umum
   Class Jabatan rendah

Dipakai untuk:
- Sorting pegawai
- Rekap absensi
- Daftar pegawai
- Laporan HRIS
"""


def get_kategori_jabatan(pegawai):
    """
    Menentukan kelompok jabatan.

    Return:
        1 = STRUKTURAL
        2 = FUNGSIONAL
        3 = FUNGSIONAL UMUM
    """

    eselon = str(
        pegawai.ESELON or ''
    ).strip()

    class_id = (
        pegawai.CLASS_ID or 0
    )


    # ==========================
    # STRUKTURAL
    # ==========================

    if eselon in (
        '1',
        '2',
        '3',
        '4'
    ):
        return 1


    # ==========================
    # FUNGSIONAL
    #
    # Non eselon dengan class
    # jabatan di atas umum
    # ==========================

    if class_id >= 8:
        return 2


    # ==========================
    # FUNGSIONAL UMUM
    # ==========================

    return 3



def get_urut_eselon(pegawai):
    """
    Semakin kecil semakin tinggi.
    """

    mapping = {
        '1': 1,
        '2': 2,
        '3': 3,
        '4': 4,
    }

    return mapping.get(
        str(pegawai.ESELON or '').strip(),
        99
    )



def get_tanggal_lahir_nip(nip):
    """
    Ambil YYYYMMDD dari NIP.

    Contoh:
    198008292010121001

    menjadi:
    19800829
    """

    if not nip:
        return '99999999'

    nip = str(nip)

    if len(nip) < 8:
        return '99999999'

    return nip[:8]



def pegawai_sort_key(pegawai):
    """
    Sorting HRIS Reborn.

    Prioritas:

    1. Kelompok jabatan
       Struktural
       Fungsional
       Fungsional Umum

    2. Eselon

    3. Class Jabatan

    4. Usia berdasarkan NIP

    5. Nama

    6. Finger ID
    """

    kategori = get_kategori_jabatan(
        pegawai
    )

    return (

        # kelompok jabatan
        kategori,


        # eselon
        get_urut_eselon(
            pegawai
        ),


        # class terbesar dahulu
        -(pegawai.CLASS_ID or 0),


        # lahir lebih tua dahulu
        get_tanggal_lahir_nip(
            pegawai.NIP
        ),


        # nama
        pegawai.NAMA or '',


        # finger
        pegawai.FINGER_ID or ''

    )
