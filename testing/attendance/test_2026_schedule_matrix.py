from datetime import date, time

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


rows = [
    # Senin-Kamis REGULER
    Row(
        "1", "1", date(2026, 3, 25),
        time(7, 30), time(16, 0), 81
    ),

    # Jumat REGULER
    Row(
        "2", "1", date(2026, 3, 25),
        time(7, 30), time(16, 30), 82
    ),

    # Senin-Kamis SIAGA
    Row(
        "1", "2", date(2026, 3, 25),
        time(19, 30), time(4, 0), 83
    ),

    # Jumat SIAGA
    Row(
        "2", "2", date(2026, 3, 25),
        time(19, 30), time(4, 30), 84
    ),
]

engine = AttendanceNormalizationEngine(
    jam_kerja=rows,
    load_finger=[],
)

print("=" * 70)
print("HRIS 2026 MASTER JAM KERJA MATRIX")
print("=" * 70)

# ================================================================
# SENIN-KAMIS
# ================================================================

print("\n=== SENIN-KAMIS ===")

tanggal = date(2026, 3, 30)  # Senin

check(
    "hari",
    engine.resolve_shift_hari(tanggal),
    "1",
)

jk = engine.resolve_jam_kerja(tanggal, "1")

check(
    "REGULER ID",
    jk.IDJKERJA,
    81,
)

baku_in, baku_out = engine.resolve_jam_baku(
    tanggal,
    jk,
)

check(
    "REGULER IN",
    baku_in.strftime("%H:%M"),
    "07:30",
)

check(
    "REGULER OUT",
    baku_out.strftime("%H:%M"),
    "16:00",
)

jk = engine.resolve_jam_kerja(tanggal, "2")

check(
    "SIAGA ID",
    jk.IDJKERJA,
    83,
)

baku_in, baku_out = engine.resolve_jam_baku(
    tanggal,
    jk,
)

check(
    "SIAGA IN",
    baku_in.strftime("%H:%M"),
    "19:30",
)

check(
    "SIAGA OUT",
    baku_out.strftime("%H:%M"),
    "04:00",
)

check(
    "SIAGA OUT NEXT DAY",
    baku_out.date(),
    date(2026, 3, 31),
)

# ================================================================
# JUMAT
# ================================================================

print("\n=== JUMAT ===")

tanggal = date(2026, 4, 3)  # Jumat

check(
    "hari",
    engine.resolve_shift_hari(tanggal),
    "2",
)

jk = engine.resolve_jam_kerja(tanggal, "1")

check(
    "REGULER ID",
    jk.IDJKERJA,
    82,
)

baku_in, baku_out = engine.resolve_jam_baku(
    tanggal,
    jk,
)

check(
    "REGULER IN",
    baku_in.strftime("%H:%M"),
    "07:30",
)

check(
    "REGULER OUT",
    baku_out.strftime("%H:%M"),
    "16:30",
)

jk = engine.resolve_jam_kerja(tanggal, "2")

check(
    "SIAGA ID",
    jk.IDJKERJA,
    84,
)

baku_in, baku_out = engine.resolve_jam_baku(
    tanggal,
    jk,
)

check(
    "SIAGA IN",
    baku_in.strftime("%H:%M"),
    "19:30",
)

check(
    "SIAGA OUT",
    baku_out.strftime("%H:%M"),
    "04:30",
)

check(
    "SIAGA OUT NEXT DAY",
    baku_out.date(),
    date(2026, 4, 4),
)

print("\n" + "=" * 70)
print("2026 MASTER JAM KERJA MATRIX: COMPLETE")
print("=" * 70)
