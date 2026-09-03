from datetime import date, time, datetime

from app.helpers.attendanceNormalizationHelper import (
    AttendanceNormalizationEngine,
)


class Row:
    def __init__(
        self,
        shift,
        shift_kerja,
        mulai,
        jam_in,
        jam_out,
        idj,
    ):
        self.SHIFT = shift
        self.SHIFT_KERJA = shift_kerja
        self.TGL_MULAI_BERLAKU = mulai
        self.STD_JAM_IN = jam_in
        self.STD_JAM_OUT = jam_out
        self.IDJKERJA = idj


def check(name, actual, expected):
    if actual != expected:
        raise AssertionError(
            f"{name}: expected={expected!r}, actual={actual!r}"
        )

    print(f"PASS  {name}: {actual!r}")


print("=" * 70)
print("HRIS ATTENDANCE SCHEDULE RESOLVER CHARACTERIZATION")
print("=" * 70)


# ================================================================
# MASTER DATA SIMULASI DARI MF_JAM_KERJA
# ================================================================

rows = [
    Row(
        "1",
        "1",
        date(2025, 1, 1),
        time(7, 30),
        time(16, 0),
        1,
    ),
    Row(
        "1",
        "1",
        date(2026, 1, 1),
        time(7, 30),
        time(16, 30),
        2,
    ),
    Row(
        "1",
        "1",
        date(2026, 6, 1),
        time(8, 0),
        time(16, 0),
        3,
    ),
    Row(
        "1",
        "1",
        date(2026, 7, 1),
        time(19, 30),
        time(4, 0),
        4,
    ),

    # SHIFT 2 = Jumat
    Row(
        "2",
        "1",
        date(2025, 1, 1),
        time(7, 30),
        time(16, 0),
        20,
    ),
    Row(
        "2",
        "1",
        date(2026, 1, 1),
        time(8, 0),
        time(16, 30),
        21,
    ),

    # SHIFT_KERJA = 2
    Row(
        "1",
        "2",
        date(2025, 1, 1),
        time(8, 0),
        time(16, 0),
        10,
    ),
    Row(
        "1",
        "2",
        date(2026, 1, 1),
        time(20, 0),
        time(4, 0),
        11,
    ),
]


engine = AttendanceNormalizationEngine(
    jam_kerja=rows,
    load_finger=[],
)


# ================================================================
# SHIFT HARI
# ================================================================

print("\n=== SHIFT HARI ===")

check(
    "Monday",
    engine.resolve_shift_hari(date(2026, 7, 6)),
    "1",
)

check(
    "Thursday",
    engine.resolve_shift_hari(date(2026, 7, 9)),
    "1",
)

check(
    "Friday",
    engine.resolve_shift_hari(date(2026, 7, 10)),
    "2",
)


# ================================================================
# EFFECTIVE DATE
# ================================================================

print("\n=== EFFECTIVE DATE ===")

jk = engine.resolve_jam_kerja(
    date(2026, 5, 4),
    "1",
)

check(
    "before June 2026",
    jk.IDJKERJA,
    2,
)

jk = engine.resolve_jam_kerja(
    date(2026, 6, 15),
    "1",
)

check(
    "June 2026",
    jk.IDJKERJA,
    3,
)

jk = engine.resolve_jam_kerja(
    date(2026, 7, 15),
    "1",
)

check(
    "July 2026",
    jk.IDJKERJA,
    4,
)


# ================================================================
# SHIFT_KERJA
# ================================================================

print("\n=== SHIFT_KERJA ===")

jk = engine.resolve_jam_kerja(
    date(2026, 7, 15),
    "2",
)

check(
    "siaga schedule",
    jk.IDJKERJA,
    11,
)


# ================================================================
# JAM BAKU
# ================================================================

print("\n=== JAM BAKU ===")

jk = engine.resolve_jam_kerja(
    date(2026, 7, 15),
    "1",
)

baku_in, baku_out = engine.resolve_jam_baku(
    date(2026, 7, 15),
    jk,
)

check(
    "cross-midnight IN",
    baku_in,
    datetime(2026, 7, 15, 19, 30),
)

check(
    "cross-midnight OUT",
    baku_out,
    datetime(2026, 7, 16, 4, 0),
)


# ================================================================
# NO MATCH
# ================================================================

print("\n=== NO MATCH ===")

empty = AttendanceNormalizationEngine(
    jam_kerja=[],
    load_finger=[],
)

check(
    "no schedule",
    empty.resolve_jam_kerja(
        date(2026, 7, 15),
        "1",
    ),
    None,
)

check(
    "no load finger",
    empty.resolve_load_finger(
        date(2026, 7, 15),
        "1",
    ),
    None,
)


print("\n" + "=" * 70)
print("SCHEDULE RESOLVER CHARACTERIZATION COMPLETE")
print("=" * 70)
