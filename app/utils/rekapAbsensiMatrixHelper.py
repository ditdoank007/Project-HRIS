"""
Matrix Rekap Absensi Bulanan HRIS Reborn.

Business source:
    HRIS 2013 RDailyAbsensi.aspx.vb

Output:
    satu baris per pegawai
    satu kolom per tanggal
    IN/OUT atau kode status per hari.

Layer:
    KALENDER -> ABSENSI -> SIAGA -> SPRIN/DINAS LUAR
    SPRIN menjadi layer tertinggi untuk kasus yang overlap dengan Siaga.
"""

from app import db
from datetime import timedelta, datetime

from app.models.pegawaiModel import Pegawai
from app.models.absensiModel import Absensi
from app.models.dinasLuarModel import DinasLuar
from app.models.kalenderModel import MfKalender
from app.models.jabatanModel import MfJabatan
from app.models.eselonModel import MfEselon
from app.models.golonganModel import MfGolongan
from app.models.logActivityModel import LogActivity

from app.utils.pegawaiHelper import is_pegawai_aktif_periode
from app.utils.pegawaiSortHelper import sort_pegawai_rows


def format_jam_absensi(value):
    if not value:
        return ""
    if (
        hasattr(value, "year")
        and value.year == 1900
        and value.month == 1
        and value.day == 1
    ):
        return ""
    return value.strftime("%H.%M")


def format_status_absensi(status):
    mapping = {
        "DINAS_LUAR": "DL",
        "CUTI": "CT",
        "SAKIT": "S",
        "IJIN": "I",
        "IZIN": "I",
        "ALPA": "A",
        "WFH": "WFH",
    }
    if not status:
        return ""
    return mapping.get(str(status).upper(), str(status))


def _calendar_rows(tgl_awal, tgl_akhir):
    rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA >= tgl_awal)
        .filter(MfKalender.TGL_KERJA <= tgl_akhir)
        .order_by(MfKalender.TGL_KERJA.asc())
        .all()
    )

    # Sama seperti RDailyAbsensi: bila Kalender kosong, fallback
    # Senin-Jumat = kerja, Sabtu-Minggu = libur.
    if rows:
        return rows

    generated = []
    d = tgl_awal
    while d <= tgl_akhir:
        generated.append(type("CalendarRow", (), {
            "TGL_KERJA": d,
            "IS_LIBUR": "Y" if d.weekday() >= 5 else "N",
            "KET": None,
        })())
        d += timedelta(days=1)
    return generated


def _is_holiday(row):
    d = row.TGL_KERJA
    if d.weekday() in (5, 6):
        return True
    if str(row.IS_LIBUR or "N").upper() == "Y":
        return True
    if d.strftime("%m-%d") in ("01-01", "08-17", "12-25"):
        return True
    return False


def _active_pegawai(unit_ids, tgl_awal, tgl_akhir):
    rows = (
        Pegawai.query
        .outerjoin(MfJabatan, Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID)
        .outerjoin(MfEselon, Pegawai.ESELON == MfEselon.ESELON)
        .outerjoin(MfGolongan, Pegawai.GOL == MfGolongan.GOL)
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(Pegawai.TGL_MASUK <= tgl_akhir)
        .all()
    )
    rows = [
        p for p in rows
        if is_pegawai_aktif_periode(p, tgl_awal, tgl_akhir)
    ]
    return sort_pegawai_rows(rows)


def generate_rekap_absensi_matrix(unit_ids, tgl_awal, tgl_akhir):
    kalender_rows = _calendar_rows(tgl_awal, tgl_akhir)
    pegawai_rows = _active_pegawai(unit_ids, tgl_awal, tgl_akhir)

    absensi_rows = (
        db.session.query(Absensi, Pegawai)
        .join(Pegawai, Absensi.FINGER_ID == Pegawai.FINGER_ID)
        .filter(Absensi.TGL_KERJA >= tgl_awal)
        .filter(Absensi.TGL_KERJA <= tgl_akhir)
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .all()
    )

    dinas_luar_rows = (
        db.session.query(DinasLuar, Pegawai)
        .join(Pegawai, DinasLuar.FINGER_ID == Pegawai.FINGER_ID)
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_akhir)
        .filter(DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_awal)
        .filter(DinasLuar.TRANSAKSI == "DinasLuar")
        .all()
    )

    # Siaga: ambil kedua shift seperti RDailyAbsensi.
    siaga_rows = (
        LogActivity.query
        .filter(LogActivity.ACTIVITY == "Piket Siaga")
        .filter(LogActivity.STATUS_ID == 3)
        .filter(LogActivity.STATUS_TRX == "-")
        .filter(LogActivity.SHIFT.in_(["1", "2"]))
        .filter(LogActivity.ACTIVITY_DATE >= (tgl_awal - timedelta(days=1)))
        .filter(LogActivity.ACTIVITY_DATE <= tgl_akhir)
        .all()
    )

    absensi_index = {}
    for absensi, pegawai in absensi_rows:
        if not absensi.TGL_KERJA:
            continue
        absensi_index[(pegawai.NIP, absensi.TGL_KERJA.date())] = absensi

    dl_index = {}
    for dl, pegawai in dinas_luar_rows:
        if not dl.TGL_AWAL_DINAS_LUAR or not dl.TGL_AKHIR_DINAS_LUAR:
            continue
        start = dl.TGL_AWAL_DINAS_LUAR.date()
        end = dl.TGL_AKHIR_DINAS_LUAR.date()
        d = max(start, tgl_awal.date())
        while d <= min(end, tgl_akhir.date()):
            # Jika ada lebih dari satu record, record yang paling baru
            # diutamakan; data input SPRIN menjadi sumber kebenaran.
            key = (pegawai.NIP, d)
            current = dl_index.get(key)
            if current is None:
                dl_index[key] = dl
            else:
                current_date = getattr(current, "UPDATE_DATE", None)
                new_date = getattr(dl, "UPDATE_DATE", None)
                if new_date and (not current_date or new_date > current_date):
                    dl_index[key] = dl
            d += timedelta(days=1)

    siaga_index = {}
    for row in siaga_rows:
        if not row.NIP or not row.ACTIVITY_DATE:
            continue
        activity_date = row.ACTIVITY_DATE.date() if hasattr(row.ACTIVITY_DATE, "date") else row.ACTIVITY_DATE
        siaga_index[(str(row.NIP), activity_date)] = str(row.SHIFT or "1")

    matrix = {}

    for pegawai in pegawai_rows:
        matrix[pegawai.NIP] = {}

        for kalender in kalender_rows:
            tanggal_obj = kalender.TGL_KERJA
            tanggal = tanggal_obj.strftime("%Y-%m-%d")
            key = (pegawai.NIP, tanggal_obj.date())

            # Default RDailyAbsensi: hari kerja tanpa ABSENSI tidak diberi
            # label ALPA di rekap. Cell dibiarkan kosong.
            matrix[pegawai.NIP][tanggal] = {
                "status": "LIBUR" if _is_holiday(kalender) else "",
                "jam_in": None,
                "jam_out": None,
                "keterangan": kalender.KET or "",
                "sumber_absensi": "",
                "warna": "holiday" if _is_holiday(kalender) else "",
                "layer": "KALENDER",
                "status_um": None,
                "siaga_shift": None,
            }

            finger = absensi_index.get(key)
            dl = dl_index.get(key)
            siaga_shift = siaga_index.get(key)

            # ---------------------------------------------------------
            # BASE ABSENSI
            # ---------------------------------------------------------
            if finger:
                transaksi_in = str(finger.TRANSAKSI_IN or "").strip().upper()
                transaksi_out = str(finger.TRANSAKSI_OUT or "").strip().upper()

                is_online_wfh = (
                    transaksi_in == "WFH"
                    or transaksi_out == "WFH"
                    or str(finger.KET_IN or "").strip().upper() == "ABSEN ONLINE WFH"
                    or str(finger.KET_OUT or "").strip().upper() == "ABSEN ONLINE WFH"
                )

                if transaksi_in in ("CUTI", "SAKIT", "ALPA", "IJIN", "IZIN"):
                    status = format_status_absensi(transaksi_in)
                    color = "orange"
                elif is_online_wfh:
                    status = "HADIR"
                    color = "wfh"
                else:
                    status = "HADIR"
                    color = "normal"

                matrix[pegawai.NIP][tanggal].update({
                    "status": status,
                    "jam_in": finger.TGL_JAM_IN,
                    "jam_out": finger.TGL_JAM_OUT,
                    "sumber_absensi": "ONLINE_WFH" if is_online_wfh else "FINGER",
                    "warna": color,
                    "layer": "ABSENSI",
                })

            # ---------------------------------------------------------
            # SIAGA
            # ---------------------------------------------------------
            # Sama seperti RDailyAbsensi: Siaga memberi warna hijau pada
            # hasil absensi yang ada. Jika belum ada absensi, tidak
            # menciptakan jam fiktif.
            if siaga_shift:
                cell = matrix[pegawai.NIP][tanggal]
                cell["siaga_shift"] = siaga_shift
                if not dl:
                    if cell["status"] not in ("LIBUR", "CT", "S", "A", "I"):
                        cell["warna"] = "siaga"
                        cell["layer"] = "SIAGA"

            # ---------------------------------------------------------
            # SPRIN / DINAS LUAR = LAYER TERTINGGI
            # ---------------------------------------------------------
            if dl:
                status_um = int(dl.STATUS_UM or 0)
                label = format_status_absensi(dl.JENIS)

                if status_um == 1:
                    # Memotong Uang Makan:
                    # tidak menampilkan jam aktual, tampil kode orange.
                    cell = matrix[pegawai.NIP][tanggal]
                    cell.update({
                        "status": label,
                        "jam_in": None,
                        "jam_out": None,
                        "sumber_absensi": "DINAS_LUAR",
                        "warna": "orange",
                        "layer": "SPRIN",
                        "status_um": 1,
                    })

                elif status_um == 2:
                    # Tidak memotong Uang Makan Penempatan:
                    # tidak wajib finger, tampil kode blue.
                    cell = matrix[pegawai.NIP][tanggal]
                    cell.update({
                        "status": label,
                        "jam_in": None,
                        "jam_out": None,
                        "sumber_absensi": "DINAS_LUAR",
                        "warna": "blue",
                        "layer": "SPRIN",
                        "status_um": 2,
                    })

                else:
                    # Tidak memotong Uang Makan:
                    # wajib finger. Jika finger ada, tampilkan actual IN/OUT.
                    # Jika tidak ada finger, jangan membuat jam fiktif.
                    cell = matrix[pegawai.NIP][tanggal]
                    finger = absensi_index.get(key)
                    cell.update({
                        "status": "HADIR" if finger else "",
                        "jam_in": finger.TGL_JAM_IN if finger else None,
                        "jam_out": finger.TGL_JAM_OUT if finger else None,
                        "sumber_absensi": "DINAS_LUAR",
                        "warna": "blue",
                        "layer": "SPRIN",
                        "status_um": 0,
                    })

    return {
        "kalender": kalender_rows,
        "pegawai": pegawai_rows,
        "matrix": matrix,
    }
