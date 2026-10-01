"""Uang Siaga V2 - isolated legacy-compatible calculation engine.

This module intentionally does not replace the existing benefit engine yet.

Business source:
    HRIS 2013 TTUPiket.aspx.vb

Migration adaptation:
    HRIS 2013 selects LOG_ACTIVITIY rows with StatusID='3'. Each selected
    row carries shift1/shift2 quantities; those values are multiplied by the
    tariff selected using Shift. Shift is the tariff selector, not the
    payment quantity.

    V2 deliberately follows this legacy rule exactly. Any mismatch caused
    by migrated source data is surfaced as a data-parity issue rather than
    compensated for in the calculation engine.

No database writes are performed.
"""

from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text

from app import db


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _month_period(year, month):
    year = int(year)
    month = int(month)
    if month < 1 or month > 12:
        raise ValueError("Bulan tidak valid.")

    start = date(year, month, 1)
    end = date(
        year + (month == 12),
        1 if month == 12 else month + 1,
        1,
    ) - timedelta(days=1)
    return start, end


def _employee(nip):
    return db.session.execute(
        text("""
            SELECT
                NIP,
                Nama,
                Gol,
                StatusPeg,
                TglMasuk,
                Tglkeluar,
                isKeluar
            FROM PEGAWAI
            WHERE NIP = :nip
            LIMIT 1
        """),
        {"nip": str(nip).strip()},
    ).mappings().first()


def _active(employee, start, end):
    if not employee:
        return False

    join = _as_date(employee["TglMasuk"])
    leave = _as_date(employee["Tglkeluar"])

    if join and join > end:
        return False

    if (
        str(employee["isKeluar"] or "").strip().upper() == "Y"
        and leave
        and leave < start
    ):
        return False

    return True


def _calendar(start, end):
    rows = db.session.execute(
        text("""
            SELECT Tgl, IsLibur
            FROM KALENDER
            WHERE Tgl >= :start_date
              AND Tgl <= :end_date
            ORDER BY Tgl
        """),
        {
            "start_date": start,
            "end_date": end,
        },
    ).mappings().all()

    return {
        _as_date(row["Tgl"]): row
        for row in rows
        if _as_date(row["Tgl"])
    }


def _tariff(activity_date, is_holiday, flag, unit_id, shift, status_peg):
    hari_kerja = 0 if is_holiday else 1

    # Same selection dimensions as HRIS 2013 TTUPiket:
    # JenisTunjangan, Activity, HariKerja, TglMulai,
    # Fungsional/Flag, IDUnitKerja, Shift, StatusPeg.
    sql = text("""
        SELECT
            IDTunjangan,
            Nominal,
            TglMulai,
            HariKerja,
            Fungsional,
            IDUnitKerja,
            Shift,
            StatusPeg,
            UpdateDate
        FROM MF_TUNJANGAN
        WHERE LOWER(JenisTunjangan) = 'u.transport'
          AND Activity = 'Piket Siaga'
          AND HariKerja = :hari_kerja
          AND TglMulai <= :activity_date
          AND Fungsional = :flag
          AND IDUnitKerja = :unit_id
          AND Shift = :shift
          AND StatusPeg = :status_peg
        ORDER BY
            TglMulai DESC,
            CASE
                WHEN :hari_kerja = 0 THEN UpdateDate
                ELSE NULL
            END DESC
        LIMIT 1
    """)

    return db.session.execute(
        sql,
        {
            "hari_kerja": hari_kerja,
            "activity_date": activity_date,
            "flag": flag,
            "unit_id": str(unit_id),
            "shift": str(shift),
            "status_peg": status_peg,
        },
    ).mappings().first()


def calculate_uang_siaga_v2(nip, year, month):
    """Calculate personal Uang Siaga using an isolated V2 engine."""

    start, end = _month_period(year, month)
    employee = _employee(nip)

    if not employee:
        return {
            "status": "success",
            "data": None,
            "message": "Pegawai tidak ditemukan.",
        }

    if not _active(employee, start, end):
        return {
            "status": "success",
            "data": None,
            "message": "Pegawai tidak aktif pada periode tersebut.",
        }

    calendar = _calendar(start, end)

    rows = db.session.execute(
        text("""
            SELECT
                GUIDLog,
                NIP,
                Activity,
                ActivityDate,
                Fungsional,
                IDUnitKerja,
                StatusID,
                shift1,
                shift2,
                Shift,
                TransacID,
                UpdateDate,
                UpdateBy
            FROM LOG_ACTIVITIY
            WHERE NIP = :nip
              AND LOWER(Activity) = 'piket siaga'
              AND ActivityDate >= :start_date
              AND ActivityDate <= :end_date
              AND Shift IS NOT NULL
              AND StatusID = 3
            ORDER BY ActivityDate ASC, Shift ASC, UpdateDate ASC
        """),
        {
            "nip": str(employee["NIP"]).strip(),
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
    work_count = 0.0
    holiday_count = 0.0
    tariff_missing = 0

    for row in rows:
        activity_date = _as_date(row["ActivityDate"])
        if not activity_date:
            continue

        calendar_row = calendar.get(activity_date)

        # Legacy TTUPiket uses KALENDER.IsLibur directly.
        # Missing calendar rows therefore follow the holiday branch.
        is_holiday = (
            str(calendar_row["IsLibur"] or "").strip().upper() != "N"
            if calendar_row
            else True
        )

        hari_kerja = 0 if is_holiday else 1
        shift1_raw = float(row["shift1"] or 0)
        shift2_raw = float(row["shift2"] or 0)
        shift_quantity = shift1_raw + shift2_raw

        if is_holiday:
            holiday_count += shift_quantity
        else:
            work_count += shift_quantity

        shift = str(row["Shift"] or "").strip()
        flag_row = db.session.execute(
            text("""
                SELECT Flag
                FROM MF_ORGZ_SIAGA
                WHERE Fungsional = :fungsional
                LIMIT 1
            """),
            {"fungsional": row["Fungsional"]},
        ).mappings().first()

        flag = flag_row["Flag"] if flag_row else None

        tariff = _tariff(
            activity_date=activity_date,
            is_holiday=is_holiday,
            flag=flag,
            unit_id=row["IDUnitKerja"],
            shift=shift,
            status_peg=employee["StatusPeg"],
        )

        nominal = float(tariff["Nominal"] or 0) if tariff else 0.0

        shift1 = shift1_raw
        shift2 = shift2_raw

        # Exact HRIS 2013 TTUPiket formula:
        # Brutto = shift1 * nominal + shift2 * nominal.
        # Shift selects the tariff; shift1/shift2 provide the quantity.
        brutto = (shift1 * nominal) + (shift2 * nominal)
        gol = str(employee["Gol"] or "").strip().upper()
        pph21 = 0.0 if gol in excluded_gol else brutto * 0.05
        netto = brutto - pph21

        if not tariff:
            tariff_missing += 1

        detail.append({
            "guid_log": str(row["GUIDLog"] or ""),
            "transac_id": row.get("TransacID"),
            "tanggal": activity_date.isoformat(),
            "shift": shift,
            "fungsional": str(row["Fungsional"] or ""),
            "flag": str(flag or ""),
            "status_id": row["StatusID"],
            "shift1_raw": shift1,
            "shift2_raw": shift2,
            "hari_kerja": hari_kerja == 1,
            "quantity": shift1 + shift2,
            "nominal": round(nominal, 2),
            "brutto": round(brutto, 2),
            "pph21": round(pph21, 2),
            "netto": round(netto, 2),
            "tariff_found": bool(tariff),
            "keterangan": "Hari Libur" if is_holiday else "Hari Kerja",
        })

    total_brutto = sum(item["brutto"] for item in detail)
    total_pph21_raw = (
        total_brutto * 0.05
        if str(employee["Gol"] or "").strip().upper() not in excluded_gol
        else 0.0
    )

    # HRIS 2013 report displays whole-rupiah PPh/netto using normal
    # half-up rounding. Decimal avoids Python's bankers-rounding behavior.
    total_pph21 = float(
        Decimal(str(total_pph21_raw)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )
    total_netto = float(
        Decimal(str(total_brutto - total_pph21_raw)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )

    return {
        "status": "success",
        "data": {
            "nip": str(employee["NIP"]),
            "nama": str(employee["Nama"] or ""),
            "gol": str(employee["Gol"] or ""),
            "status_peg": employee["StatusPeg"],
            "year": int(year),
            "month": int(month),
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
            "tariff_missing": int(tariff_missing),
            "total_brutto": round(total_brutto, 2),
            "total_pph21": round(total_pph21, 2),
            "total_uang_siaga": round(total_netto, 2),
            "calculation_basis": (
                "HRIS 2013 TTUPiket.aspx.vb adapted to migrated "
                "LOG_ACTIVITIY rows: one row = one shift."
            ),
            "detail": detail,
        },
    }
