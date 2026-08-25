"""
Helper Report Rekap Absensi All HRIS Reborn

Layer:
    rekapAbsensiHelper
            |
            v
    rekapAbsensiReportHelper
            |
            v
    VIEW / EXCEL / PDF


Business Rule:

- PEGAWAI adalah sumber daftar personel.
- ABSENSI adalah sumber transaksi finger.
- FINGER_ID adalah connector absensi.
- Piket Siaga terpisah dari finger.
"""




from app.utils.absensiNormalisasiHelper import (
    merge_absensi_dinas_luar
)

def generate_rekap_absensi_report(
    data
):
    """
    Membuat data laporan Rekap Absensi.

    Parameter:
        data dari generate_rekap_absensi_all_data()

    Return:
        list dictionary siap VIEW/EXPORT
    """


    pegawai_rows = data.get(
        "pegawai",
        []
    )

    absensi_rows = data.get(
        "absensi",
        []
    )


    siaga_rows = data.get(
        "siaga",
        []
    )


    dinas_luar_rows = data.get(
        "dinas_luar",
        []
    )


    normalisasi_rows = merge_absensi_dinas_luar(
        pegawai_rows,
        absensi_rows,
        dinas_luar_rows,
        min(
            [
                a.TGL_KERJA
                for a, p in absensi_rows
            ],
            default=None
        ),
        max(
            [
                a.TGL_KERJA
                for a, p in absensi_rows
            ],
            default=None
        )
    )


    # ======================================
    # Index NORMALISASI berdasarkan NIP
    #
    # Sumber:
    #
    # ABSENSI
    # +
    # DINAS_LUAR
    #
    # sudah digabung oleh
    # merge_absensi_dinas_luar()
    # ======================================

    normalisasi_by_nip = {}

    for item in normalisasi_rows:

        nip = item["nip"]

        if nip not in normalisasi_by_nip:
            normalisasi_by_nip[nip] = []

        normalisasi_by_nip[nip].append(
            item
        )


    # ======================================
    # Index Siaga
    # ======================================

    siaga_by_nip = {}

    for siaga in siaga_rows:

        nip = (
            siaga.NIP or ''
        ).strip()

        if not nip:
            continue

        siaga_by_nip[nip] = (
            siaga_by_nip.get(
                nip,
                0
            )
            + 1
        )


    hasil = []


    # ======================================
    # Konversi NORMALISASI menjadi
    # struktur transaksi laporan
    #
    # Karena sebelumnya report memakai
    # object Absensi.
    #
    # Sekarang memakai dict normalisasi.
    # ======================================


    class NormalisasiAdapter:

        def __init__(self, item):

            self.item = item


            self.TRANSAKSI_IN = (
                item.get("label")
            )


            self.TINGKAT_TLM = (
                ""
            )


            self.PENDUKUNG_IN = (
                ""
            )


            self.TINGKAT_PSW = (
                ""
            )


            if item.get("sumber") == "DINAS_LUAR":

                self.TRANSAKSI_IN = (
                    "DinasLuar"
                )


                self.TINGKAT_TLM = (
                    item.get("label")
                )



    normalisasi_by_nip = {

        nip:
        [
            NormalisasiAdapter(x)
            for x in rows
        ]

        for nip, rows
        in normalisasi_by_nip.items()

    }



    # ======================================
    # Hitung per pegawai
    # ======================================

    for pegawai in pegawai_rows:

        nip = pegawai.NIP

        absensi_list = normalisasi_by_nip.get(
            nip,
            []
        )


        def count_transaksi(
            transaksi=None,
            tingkat=None,
            pendukung=None
        ):

            total = 0

            for a in absensi_list:

                if transaksi:

                    if (
                        (a.TRANSAKSI_IN or '').strip()
                        != transaksi
                    ):
                        continue


                if tingkat:

                    if (
                        (a.TINGKAT_TLM or '').strip()
                        != tingkat
                    ):
                        continue


                if pendukung:

                    if (
                        (a.PENDUKUNG_IN or '').strip()
                        != pendukung
                    ):
                        continue


                total += 1


            return total



        hasil.append({

            "nip":
                nip,

            "nama":
                pegawai.NAMA,


            "tlm1":
                count_transaksi(
                    tingkat="TLM-1"
                ),

            "tlm2":
                count_transaksi(
                    tingkat="TLM-2"
                ),

            "tlm3":
                count_transaksi(
                    tingkat="TLM-3"
                ),

            "tlm4":
                count_transaksi(
                    tingkat="TLM-4"
                ),


            "psw1":
                count_transaksi(
                    tingkat="PSW-1"
                ),

            "psw2":
                count_transaksi(
                    tingkat="PSW-2"
                ),

            "psw3":
                count_transaksi(
                    tingkat="PSW-3"
                ),

            "psw4":
                count_transaksi(
                    tingkat="PSW-4"
                ),


            "cuti":
                count_transaksi(
                    transaksi="Cuti",
                    tingkat="CT"
                ),


            "sakit":
                count_transaksi(
                    transaksi="Sakit",
                    tingkat="S-1"
                ),


            "alpa":
                count_transaksi(
                    transaksi="Alpa",
                    pendukung="Y"
                ),


            "alpa_tanpa_ket":
                count_transaksi(
                    transaksi="Alpa",
                    pendukung="N"
                ),


            "dl":
                count_transaksi(
                    transaksi="DinasLuar"
                ),


            "dl_op":
                count_transaksi(
                    transaksi="DinasLuar",
                    tingkat="DL OP"
                ),


            "dl_sd":
                count_transaksi(
                    transaksi="DinasLuar",
                    tingkat="DL SD"
                ),


            "siaga":
                siaga_by_nip.get(
                    nip,
                    0
                )

        })


    return hasil
