# app/services/attendance_rules.py

from datetime import datetime, timedelta


def _minutes(delta):
    """Konversi timedelta menjadi menit."""
    return delta.total_seconds() / 60


def _build_datetime(tanggal, value):
    """
    Menggabungkan tanggal kerja dengan time/datetime master.
    """
    if value is None:
        return None

    if hasattr(value, "time"):
        value = value.time()

    return datetime.combine(tanggal, value)


def _normalize_cross_midnight(jam_in_baku, jam_out_baku):
    """
    Jika jam OUT <= jam IN, berarti shift melewati tengah malam.
    """
    if (
        jam_in_baku
        and jam_out_baku
        and jam_out_baku <= jam_in_baku
    ):
        return jam_out_baku + timedelta(days=1)

    return jam_out_baku


def _classify_tlm(total_tlm):
    if total_tlm <= 0:
        return "", 0

    if total_tlm <= 30:
        return "TLM-1", 0.5

    if total_tlm <= 60:
        return "TLM-2", 1

    if total_tlm <= 90:
        return "TLM-3", 1.25

    return "TLM-4", 1.5


def _classify_psw(total_psw):
    """
    total_psw bernilai negatif apabila pulang sebelum
    jam baku.

    Contoh:
        -15 -> PSW-1
        -45 -> PSW-2
    """
    if total_psw >= 0:
        return "", 0

    psw = abs(total_psw)

    if psw <= 30:
        return "PSW-1", 0.5

    if psw <= 60:
        return "PSW-2", 1

    if psw <= 90:
        return "PSW-3", 1.25

    return "PSW-4", 1.5


def calculate_tlm_psw(
    jam_in,
    jam_out,
    jam_baku_in,
    jam_baku_out,
    is_libur=False,
    penggantian_tlm1=True,
):
    """
    Attendance Rule Engine.

    Aturan dasar:

    1. TLM dihitung dari:
           JAM_IN - JAM_BAKU_IN

    2. PSW dihitung dari:
           JAM_OUT - JAM_BAKU_OUT

       Positif  = pulang setelah jam baku
       Negatif  = pulang sebelum jam baku

    3. TLM-1 dapat digantikan oleh kelebihan waktu pulang
       apabila penggantian_tlm1 aktif.

    4. Hari libur tidak menghasilkan potongan TLM/PSW.

    5. Shift lintas tengah malam didukung oleh engine.
    """

    # ---------------------------------------------------------
    # DATA TIDAK LENGKAP
    # ---------------------------------------------------------

    if not jam_in and not jam_out:
        return {
            "awal_tlm": 0,
            "total_tlm": 0,
            "tingkat_tlm": "",
            "persen_pot_tlm": 0,
            "total_psw": 0,
            "tingkat_psw": "",
            "persen_pot_psw": 0,
        }

    # ---------------------------------------------------------
    # TLM
    # ---------------------------------------------------------

    awal_tlm = 0

    if jam_in and jam_baku_in:
        awal_tlm = max(
            0,
            _minutes(jam_in - jam_baku_in)
        )

    # ---------------------------------------------------------
    # PSW
    # ---------------------------------------------------------

    total_psw = 0

    if jam_out and jam_baku_out:
        total_psw = _minutes(
            jam_out - jam_baku_out
        )

    # ---------------------------------------------------------
    # TLM PENGGANTIAN
    #
    # Contoh:
    #
    # Baku IN  : 08:00
    # Aktual IN: 08:15
    # Baku OUT : 16:00
    # Aktual OUT:16:20
    #
    # Awal TLM = 15
    # PSW      = +20
    #
    # TLM akhir = 15 - 20 = 0
    # ---------------------------------------------------------

    total_tlm = awal_tlm

    if (
        not is_libur
        and penggantian_tlm1
        and 0 < awal_tlm <= 30
        and total_psw > 0
    ):
        total_tlm = max(
            0,
            awal_tlm - total_psw
        )

    # ---------------------------------------------------------
    # HARI LIBUR
    # ---------------------------------------------------------

    if is_libur:
        return {
            "awal_tlm": round(awal_tlm, 2),
            "total_tlm": 0,
            "tingkat_tlm": "",
            "persen_pot_tlm": 0,
            "total_psw": round(total_psw, 2),
            "tingkat_psw": "",
            "persen_pot_psw": 0,
        }

    # ---------------------------------------------------------
    # KLASIFIKASI
    # ---------------------------------------------------------

    tingkat_tlm, persen_pot_tlm = _classify_tlm(
        total_tlm
    )

    tingkat_psw, persen_pot_psw = _classify_psw(
        total_psw
    )

    return {
        "awal_tlm": round(awal_tlm, 2),
        "total_tlm": round(total_tlm, 2),
        "tingkat_tlm": tingkat_tlm,
        "persen_pot_tlm": persen_pot_tlm,

        "total_psw": round(total_psw, 2),
        "tingkat_psw": tingkat_psw,
        "persen_pot_psw": persen_pot_psw,
    }


def build_work_schedule(
    tanggal,
    std_jam_in,
    std_jam_out,
):
    """
    Membentuk jam kerja aktual berdasarkan tanggal kerja.

    Mendukung:

        07:30 -> 16:00
        19:30 -> 04:00
        20:00 -> 03:30

    Untuk shift malam, JAM_BAKU_OUT otomatis masuk
    ke hari berikutnya.
    """

    jam_baku_in = _build_datetime(
        tanggal,
        std_jam_in,
    )

    jam_baku_out = _build_datetime(
        tanggal,
        std_jam_out,
    )

    jam_baku_out = _normalize_cross_midnight(
        jam_baku_in,
        jam_baku_out,
    )

    return jam_baku_in, jam_baku_out
