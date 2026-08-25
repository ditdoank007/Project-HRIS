"""
Helper Matrix Rekap Absensi All HRIS Reborn

Sumber:
    PEGAWAI
    ABSENSI
    DINAS_LUAR
    KALENDER

Dipakai oleh:
    VIEW DATA
    EXPORT
    PDF
"""

from app import db

from datetime import timedelta

from app.models.pegawaiModel import Pegawai
from app.models.absensiModel import Absensi
from app.models.dinasLuarModel import DinasLuar
from app.models.kalenderModel import MfKalender
from app.models.jabatanModel import MfJabatan
from app.models.eselonModel import MfEselon
from app.models.golonganModel import MfGolongan

from app.utils.pegawaiHelper import (
    is_pegawai_aktif_periode
)

from app.utils.pegawaiSortHelper import sort_pegawai_rows

from app.utils.absensiNormalisasiHelper import (
    merge_absensi_dinas_luar
)



def format_jam_absensi(value):
    """
    Format jam absensi HRIS.

    Input:
        datetime

    Output:
        HH.MM

    Contoh:
        07.28
        16.50
    """

    if not value:
        return ""


    # Legacy sentinel
    # 1900-01-01 dianggap kosong

    if (
        hasattr(value, "year")
        and value.year == 1900
        and value.month == 1
        and value.day == 1
    ):
        return ""


    return value.strftime(
        "%H.%M"
    )



def format_status_absensi(status):
    """
    Standarisasi label absensi.
    """

    mapping = {

        "DINAS_LUAR": "DL",

        "CUTI": "CT",

        "SAKIT": "S",

        "IJIN": "I",

        "IZIN": "I",

        "WFH": "WFH",

        "OPS": "OPS",

        "SPRIN": "SD",

        "ALPA": "A",

    }


    if not status:
        return ""


    return mapping.get(
        status.upper(),
        status
    )



def render_absensi_cell(data):
    """
    Renderer satu cell tanggal.

    Output:

    HADIR:
        07.28
        16.50

    Status:
        DL

    """

    if not data:
        return (
            "",
            ""
        )


    status = format_status_absensi(
        data.get("status")
    )


    if status not in (
        "",
        "HADIR"
    ):

        return (
            status,
            ""
        )


    jam_in = format_jam_absensi(
        data.get("jam_in")
    )

    jam_out = format_jam_absensi(
        data.get("jam_out")
    )


    return (
        jam_in,
        jam_out
    )



def generate_rekap_absensi_matrix(
    unit_ids,
    tgl_awal,
    tgl_akhir
):
    """
    Generate matriks absensi pegawai x tanggal.
    """

    # ==============================
    # KALENDER
    # ==============================

    kalender_rows = (
        MfKalender.query
        .filter(
            MfKalender.TGL_KERJA >= tgl_awal
        )
        .filter(
            MfKalender.TGL_KERJA <= tgl_akhir
        )
        .order_by(
            MfKalender.TGL_KERJA.asc()
        )
        .all()
    )


    # ==============================
    # PEGAWAI
    # ==============================

    pegawai_rows = (
        Pegawai.query
        .outerjoin(
            MfJabatan,
            Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID
        )
        .outerjoin(
            MfEselon,
            Pegawai.ESELON == MfEselon.ESELON
        )
        .outerjoin(
            MfGolongan,
            Pegawai.GOL == MfGolongan.GOL
        )
        .filter(
            Pegawai.UNIT_KERJA_ID.in_(unit_ids)
        )
        .filter(
            Pegawai.TGL_MASUK <= tgl_akhir
        )
        .all()
    )


    # ==============================
    # PEGAWAI UNIVERSE PERIODE
    #
    # Pegawai yang mempunyai
    # hubungan kerja pada periode laporan
    # ==============================

    def normalize_date(value):

        if not value:
            return None


        value_str = str(value)


        # Legacy zero date
        # 0000-00-00 dianggap kosong

        if value_str.startswith(
            '0000-00-00'
        ):
            return None


        if hasattr(value, 'date'):
            return value


        try:
            from datetime import datetime

            return datetime.strptime(
                value_str,
                '%Y-%m-%d'
            )

        except Exception:

            return None



    pegawai_rows = [

        p for p in pegawai_rows

        if (

            normalize_date(
                p.TGL_MASUK
            )

            and

            normalize_date(
                p.TGL_MASUK
            ) <= tgl_akhir

        )

        and

        (

            not normalize_date(
                p.TGL_KELUAR
            )

            or

            normalize_date(
                p.TGL_KELUAR
            ) >= tgl_awal

        )

    ]


    # ==============================
    # SORTING LAPORAN REKAP ABSENSI
    #
    # Central Rule:
    # pegawaiSortHelper.py
    #
    # Urutan:
    # 1. Eselon
    # 2. Urut Jabatan
    # 3. Class Jabatan DESC
    # 4. NIP ASC
    # ==============================

    pegawai_rows = sort_pegawai_rows(
        pegawai_rows
    )



    # ==============================

    pegawai_rows = sorted(
        pegawai_rows,
        key=lambda p: (

            (
                int(p.ESELON)
                if str(p.ESELON).isdigit()
                else 99
            ),

            (
                getattr(
                    p,
                    'URUT_JABATAN',
                    999999
                )
                if getattr(
                    p,
                    'URUT_JABATAN',
                    None
                )
                else 999999
            ),

            -(
                p.CLASS_ID or 0
            ),

            p.NIP or ''
        )
    )


    # ==============================
    # ABSENSI FINGER
    # ==============================

    absensi_rows = (
        db.session.query(
            Absensi,
            Pegawai
        )
        .join(
            Pegawai,
            Absensi.FINGER_ID == Pegawai.FINGER_ID
        )
        .filter(
            Absensi.TGL_KERJA >= tgl_awal
        )
        .filter(
            Absensi.TGL_KERJA <= tgl_akhir
        )
        .filter(
            Pegawai.UNIT_KERJA_ID.in_(unit_ids)
        )
        .all()
    )


    # ==============================
    # DINAS LUAR
    # ==============================

    dinas_luar_rows = (
        db.session.query(
            DinasLuar,
            Pegawai
        )
        .join(
            Pegawai,
            DinasLuar.FINGER_ID == Pegawai.FINGER_ID
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


    # ==============================
    # MATRIX PEGAWAI x TANGGAL
    # ==============================

    matrix = {}

    for pegawai in pegawai_rows:

        matrix[pegawai.NIP] = {}

        for kalender in kalender_rows:

            tanggal = (
                kalender.TGL_KERJA.strftime("%Y-%m-%d")
            )

            # Default status berdasarkan kalender
            #
            # KERJA :
            #   status = ALPA
            #
            # LIBUR :
            #   status = LIBUR
            #
            # WFH :
            #   IS_LIBUR = N
            #   KET = WFH
            #   status = WFH
            #
            # Keterangan kalender tetap dibawa
            # agar frontend dapat membedakan:
            # Sabtu, Minggu, Libur Nasional,
            # Libur Khusus, dan WFH.

            kalender_ket = (
                kalender.KET
                if kalender.KET
                else None
            )

            kalender_is_libur = (
                (kalender.IS_LIBUR or 'N').upper()
                == 'Y'
            )

            if kalender_is_libur:

                status = "LIBUR"

            elif (
                str(kalender_ket or '').upper()
                == "WFH"
            ):

                status = "WFH"

            else:

                status = "ALPA"


            matrix[pegawai.NIP][tanggal] = {

                "status": status,

                "jam_in": None,

                "jam_out": None,

                "keterangan": kalender_ket

            }


    # ==============================
    # ABSENSI FINGER MASUK MATRIX
    # ==============================

    for absensi, pegawai in absensi_rows:

        tanggal = (
            absensi.TGL_KERJA.strftime("%Y-%m-%d")
        )

        if pegawai.NIP not in matrix:
            continue

        current_cell = (
            matrix[pegawai.NIP]
            .get(tanggal, {})
        )

        current_status = (
            current_cell.get("status")
        )

        if current_status == "WFH":

            status = "WFH"

        else:

            status = "HADIR"


        matrix[pegawai.NIP][tanggal] = {

            "status": status,

            "jam_in":
                absensi.TGL_JAM_IN,

            "jam_out":
                absensi.TGL_JAM_OUT,

            "keterangan":
                current_cell.get("keterangan")

        }


    # ==============================
    # DINAS LUAR PRIORITAS
    # ==============================

    for dl, pegawai in dinas_luar_rows:

        if pegawai.NIP not in matrix:
            continue


        tanggal = dl.TGL_AWAL_DINAS_LUAR

        while tanggal <= dl.TGL_AKHIR_DINAS_LUAR:

            key = tanggal.strftime(
                "%Y-%m-%d"
            )

            if key in matrix[pegawai.NIP]:

                matrix[pegawai.NIP][key] = {

                    "status": "DL",

                    "jam_in": None,

                    "jam_out": None,

                    "keterangan": "Dinas Luar"

                }

            tanggal += timedelta(days=1)


    return {

        "kalender": kalender_rows,

        "pegawai": pegawai_rows,

        "matrix": matrix

    }
