from datetime import date, datetime

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
        penggantian,
    ):
        self.SHIFT = shift
        self.SHIFT_KERJA = shift_kerja
        self.TGL_MULAI_BERLAKU = mulai
        self.STD_JAM_IN = jam_in
        self.STD_JAM_OUT = jam_out
        self.IDJKERJA = idj
        self.PENGGANTIAN_TLM1 = penggantian


rows = [
    # Senin-Kamis REGULER
    Row(
        "1", "1",
        date(2026, 3, 25),
        datetime(1900, 1, 1, 7, 30).time(),
        datetime(1900, 1, 1, 16, 0).time(),
        81,
        "Y",
    ),

    # Jumat REGULER
    Row(
        "2", "1",
        date(2026, 3, 25),
        datetime(1900, 1, 1, 7, 30).time(),
        datetime(1900, 1, 1, 16, 30).time(),
        82,
        "Y",
    ),

    # Senin-Kamis SIAGA
    Row(
        "1", "2",
        date(2026, 3, 25),
        datetime(1900, 1, 1, 19, 30).time(),
        datetime(1900, 1, 1, 4, 0).time(),
        83,
        "Y",
    ),

    # Jumat SIAGA
    Row(
        "2", "2",
        date(2026, 3, 25),
        datetime(1900, 1, 1, 19, 30).time(),
        datetime(1900, 1, 1, 4, 30).time(),
        84,
        "Y",
    ),
]


engine = AttendanceNormalizationEngine(
    jam_kerja=rows,
    load_finger=[],
)


def check(name, actual, expected):
    if actual != expected:
        raise AssertionError(
            f"{name}: expected={expected!r}, actual={actual!r}"
        )
    print(f"PASS  {name}: {actual!r}")


print("=" * 70)
print("HRIS NORMALIZE MASTER 2026 CHARACTERIZATION")
print("=" * 70)


# ================================================================
# SENIN-KAMIS REGULER
# ================================================================

print("\n=== SENIN-KAMIS REGULER ===")

row = engine.normalize_row(
    nip="TEST",
    finger_id="TEST",
    nama="TEST",
    gol="",
    unit_kerja="TEST",
    tgl_kerja=date(2026, 7, 6),
    jam_in=datetime(2026, 7, 6, 7, 50),
    jam_out=datetime(2026, 7, 6, 16, 20),
    shift_kerja="1",
    is_libur=False,
)

check("jam baku IN", row["jam_baku_in"], "07:30")
check("jam baku OUT", row["jam_baku_out"], "16:00")
check("awal TLM", row["awal_tlm"], 20.0)
check("total TLM", row["total_tlm"], 0.0)
check("tingkat TLM", row["tingkat_tlm"], "TLM-1")


# ================================================================
# JUMAT REGULER
# ================================================================

print("\n=== JUMAT REGULER ===")

row = engine.normalize_row(
    nip="TEST",
    finger_id="TEST",
    nama="TEST",
    gol="",
    unit_kerja="TEST",
    tgl_kerja=date(2026, 7, 10),
    jam_in=datetime(2026, 7, 10, 7, 50),
    jam_out=datetime(2026, 7, 10, 16, 50),
    shift_kerja="1",
    is_libur=False,
)

check("jam baku IN", row["jam_baku_in"], "07:30")
check("jam baku OUT", row["jam_baku_out"], "16:30")
check("awal TLM", row["awal_tlm"], 20.0)
check("total TLM", row["total_tlm"], 0.0)
check("tingkat TLM", row["tingkat_tlm"], "TLM-1")


# ================================================================
# SENIN-KAMIS SIAGA
# ================================================================

print("\n=== SENIN-KAMIS SIAGA ===")

row = engine.normalize_row(
    nip="TEST",
    finger_id="TEST",
    nama="TEST",
    gol="",
    unit_kerja="TEST",
    tgl_kerja=date(2026, 7, 6),
    jam_in=datetime(2026, 7, 6, 19, 50),
    jam_out=datetime(2026, 7, 7, 4, 20),
    shift_kerja="2",
    is_libur=False,
)

check("jam baku IN", row["jam_baku_in"], "19:30")
check("jam baku OUT", row["jam_baku_out"], "04:00")
check("awal TLM", row["awal_tlm"], 20.0)
check("total TLM", row["total_tlm"], 0.0)
check("tingkat TLM", row["tingkat_tlm"], "TLM-1")


# ================================================================
# JUMAT SIAGA
# ================================================================

print("\n=== JUMAT SIAGA ===")

row = engine.normalize_row(
    nip="TEST",
    finger_id="TEST",
    nama="TEST",
    gol="",
    unit_kerja="TEST",
    tgl_kerja=date(2026, 7, 10),
    jam_in=datetime(2026, 7, 10, 19, 50),
    jam_out=datetime(2026, 7, 11, 4, 50),
    shift_kerja="2",
    is_libur=False,
)

check("jam baku IN", row["jam_baku_in"], "19:30")
check("jam baku OUT", row["jam_baku_out"], "04:30")
check("awal TLM", row["awal_tlm"], 20.0)
check("total TLM", row["total_tlm"], 0.0)
check("tingkat TLM", row["tingkat_tlm"], "TLM-1")


print()
print("=" * 70)
print("NORMALIZE MASTER 2026: COMPLETE")
print("=" * 70)
