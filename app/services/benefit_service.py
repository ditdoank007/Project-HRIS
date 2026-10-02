"""
Personal Benefit engine.

Tunjangan Kinerja / Uang Makan mengikuti alur data HRIS Reborn
dan legacy MyTunkin/MyUM. Uang Siaga mengikuti formula TTUPiket
HRIS 2013, tetapi hasilnya difilter hanya untuk NIP yang login.
"""

from calendar import monthrange
from datetime import date, datetime, timedelta

from sqlalchemy import text

from app import db
from app.models.absensiModel import Absensi
from app.models.classModel import MfClass
from app.models.dinasLuarModel import DinasLuar
from app.models.kalenderModel import MfKalender
from app.models.logActivityModel import LogActivity
from app.models.orgzSiagaModel import MfOrgzSiaga
from app.models.pegawaiModel import Pegawai
from app.models.potModel import MfPot
from app.models.tunjanganModel import MfTunjangan


def _d(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _parse(value):
    if isinstance(value, (date, datetime)):
        return _d(value)
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _month_add(value, months):
    index = value.year * 12 + value.month - 1 + months
    year, month0 = divmod(index, 12)
    return date(year, month0 + 1, min(
        value.day, monthrange(year, month0 + 1)[1]
    ))


def _employee(nip):
    return Pegawai.query.filter(Pegawai.NIP == str(nip).strip()).first()


def _active(pegawai, start, end):
    if not pegawai:
        return False
    join = _d(pegawai.TGL_MASUK)
    leave = _d(pegawai.TGL_KELUAR)
    if join and join > end:
        return False
    if str(pegawai.IS_KELUAR or "").upper() == "Y" and leave and leave < start:
        return False
    return True


def _calendar(start, end):
    rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA >= start)
        .filter(MfKalender.TGL_KERJA <= end)
        .order_by(MfKalender.TGL_KERJA.asc())
        .all()
    )
    return {_d(row.TGL_KERJA): row for row in rows if _d(row.TGL_KERJA)}


def _holiday(day, cal):
    row = cal.get(day)
    return (
        str(row.IS_LIBUR or "N").upper() == "Y"
        if row else day.weekday() >= 5
    )


def _latest_class(class_id, effective):
    if class_id is None:
        return 0.0
    row = (
        MfClass.query
        .filter(MfClass.CLASS_ID == class_id)
        .filter(MfClass.TGL_MULAI <= effective)
        .order_by(MfClass.TGL_MULAI.desc(), MfClass.ID.desc())
        .first()
    )
    return float(row.TUNJANGAN or 0) if row else 0.0


def _latest_pot(kategori, effective):
    row = (
        MfPot.query
        .filter(MfPot.KATEGORI == kategori)
        .filter(MfPot.TGL_MULAI <= effective)
        .order_by(MfPot.TGL_MULAI.desc(), MfPot.POTONGAN_ID.desc())
        .first()
    )
    return float(row.PERSEN_POT or 0) if row else 0.0


def calculate_tunjangan_kinerja(nip, start, end):
    start, requested_end = _parse(start), _parse(end)
    if start > requested_end:
        raise ValueError("Tanggal mulai tidak boleh lebih besar dari tanggal selesai.")

    pegawai = _employee(nip)
    if not _active(pegawai, start, requested_end):
        return {"status": "success", "data": None,
                "message": "Pegawai tidak aktif pada periode tersebut."}

    effective_end = min(requested_end, date.today())
    if effective_end < start:
        return {"status": "success", "data": {
            "requested_period": {"start": start.isoformat(), "end": requested_end.isoformat()},
            "effective_period": None, "tunjangan": 0, "persen_potongan": 0,
            "nilai_potongan": 0, "total_diterima": 0, "detail": []
        }}

    cal = _calendar(start, effective_end)
    absensi = (
        Absensi.query
        .filter(Absensi.FINGER_ID == pegawai.FINGER_ID)
        .filter(Absensi.TGL_KERJA >= start)
        .filter(Absensi.TGL_KERJA <= effective_end)
        .order_by(Absensi.TGL_KERJA.asc())
        .all()
    )
    abs_by_date = {}
    for row in absensi:
        day = _d(row.TGL_KERJA)
        if day and day not in abs_by_date:
            abs_by_date[day] = row

    dl_rows = (
        DinasLuar.query
        .filter(DinasLuar.FINGER_ID == pegawai.FINGER_ID)
        .filter(DinasLuar.TGL_AWAL_DINAS_LUAR <= effective_end)
        .filter(DinasLuar.TGL_AKHIR_DINAS_LUAR >= start)
        .all()
    )

    allowance = _latest_class(pegawai.CLASS_ID, effective_end)
    pot_ta = _latest_pot("TA", effective_end)
    pot_dl = _latest_pot("DINASLUAR", effective_end)

    detail = []
    total_percent = 0.0
    day = start

    while day <= effective_end:
        item = {
            "tanggal": day.isoformat(), "ta": 0,
            "tlm_tingkat": "", "tlm_persen": 0,
            "psw_tingkat": "", "psw_persen": 0,
            "dinas_luar": 0, "cuti_tingkat": "", "cuti_persen": 0,
            "sakit_tingkat": "", "sakit_persen": 0, "ijin": 0,
            "potongan_persen": 0, "hari_libur": _holiday(day, cal),
            "keterangan": ""
        }

        if not item["hari_libur"]:
            row = abs_by_date.get(day)
            if not row:
                item["ta"] = 1
                item["potongan_persen"] = pot_ta
                item["keterangan"] = "TA"
            else:
                trx = str(row.TRANSAKSI_IN or "").strip().upper()
                if trx == "DINASLUAR":
                    item["dinas_luar"] = 1
                    item["keterangan"] = row.KET_IN or "Dinas Luar"
                elif trx == "CUTI":
                    level = str(row.TINGKAT_TLM or "").strip().upper()
                    pct = float(row.PERSEN_POT_TLM or 0)
                    item.update(cuti_tingkat=level, cuti_persen=pct,
                                potongan_persen=pct, keterangan=row.KET_IN or level)
                elif trx == "SAKIT":
                    level = str(row.TINGKAT_TLM or "").strip().upper()
                    pct = float(row.PERSEN_POT_TLM or 0)
                    item.update(sakit_tingkat=level, sakit_persen=pct,
                                potongan_persen=pct,
                                keterangan=((row.KET_IN or "") + " " + (row.KET_OUT or "")).strip())
                elif trx == "ALPA":
                    # MyTunkin legacy displays ALPA in the IJIN column.
                    item["ijin"] = 1
                    item["keterangan"] = ((row.KET_IN or "") + " " + (row.KET_OUT or "")).strip()
                else:
                    tlm = str(row.TINGKAT_TLM or "").strip().upper()
                    psw = str(row.TINGKAT_PSW or "").strip().upper()
                    tlm_pct = float(row.PERSEN_POT_TLM or 0)
                    psw_pct = float(row.PERSEN_POT_PSW or 0)
                    item.update(tlm_tingkat=tlm, tlm_persen=tlm_pct,
                                psw_tingkat=psw, psw_persen=psw_pct,
                                potongan_persen=tlm_pct + psw_pct,
                                keterangan=((row.KET_IN or "") + " " + (row.KET_OUT or "")).strip())

            for dl in dl_rows:
                dl_start, dl_end = _d(dl.TGL_AWAL_DINAS_LUAR), _d(dl.TGL_AKHIR_DINAS_LUAR)
                if dl_start and dl_end and dl_start <= day <= dl_end and _month_add(dl_start, 4) <= day:
                    item["potongan_persen"] += pot_dl
                    item["keterangan"] = ((item["keterangan"] + " + ") if item["keterangan"] else "") + "DL > 4 bulan"
                    break

        total_percent += float(item["potongan_persen"] or 0)
        detail.append(item)
        day += timedelta(days=1)

    deduction = allowance * total_percent / 100 if total_percent else 0
    return {"status": "success", "data": {
        "nip": str(pegawai.NIP), "nama": str(pegawai.NAMA or ""),
        "class_id": pegawai.CLASS_ID,
        "requested_period": {"start": start.isoformat(), "end": requested_end.isoformat()},
        "effective_period": {"start": start.isoformat(), "end": effective_end.isoformat()},
        "tunjangan": round(allowance, 2),
        "persen_potongan": round(total_percent, 4),
        "nilai_potongan": round(deduction, 2),
        "total_diterima": round(allowance - deduction, 2),
        "detail": detail
    }}


def calculate_uang_makan(nip, year, month):
    """
    Calculate personal Uang Makan using the legacy HRIS 2013 MyUM logic.

    Legacy source of truth (MyUM.aspx.vb):
      - period = selected month, capped by SQL Server current date
      - KALENDER rows with IsLibur='N' are the workdays
      - employee workdays begin after TglMasuk when TglMasuk is inside period
      - ABSENSI is the source for DinasLuar/Cuti/Sakit/Alpa
      - DinasLuar counts only TransaksiIn='DinasLuar' and StatusUM=1
      - Cuti/Sakit are classified by TingkatTLM
      - Alpa with PendukungIN='Y' is counted as Alpa/Ijin
      - Alpa with PendukungIN='N', plus missing attendance rows, becomes TA
      - UM = payable days * latest MFTunjangan Nominal where JenisTunjangan='U.makan'

    HRIS-Pegawai adaptation:
      only records belonging to the logged-in NIP are returned.
    """
    year, month = int(year), int(month)
    start = date(year, month, 1)
    end = (
        date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        - timedelta(days=1)
    )
    effective_end = min(end, date.today())

    pegawai = _employee(nip)
    if not _active(pegawai, start, effective_end):
        return {
            "status": "success",
            "data": None,
            "message": "Pegawai tidak aktif pada periode tersebut.",
        }

    cal = _calendar(start, effective_end)

    # MyUM selects only calendar rows where IsLibur='N'.
    workdays = [
        d for d in sorted(cal)
        if str(cal[d].IS_LIBUR or "").strip().upper() == "N"
    ]

    # MyUM:
    #   if TglMasuk > period start:
    #       calendar dates are selected with Tgl > TglMasuk
    #   else:
    #       all workdays in the period are counted.
    join = _d(pegawai.TGL_MASUK)
    if join and join > start:
        employee_days = [d for d in workdays if d > join]
    else:
        employee_days = list(workdays)

    # Master Uang Makan HRIS Reborn:
    #   1. hanya U.Makan + Intern + HariKerja=0
    #   2. pilih record yang sudah berlaku pada akhir periode
    #   3. cocokkan Fungsional dengan level golongan pegawai
    #   4. fallback ke legacy Fungsional='All'
    #   5. IDTunjangan menjadi identitas master yang benar-benar dipakai
    def _golongan_level(value):
        raw = str(value or "").strip().upper()
        if not raw:
            return None
        raw = raw.replace("GOLONGAN", "").replace("GOL.", "").strip()
        level = raw.split("/", 1)[0].strip()
        return {"2": "II", "3": "III", "4": "IV"}.get(level, level)

    master_rows = (
        MfTunjangan.query
        .filter(db.func.lower(MfTunjangan.JENIS_TUNJANGAN) == "u.makan")
        .filter(db.func.lower(MfTunjangan.ACTIVITY) == "intern")
        .filter(MfTunjangan.HARI_KERJA == 0)
        .filter(MfTunjangan.TGL_MULAI <= effective_end)
        .order_by(
            MfTunjangan.TGL_MULAI.desc(),
            MfTunjangan.IDTUNJANGAN.desc()
        )
        .all()
    )

    employee_golongan = _golongan_level(pegawai.GOL_ID)
    master_uang_makan = None

    if employee_golongan:
        for item in master_rows:
            if _golongan_level(item.FUNGSIONAL) == employee_golongan:
                master_uang_makan = item
                break

    if master_uang_makan is None:
        for item in master_rows:
            if str(item.FUNGSIONAL or "").strip().upper() == "ALL":
                master_uang_makan = item
                break

    nominal = float(master_uang_makan.NOMINAL or 0) if master_uang_makan else 0.0
    master_tunjangan_id = (
        int(master_uang_makan.IDTUNJANGAN)
        if master_uang_makan and master_uang_makan.IDTUNJANGAN is not None
        else None
    )

    # MyUM joins ABSENSI to KALENDER and keeps only workday attendance.
    # Keep one row per date, matching the legacy monthly counting model.
    abs_rows = (
        Absensi.query
        .filter(Absensi.FINGER_ID == pegawai.FINGER_ID)
        .filter(Absensi.TGL_KERJA >= start)
        .filter(Absensi.TGL_KERJA <= effective_end)
        .order_by(Absensi.TGL_KERJA.asc())
        .all()
    )
    abs_by_date = {}
    for row in abs_rows:
        d = _d(row.TGL_KERJA)
        if d in employee_days and d not in abs_by_date:
            abs_by_date[d] = row

    # Exact MyUM category counters.
    cuti = {
        x: 0 for x in ("CT", "CB-1", "CB-2", "CB-3", "CAP-M2", "CAP")
    }
    sakit = {
        x: 0 for x in ("S-1", "S-2", "S-3", "S-4", "S-5")
    }
    dinas_luar = 0
    alpa = 0
    alpa_tanpa_keterangan = 0

    for row in abs_by_date.values():
        trx = str(row.TRANSAKSI_IN or "").strip().upper()
        level = str(row.TINGKAT_TLM or "").strip().upper()

        if trx == "DINASLUAR" and row.STATUS_UM == 1:
            dinas_luar += 1
        elif trx == "CUTI" and level in cuti:
            cuti[level] += 1
        elif trx == "SAKIT" and level in sakit:
            sakit[level] += 1
        elif trx == "ALPA":
            if str(row.PENDUKUNG_IN or "").strip().upper() == "Y":
                alpa += 1
            else:
                alpa_tanpa_keterangan += 1

    cuti_total = sum(cuti.values())
    sakit_total = sum(sakit.values())

    # Legacy MyUM:
    # xAlpaTanpaKet = xAlpaA + (xnTglKerja - attendance_row_count)
    # TA is then this same value.
    missing_attendance = max(0, len(employee_days) - len(abs_by_date))
    ta = alpa_tanpa_keterangan + missing_attendance

    # Legacy final payable-day formula:
    # Periode - Cuti - Sakit - DinasLuar - TA - Alpa
    um_days = max(
        0,
        len(employee_days)
        - cuti_total
        - sakit_total
        - dinas_luar
        - ta
        - alpa,
    )

    detail = []
    for d in employee_days:
        row = abs_by_date.get(d)
        if not row:
            detail.append({
                "tanggal": d.isoformat(),
                "status": "TA",
                "kategori": "TA",
                "keterangan": "Tidak ada absensi",
            })
            continue

        trx = str(row.TRANSAKSI_IN or "").strip().upper()
        level = str(row.TINGKAT_TLM or "").strip().upper()

        if trx == "DINASLUAR" and row.STATUS_UM == 1:
            kategori = "Dinas Luar"
            keterangan = row.KET_IN or "Dinas Luar"
        elif trx == "CUTI" and level in cuti:
            kategori = level
            keterangan = row.KET_IN or level
        elif trx == "SAKIT" and level in sakit:
            kategori = level
            keterangan = row.KET_IN or level
        elif trx == "ALPA" and str(row.PENDUKUNG_IN or "").strip().upper() == "Y":
            kategori = "Alpa"
            keterangan = row.KET_IN or "Alpa"
        elif trx == "ALPA":
            kategori = "TA"
            keterangan = row.KET_IN or "Alpa tanpa keterangan"
        else:
            kategori = "Hadir"
            keterangan = row.KET_IN or "Hadir"

        detail.append({
            "tanggal": d.isoformat(),
            "status": "Hadir" if kategori == "Hadir" else kategori,
            "kategori": kategori,
            "keterangan": keterangan,
        })

    return {
        "status": "success",
        "data": {
            "nip": str(pegawai.NIP),
            "nama": str(pegawai.NAMA or ""),
            "year": year,
            "month": month,
            "requested_period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "effective_period": {
                "start": start.isoformat(),
                "end": effective_end.isoformat(),
            },
            "golongan": employee_golongan or "-",
            "id_tunjangan": master_tunjangan_id,
            "nominal_per_hari": round(nominal, 2),
            "hari_kerja": len(employee_days),
            "dinas_luar": dinas_luar,
            "cuti": cuti_total,
            "cuti_detail": cuti,
            "ijin": alpa,
            "alpa": alpa,
            "sakit": sakit_total,
            "sakit_detail": sakit,
            "tidak_absen": ta,
            "ta": ta,
            "um_hari": um_days,
            "nominal": round(um_days * nominal, 2),
            "detail": detail,
        },
    }


def calculate_uang_siaga(nip, year, month):
    """
    Calculate personal Uang Siaga using the legacy HRIS 2013 TTUPiket
    calculation as the business source of truth.

    Legacy flow:
      LOG_ACTIVITIY -> PEGAWAI -> MF_ORGZ_SIAGA -> KALENDER -> MF_TUNJANGAN
      Activity='piket siaga'
      StatusID=3
      Shift IS NOT NULL
      nominal selected by workday/holiday, TglMulai, Flag, Unit, Shift,
      and StatusPeg
      Brutto = (Shift1 + Shift2) * Nominal
      PPh21 = 0 for Gol I/II, otherwise 5%
      Netto = Brutto - PPh21

    HRIS-Pegawai adaptation:
      only records belonging to the logged-in NIP are returned.
    """
    year, month = int(year), int(month)
    start = date(year, month, 1)
    end = date(
        year + (month == 12),
        1 if month == 12 else month + 1,
        1,
    ) - timedelta(days=1)

    pegawai = _employee(nip)
    if not _active(pegawai, start, end):
        return {
            "status": "success",
            "data": None,
            "message": "Pegawai tidak aktif pada periode tersebut.",
        }

    cal = _calendar(start, end)

    # LOG_ACTIVITIY has no physical ID column in the migrated HRIS database.
    # Therefore this query intentionally uses SQLAlchemy Core instead of the
    # current ORM model, while preserving the legacy TTUPiket join/filter.
    sql = text(
        """
        SELECT
            la.NIP AS nip,
            la.Activity AS activity,
            la.ActivityDate AS activity_date,
            la.Fungsional AS fungsional,
            la.IDUnitKerja AS unit_kerja_id,
            la.shift1 AS shift_1,
            la.shift2 AS shift_2,
            la.Shift AS shift,
            os.Flag AS flag,
            p.Gol AS gol,
            p.StatusPeg AS status_peg
        FROM LOG_ACTIVITIY la
        INNER JOIN PEGAWAI p
            ON la.NIP = p.NIP
        INNER JOIN MF_ORGZ_SIAGA os
            ON la.Fungsional = os.Fungsional
        WHERE la.NIP = :nip
          AND LOWER(la.Activity) = 'piket siaga'
          AND la.StatusID = 3
          AND la.ActivityDate >= :start_date
          AND la.ActivityDate <= :end_date
          AND la.Shift IS NOT NULL
        ORDER BY la.ActivityDate ASC
        """
    )

    rows = db.session.execute(
        sql,
        {
            "nip": str(pegawai.NIP),
            "start_date": start,
            "end_date": end,
        },
    ).mappings().all()

    excluded_gol = {
        "",
        "I/A", "I/B", "I/C", "I/D",
        "II/A", "II/B", "II/C", "II/D",
    }

    detail = []
    work_count = 0
    holiday_count = 0

    for log in rows:
        d = _d(log["activity_date"])
        if not d:
            continue

        calendar_row = cal.get(d)

        # TTUPiket uses KALENDER.IsLibur directly. There is no weekend
        # fallback in the legacy calculation. Missing calendar rows therefore
        # follow the legacy CASE ELSE branch (HariKerja=0).
        is_holiday = (
            str(calendar_row.IS_LIBUR or "").strip().upper() != "N"
            if calendar_row
            else True
        )

        if is_holiday:
            holiday_count += 1
        else:
            work_count += 1

        hari_kerja = 0 if is_holiday else 1
        shift = str(log["shift"] or "").strip()
        flag = log["flag"]

        master_query = (
            MfTunjangan.query
            .filter(
                db.func.lower(MfTunjangan.JENIS_TUNJANGAN)
                == "u.transport"
            )
            .filter(MfTunjangan.ACTIVITY == "Piket Siaga")
            .filter(MfTunjangan.HARI_KERJA == hari_kerja)
            .filter(MfTunjangan.TGL_MULAI <= d)
            .filter(MfTunjangan.FUNGSIONAL == flag)
            .filter(
                MfTunjangan.ID_UNIT_KERJA
                == str(log["unit_kerja_id"])
            )
            .filter(MfTunjangan.SHIFT == shift)
            .filter(MfTunjangan.STATUS_PEG == log["status_peg"])
        )

        # Preserve TTUPiket ordering:
        # - workday: TglMulai DESC
        # - holiday: TglMulai DESC, UpdateDate DESC
        if hari_kerja == 1:
            master = (
                master_query
                .order_by(MfTunjangan.TGL_MULAI.desc())
                .first()
            )
        else:
            master = (
                master_query
                .order_by(
                    MfTunjangan.TGL_MULAI.desc(),
                    MfTunjangan.UPDATE_DATE.desc(),
                )
                .first()
            )

        nominal = float(master.NOMINAL or 0) if master else 0.0
        shift1 = float(log["shift_1"] or 0)
        shift2 = float(log["shift_2"] or 0)

        brutto = (shift1 * nominal) + (shift2 * nominal)

        gol = str(log["gol"] or "").strip().upper()
        pph21 = 0.0 if gol in excluded_gol else brutto * 0.05
        netto = brutto - pph21

        detail.append({
            "tanggal": d.isoformat(),
            "shift": shift,
            "fungsional": str(log["fungsional"] or ""),
            "flag": str(flag or ""),
            "hari_kerja": hari_kerja == 1,
            "status": "Hadir",
            "shift1": shift1,
            "shift2": shift2,
            "nominal": round(nominal, 2),
            "brutto": round(brutto, 2),
            "pph21": round(pph21, 2),
            "netto": round(netto, 2),
            "keterangan": (
                "Hari Libur" if is_holiday else "Hari Kerja"
            ),
        })

    return {
        "status": "success",
        "data": {
            "nip": str(pegawai.NIP),
            "nama": str(pegawai.NAMA or ""),
            "year": year,
            "month": month,
            "requested_period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "effective_period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "jumlah_siaga_piket": len(detail),
            "hari_kerja": int(work_count),
            "hari_libur": int(holiday_count),
            "total_brutto": round(
                sum(item["brutto"] for item in detail), 2
            ),
            "total_pph21": round(
                sum(item["pph21"] for item in detail), 2
            ),
            "total_uang_siaga": round(
                sum(item["netto"] for item in detail), 2
            ),
            "detail": detail,
        },
    }

