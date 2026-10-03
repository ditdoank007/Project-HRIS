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
from sqlalchemy import bindparam, text

from app.models.pegawaiModel import Pegawai
from app.models.absensiModel import Absensi
from app.models.dinasLuarModel import DinasLuar
from app.models.kalenderModel import MfKalender
from app.models.jabatanModel import MfJabatan
from app.models.eselonModel import MfEselon
from app.models.golonganModel import MfGolongan

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


def _is_vip(pegawai):
    value = getattr(pegawai, "IS_VIP", None)
    return str(value or "").strip().upper() in ("Y", "1", "TRUE")


def _legacy_vip_jam(actual, baku, is_vip, arah):
    """
    Reproduce the active VIP display rule from HRIS 2013 RDailyAbsensi.
    This changes only the displayed/reporting time; raw ABSENSI remains untouched.
    """
    if not is_vip or not actual or not baku:
        return actual

    actual_minutes = actual.hour * 60 + actual.minute
    baku_minutes = baku.hour * 60 + baku.minute

    if arah == "IN" and actual <= baku:
        return actual
    if arah == "OUT" and actual >= baku:
        return actual

    diff = baku_minutes - actual_minutes
    sql_remainder = diff - int(diff / 11) * 11

    if arah == "IN":
        delta_minutes = sql_remainder - 1
    else:
        delta_minutes = sql_remainder + 1

    return baku + timedelta(minutes=delta_minutes)


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

    # Siaga dibaca dengan SQL langsung karena tabel hasil migrasi
    # menggunakan nama kolom fisik legacy-mapped (GUIDLog, ActivityDate,
    # StatusID, IDUnitKerja, dll), bukan nama atribut ORM lama.
    siaga_sql = text("""
        SELECT
            NIP,
            ActivityDate,
            Shift
        FROM LOG_ACTIVITIY
        WHERE Activity = :activity
          AND StatusID = :status_id
          AND StatusTrx = :status_trx
          AND Shift IN ('1', '2')
          AND ActivityDate >= :activity_awal
          AND ActivityDate <= :activity_akhir
          AND IDUnitKerja IN :unit_ids
    """).bindparams(bindparam("unit_ids", expanding=True))

    siaga_rows = db.session.execute(
        siaga_sql,
        {
            "activity": "Piket Siaga",
            "status_id": 3,
            "status_trx": "-",
            "activity_awal": (tgl_awal - timedelta(days=1)).date(),
            "activity_akhir": tgl_akhir.date(),
            "unit_ids": [str(x) for x in unit_ids],
        },
    ).mappings().all()

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
        # Karena hasil SQL diambil sebagai MappingResult, gunakan nama
        # kolom fisik database, bukan atribut ORM lama.
        nip = row.get("NIP")
        activity_date_value = row.get("ActivityDate")
        if not nip or not activity_date_value:
            continue
        activity_date = (
            activity_date_value.date()
            if hasattr(activity_date_value, "date")
            else activity_date_value
        )
        shift = str(row.get("Shift") or "1")
        # HRIS 2013: shift 2 tercatat pada tanggal H-1 untuk
        # kehadiran yang direkap pada tanggal H.
        report_date = (
            activity_date + timedelta(days=1)
            if shift == "2"
            else activity_date
        )
        siaga_index[(str(nip), report_date)] = shift

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

                jam_in_report = _legacy_vip_jam(
                    finger.TGL_JAM_IN,
                    finger.TGL_JAM_BAKU_IN,
                    _is_vip(pegawai),
                    "IN",
                )
                jam_out_report = _legacy_vip_jam(
                    finger.TGL_JAM_OUT,
                    finger.TGL_JAM_BAKU_OUT,
                    _is_vip(pegawai),
                    "OUT",
                )

                matrix[pegawai.NIP][tanggal].update({
                    "status": status,
                    "jam_in": jam_in_report,
                    "jam_out": jam_out_report,
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
                        "jam_in": (
                            _legacy_vip_jam(
                                finger.TGL_JAM_IN,
                                finger.TGL_JAM_BAKU_IN,
                                _is_vip(pegawai),
                                "IN",
                            )
                            if finger else None
                        ),
                        "jam_out": (
                            _legacy_vip_jam(
                                finger.TGL_JAM_OUT,
                                finger.TGL_JAM_BAKU_OUT,
                                _is_vip(pegawai),
                                "OUT",
                            )
                            if finger else None
                        ),
                        "sumber_absensi": "DINAS_LUAR",
                        "warna": "blue",
                        "layer": "SPRIN",
                        "status_um": 0,
                    })

            # HRIS 2013 menerapkan warna hari libur setelah seluruh
            # resolusi absensi/Siaga/DL selesai.
            if _is_holiday(kalender):
                matrix[pegawai.NIP][tanggal]["warna"] = "holiday"

    return {
        "kalender": kalender_rows,
        "pegawai": pegawai_rows,
        "matrix": matrix,
    }
