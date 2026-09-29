# app/utils/pegawaiLegacyHelper.py
"""
Business rules derived from HRIS 2013 for employee identity data.

This module does not modify legacy PEGAWAI data. It only derives values
needed by HRIS Reborn from the established NIP format and existing dates.
"""

from datetime import date, datetime
from typing import Optional


def parse_pns_nip(nip: str) -> Optional[dict]:
    """
    Parse the established 18-digit PNS NIP format.

    YYYYMMDD YYYYMM G UUU
    0------- 8---- 14 15--

    The first 8 digits are date of birth.
    Digits 8-13 are CPNS year/month.
    Digit 14 is gender: 1 male, 2 female.
    Digits 15-17 are the unique sequence.
    """
    value = str(nip or "").strip()

    if len(value) != 18 or not value.isdigit():
        return None

    try:
        birth_date = datetime.strptime(value[0:8], "%Y%m%d").date()
        cpns_year = int(value[8:12])
        cpns_month = int(value[12:14])

        if not 1 <= cpns_month <= 12:
            return None

        gender_code = value[14]
        gender = {
            "1": "Laki-laki",
            "2": "Perempuan",
        }.get(gender_code)

        return {
            "birth_date": birth_date,
            "cpns_year": cpns_year,
            "cpns_month": cpns_month,
            "cpns_period": f"{cpns_year:04d}-{cpns_month:02d}",
            "gender_code": gender_code,
            "gender": gender,
            "sequence": value[15:18],
        }
    except (TypeError, ValueError):
        return None


def calculate_age(birth_date, on_date: Optional[date] = None) -> Optional[int]:
    """Calculate completed age in years."""
    if not birth_date:
        return None

    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()

    on_date = on_date or date.today()

    if birth_date > on_date:
        return None

    return (
        on_date.year
        - birth_date.year
        - (
            (on_date.month, on_date.day)
            < (birth_date.month, birth_date.day)
        )
    )


def calculate_service_years(start_date, on_date: Optional[date] = None) -> Optional[int]:
    """Calculate completed service years from a concrete start date."""
    return calculate_age(start_date, on_date)


def calculate_service_months_from_period(
    year: int,
    month: int,
    on_date: Optional[date] = None,
) -> Optional[int]:
    """
    Calculate completed months from a YYYY-MM period.

    HRIS 2013 stores an actual TMTCPNS date when available. When only the
    NIP's YYYYMM component is available, this deliberately uses month
    precision and does not invent a day.
    """
    try:
        start = date(int(year), int(month), 1)
    except (TypeError, ValueError):
        return None

    on_date = on_date or date.today()
    if start > on_date:
        return None

    return (
        (on_date.year - start.year) * 12
        + (on_date.month - start.month)
    )


def derive_employee_metrics(
    nip: str,
    status_peg,
    tgl_lahir=None,
    tmt_cpns=None,
    on_date: Optional[date] = None,
) -> dict:
    """
    Derive age, gender and service information without changing source data.

    PNS:
      - birth date and gender are derived from NIP when the NIP is valid.
      - actual TMTCPNS is preferred for service duration.
      - NIP YYYYMM is used only when TMTCPNS is unavailable.

    NON PNS:
      - birth date comes only from PEGAWAI.TglLahir.
      - missing birth date remains missing.
    """
    is_pns = str(status_peg or "") == "1"
    parsed = parse_pns_nip(nip) if is_pns else None

    effective_birth = (
        parsed.get("birth_date")
        if parsed
        else tgl_lahir
    )

    age = calculate_age(effective_birth, on_date)

    service_months = None
    if is_pns:
        if tmt_cpns:
            if isinstance(tmt_cpns, datetime):
                tmt_cpns = tmt_cpns.date()

            effective_date = on_date or date.today()
            if tmt_cpns <= effective_date:
                service_months = (
                    (effective_date.year - tmt_cpns.year) * 12
                    + (effective_date.month - tmt_cpns.month)
                )
        elif parsed:
            service_months = calculate_service_months_from_period(
                parsed["cpns_year"],
                parsed["cpns_month"],
                on_date,
            )

    return {
        "tanggal_lahir_derived": (
            effective_birth.isoformat()
            if effective_birth else None
        ),
        "usia": age,
        "jenis_kelamin_derived": (
            parsed.get("gender")
            if parsed and parsed.get("gender")
            else None
        ),
        "tmt_cpns_period_derived": (
            parsed.get("cpns_period")
            if parsed
            else None
        ),
        "masa_kerja_bulan": service_months,
        "masa_kerja_tahun": (
            service_months // 12
            if service_months is not None
            else None
        ),
        "nip_valid_pns": bool(parsed) if is_pns else None,
    }
