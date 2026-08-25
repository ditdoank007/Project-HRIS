"""
Helper Normalisasi Absensi HRIS Reborn

Business Rule:

ABSENSI adalah hasil normalisasi kehadiran.

Sumber:
- ABSENSI RAW
- DINAS_LUAR
- PEGAWAI

Connector:

ABSENSI.FingerID
        |
        v
PEGAWAI.FingerID


ABSENSI.TransaksiIDFrom
        |
        v
DINAS_LUAR.TransaksiID
"""


from datetime import timedelta

from app import db

from app.models.absensiModel import Absensi
from app.models.pegawaiModel import Pegawai
from app.models.dinasLuarModel import DinasLuar



def get_dinas_luar_detail(
    transaksi_id
):

    if not transaksi_id:
        return None


    return (
        DinasLuar.query
        .filter(
            DinasLuar.TRANSAKSI_ID == transaksi_id
        )
        .first()
    )



def get_label_dinas_luar(
    jenis
):

    mapping = {

        'DL':
            'DL',

        'OP':
            'DL OP',

        'SD':
            'DL SD'
    }


    return mapping.get(
        str(jenis or '').upper(),
        'DL'
    )



def get_warna_dinas_luar(
    status_um
):

    if status_um == 1:
        return "orange"


    if status_um in [0,2]:
        return "blue"


    return None


def generate_absensi_normalisasi(
    absensi_rows
):
    """
    Normalisasi data ABSENSI.

    Input:
        list object Absensi

    Output:
        list dictionary siap laporan

    Rule:

    1. Jika ABSENSI bukan DinasLuar
       -> tampilkan finger normal

    2. Jika ABSENSI DinasLuar:
       cek DINAS_LUAR

       StatusUM:
       
       1 :
           Memotong Uang Makan
           warna orange

       0 :
           Tidak Memotong Uang Makan
           warna blue

       2 :
           Tidak Memotong Uang Makan Penempatan
           warna blue
    """


    hasil = []


    for absensi in absensi_rows:


        item = {

            "finger_id":
                absensi.FINGER_ID,


            "tgl_kerja":
                absensi.TGL_KERJA,


            "jam_in":
                absensi.TGL_JAM_IN,


            "jam_out":
                absensi.TGL_JAM_OUT,


            "transaksi_in":
                absensi.TRANSAKSI_IN,


            "transaksi_out":
                absensi.TRANSAKSI_OUT,


            "label":
                "",


            "warna":
                "",


            "status_um":
                None,


            "wajib_finger":
                True,


            "keterangan_um":
                ""

        }


        # ==================================
        # Bukan Dinas Luar
        # ==================================

        if (
            (absensi.TRANSAKSI_IN or '')
            !=
            'DinasLuar'
        ):

            item["label"] = "HADIR"

            item["warna"] = "normal"


            hasil.append(item)

            continue



        # ==================================
        # Dinas Luar
        # ==================================

        dinas = get_dinas_luar_detail(
            absensi.TRANSAKSI_ID_FROM
        )


        if not dinas:

            item["label"] = "DINAS LUAR"

            item["warna"] = "blue"

            hasil.append(item)

            continue



        item["status_um"] = (
            dinas.STATUS_UM
        )


        item["wajib_finger"] = (
            get_kewajiban_finger(
                dinas.STATUS_UM
            )
        )


        item["label"] = (
            get_label_dinas_luar(
                dinas.JENIS
            )
        )


        item["warna"] = (
            get_warna_dinas_luar(
                dinas.STATUS_UM
            )
        )



        if dinas.STATUS_UM == 1:

            item["keterangan_um"] = (
                "Memotong Uang Makan"
            )


        elif dinas.STATUS_UM == 0:

            item["keterangan_um"] = (
                "Tidak Memotong Uang Makan"
            )


        elif dinas.STATUS_UM == 2:

            item["keterangan_um"] = (
                "Tidak Memotong Uang Makan Penempatan"
            )



        hasil.append(item)



    return hasil



def get_kewajiban_finger(
    status_um
):
    """
    Menentukan kewajiban finger.

    StatusUM:

    1:
        Terpotong Uang Makan
        Tidak wajib finger

    0:
        Tidak terpotong Uang Makan
        Wajib finger

    2:
        Tidak terpotong Uang Makan Penempatan
        Tidak wajib finger
    """


    if status_um == 0:

        return True


    if status_um in [1, 2]:

        return False


    return True



def merge_absensi_dinas_luar(
    pegawai_rows,
    absensi_rows,
    dinas_luar_rows,
    tgl_awal,
    tgl_akhir
):
    """
    Normalisasi final absensi HRIS Reborn.

    Prioritas:

    DINAS_LUAR
        >
    ABSENSI FINGER


    Connector:

    DINAS_LUAR.FingerID
            |
            v
    PEGAWAI.FingerID


    StatusUM:

    1:
        Memotong Uang Makan
        Tidak wajib finger
        Warna orange


    0:
        Tidak memotong Uang Makan
        Wajib finger
        Warna biru


    2:
        Tidak memotong Uang Makan Penempatan
        Tidak wajib finger
        Warna biru
    """


    hasil = []


    # =========================
    # INDEX PEGAWAI
    # =========================

    pegawai_by_finger = {

        p.FINGER_ID:
            p

        for p in pegawai_rows

    }



    # =========================
    # INDEX DINAS LUAR
    # =========================

    dl_index = {}


    for row in dinas_luar_rows:


        # SQLAlchemy Row / tuple support
        if hasattr(row, "_mapping"):

            values = list(
                row._mapping.values()
            )

            dl = values[0]

            if len(values) > 1:
                pegawai = values[1]

            else:
                pegawai = (
                    pegawai_by_finger.get(
                        dl.FINGER_ID
                    )
                )


        elif isinstance(row, tuple):

            dl, pegawai = row


        else:

            dl = row

            pegawai = (
                pegawai_by_finger.get(
                    dl.FINGER_ID
                )
            )


        if not pegawai:
            continue


        if not pegawai:
            continue


        tanggal = (
            dl.TGL_AWAL_DINAS_LUAR.date()
        )


        while tanggal <= dl.TGL_AKHIR_DINAS_LUAR.date():


            dl_index[
                (
                    pegawai.NIP,
                    tanggal
                )
            ] = dl


            tanggal += timedelta(
                days=1
            )



    # =========================
    # INDEX FINGER
    # =========================

    finger_index = {}


    for row in absensi_rows:

        # Support:
        #
        # (Absensi, Pegawai)
        #
        # atau
        #
        # (Absensi, Pegawai, UnitKerja)
        #

        absensi = row[0]
        pegawai = row[1]


        finger_index[
            (
                pegawai.NIP,
                absensi.TGL_KERJA.date()
            )
        ] = absensi



    # =========================
    # BUILD NORMALISASI
    # =========================

    tanggal = tgl_awal


    while tanggal <= tgl_akhir:


        for pegawai in pegawai_rows:


            key = (

                pegawai.NIP,

                tanggal.date()

            )


            dl = dl_index.get(key)

            finger = finger_index.get(key)



            item = {

                "nip":
                    pegawai.NIP,

                "nama":
                    pegawai.NAMA,

                "tanggal":
                    tanggal,

                "label":
                    "",

                "warna":
                    "",

                "status_um":
                    None,

                "wajib_finger":
                    True,

                "jam_in":
                    None,

                "jam_out":
                    None,

                "sumber":
                    ""

            }



            if dl:


                item["label"] = (
                    get_label_dinas_luar(
                        dl.JENIS
                    )
                )


                item["warna"] = (
                    get_warna_dinas_luar(
                        dl.STATUS_UM
                    )
                )


                item["status_um"] = (
                    dl.STATUS_UM
                )


                item["wajib_finger"] = (
                    get_kewajiban_finger(
                        dl.STATUS_UM
                    )
                )


                item["sumber"] = (
                    "DINAS_LUAR"
                )



            elif finger:


                item["jam_in"] = (
                    finger.TGL_JAM_IN
                )


                item["jam_out"] = (
                    finger.TGL_JAM_OUT
                )


                item["label"] = (
                    "HADIR"
                )


                item["warna"] = (
                    "normal"
                )


                item["sumber"] = (
                    "ABSENSI"
                )



            else:


                item["label"] = (
                    "TIDAK ADA DATA"
                )


                item["sumber"] = (
                    "NONE"
                )



            hasil.append(
                item
            )



        tanggal += timedelta(
            days=1
        )



    return hasil

