"""
Helper Dinas Luar HRIS Reborn

Sumber:
    DINAS_LUAR

Jenis:
    DL = Dinas Luar Umum
    OP = Dinas Luar Operasi
    SD = Dinas Luar Sumber Daya


Dipakai oleh:
    - Rekap Absensi
    - Uang Makan
    - Uang Harian Operasi SAR
"""


from app import db
from app.models.dinasLuarModel import DinasLuar
from app.models.pegawaiModel import Pegawai



def normalize_jenis_dinas_luar(value):

    value = (
        str(value or '')
        .strip()
        .upper()
    )

    mapping = {

        'DL':
            'DINAS LUAR UMUM',

        'OP':
            'DINAS LUAR OPERASI',

        'SD':
            'DINAS LUAR SUMBER DAYA',

        '-':
            'DINAS LUAR BELUM TERKATEGORI',

        '':
            'DINAS LUAR BELUM TERKATEGORI'
    }


    return mapping.get(
        value,
        'DINAS LUAR BELUM TERKATEGORI'
    )



def normalize_status_um(value):

    mapping = {

        0:
            'TIDAK TERPOTONG',

        1:
            'TERPOTONG',

        2:
            'TIDAK TERPOTONG PENEMPATAN'
    }


    return mapping.get(
        value,
        '-'
    )



def generate_dinas_luar_data(
    unit_ids,
    tgl_awal,
    tgl_akhir
):

    rows = (
        db.session.query(
            DinasLuar,
            Pegawai
        )
        .join(
            Pegawai,
            DinasLuar.FINGER_ID ==
            Pegawai.FINGER_ID
        )
        .filter(
            Pegawai.UNIT_KERJA_ID.in_(unit_ids)
        )
        .filter(
            DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_akhir
        )
        .filter(
            DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_awal
        )
        .all()
    )


    hasil = []


    for d, pegawai in rows:

        hasil.append({

            "nip":
                pegawai.NIP,

            "jenis":
                d.JENIS,

            "jenis_text":
                normalize_jenis_dinas_luar(
                    d.JENIS
                ),

            "tgl_awal":
                d.TGL_AWAL_DINAS_LUAR,

            "tgl_akhir":
                d.TGL_AKHIR_DINAS_LUAR,


            "no_surat":
                d.NO_SURAT,


            "penempatan":
                d.PENEMPATAN_DINAS_LUAR,


            "keterangan":
                d.KETERANGAN_DINAS_LUAR,


            "status_um":
                d.STATUS_UM,


            "status_um_text":
                normalize_status_um(
                    d.STATUS_UM
                ),


            "nama_file":
                d.NAMA_FILE

        })


    return hasil
