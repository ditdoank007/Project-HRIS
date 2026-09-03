from datetime import datetime

from app.services.attendance_business_engine import AttendanceBusinessEngine


def check(name, actual, expected):
    if actual != expected:
        raise AssertionError(
            f"{name}: expected={expected!r}, actual={actual!r}"
        )
    print(f"PASS  {name}: {actual!r}")


print("=" * 70)
print("HRIS ATTENDANCE TLM / PSW BOUNDARY TEST")
print("=" * 70)


# ================================================================
# TLM
# ================================================================

print("\n=== TLM BOUNDARIES ===")

tlm_cases = [
    (0, ("", 0)),
    (1, ("TLM-1", 0.5)),
    (30, ("TLM-1", 0.5)),
    (31, ("TLM-2", 1)),
    (60, ("TLM-2", 1)),
    (61, ("TLM-3", 1.25)),
    (90, ("TLM-3", 1.25)),
    (91, ("TLM-4", 1.5)),
]

for minutes, expected in tlm_cases:
    actual = AttendanceBusinessEngine.classify_tlm(minutes)

    check(
        f"TLM {minutes} menit",
        actual,
        expected,
    )


# ================================================================
# PSW
# ================================================================

print("\n=== PSW BOUNDARIES ===")

psw_cases = [
    (0, ("", 0)),
    (-1, ("PSW-1", 0.5)),
    (-30, ("PSW-1", 0.5)),
    (-31, ("PSW-2", 1)),
    (-60, ("PSW-2", 1)),
    (-61, ("PSW-3", 1.25)),
    (-90, ("PSW-3", 1.25)),
    (-91, ("PSW-4", 1.5)),
]

for minutes, expected in psw_cases:
    actual = AttendanceBusinessEngine.classify_psw(minutes)

    check(
        f"PSW {minutes} menit",
        actual,
        expected,
    )


# ================================================================
# JAM AKTUAL → TLM
# ================================================================

print("\n=== ACTUAL IN → TLM ===")

baku_in = datetime(2026, 7, 1, 7, 30)

cases = [
    (
        "07:30",
        datetime(2026, 7, 1, 7, 30),
        0,
        ("", 0),
    ),
    (
        "07:31",
        datetime(2026, 7, 1, 7, 31),
        1,
        ("TLM-1", 0.5),
    ),
    (
        "08:00",
        datetime(2026, 7, 1, 8, 0),
        30,
        ("TLM-1", 0.5),
    ),
    (
        "08:01",
        datetime(2026, 7, 1, 8, 1),
        31,
        ("TLM-2", 1),
    ),
    (
        "08:30",
        datetime(2026, 7, 1, 8, 30),
        60,
        ("TLM-2", 1),
    ),
    (
        "08:31",
        datetime(2026, 7, 1, 8, 31),
        61,
        ("TLM-3", 1.25),
    ),
    (
        "09:00",
        datetime(2026, 7, 1, 9, 0),
        90,
        ("TLM-3", 1.25),
    ),
    (
        "09:01",
        datetime(2026, 7, 1, 9, 1),
        91,
        ("TLM-4", 1.5),
    ),
]

for label, actual_in, expected_minutes, expected_category in cases:

    actual_minutes = AttendanceBusinessEngine.calculate_tlm(
        actual_in,
        baku_in,
    )

    check(
        f"TLM minutes {label}",
        actual_minutes,
        expected_minutes,
    )

    actual_category = AttendanceBusinessEngine.classify_tlm(
        actual_minutes
    )

    check(
        f"TLM category {label}",
        actual_category,
        expected_category,
    )


# ================================================================
# JAM AKTUAL → PSW
# ================================================================

print("\n=== ACTUAL OUT → PSW ===")

baku_out = datetime(2026, 7, 1, 16, 0)

cases = [
    (
        "16:00",
        datetime(2026, 7, 1, 16, 0),
        0,
        ("", 0),
    ),
    (
        "15:59",
        datetime(2026, 7, 1, 15, 59),
        -1,
        ("PSW-1", 0.5),
    ),
    (
        "15:30",
        datetime(2026, 7, 1, 15, 30),
        -30,
        ("PSW-1", 0.5),
    ),
    (
        "15:29",
        datetime(2026, 7, 1, 15, 29),
        -31,
        ("PSW-2", 1),
    ),
    (
        "15:00",
        datetime(2026, 7, 1, 15, 0),
        -60,
        ("PSW-2", 1),
    ),
    (
        "14:59",
        datetime(2026, 7, 1, 14, 59),
        -61,
        ("PSW-3", 1.25),
    ),
    (
        "14:30",
        datetime(2026, 7, 1, 14, 30),
        -90,
        ("PSW-3", 1.25),
    ),
    (
        "14:29",
        datetime(2026, 7, 1, 14, 29),
        -91,
        ("PSW-4", 1.5),
    ),
]

for label, actual_out, expected_minutes, expected_category in cases:

    actual_minutes = AttendanceBusinessEngine.calculate_psw(
        actual_out,
        baku_out,
    )

    check(
        f"PSW minutes {label}",
        actual_minutes,
        expected_minutes,
    )

    actual_category = AttendanceBusinessEngine.classify_psw(
        actual_minutes
    )

    check(
        f"PSW category {label}",
        actual_category,
        expected_category,
    )


# ================================================================
# SHIFT 2 CROSS MIDNIGHT
# ================================================================

print("\n=== SHIFT 2 CROSS MIDNIGHT ===")

baku_in = datetime(2026, 7, 1, 19, 30)
baku_out = datetime(2026, 7, 2, 4, 0)

actual_in = datetime(2026, 7, 1, 19, 50)
actual_out = datetime(2026, 7, 2, 4, 10)

tlm = AttendanceBusinessEngine.calculate_tlm(
    actual_in,
    baku_in,
)

psw = AttendanceBusinessEngine.calculate_psw(
    actual_out,
    baku_out,
)

check(
    "Shift 2 TLM",
    tlm,
    20,
)

check(
    "Shift 2 PSW",
    psw,
    0,
)


# ================================================================
# KOMPENSASI TLM-1
# ================================================================

print("\n=== TLM-1 COMPENSATION ===")

check(
    "20 menit TLM + 10 menit pulang lebih",
    AttendanceBusinessEngine.calculate_compensation(
        20,
        datetime(2026, 7, 1, 16, 10),
        datetime(2026, 7, 1, 16, 0),
        False,
        True,
    ),
    10,
)

check(
    "20 menit TLM + 20 menit pulang lebih",
    AttendanceBusinessEngine.calculate_compensation(
        20,
        datetime(2026, 7, 1, 16, 20),
        datetime(2026, 7, 1, 16, 0),
        False,
        True,
    ),
    0,
)

check(
    "20 menit TLM + 30 menit pulang lebih",
    AttendanceBusinessEngine.calculate_compensation(
        20,
        datetime(2026, 7, 1, 16, 30),
        datetime(2026, 7, 1, 16, 0),
        False,
        True,
    ),
    0,
)

check(
    "TLM-2 tidak boleh dikompensasi",
    AttendanceBusinessEngine.calculate_compensation(
        31,
        datetime(2026, 7, 1, 16, 30),
        datetime(2026, 7, 1, 16, 0),
        False,
        True,
    ),
    31,
)

check(
    "PenggantianTLM1=N",
    AttendanceBusinessEngine.calculate_compensation(
        20,
        datetime(2026, 7, 1, 16, 20),
        datetime(2026, 7, 1, 16, 0),
        False,
        False,
    ),
    20,
)


print("\n" + "=" * 70)
print("TLM / PSW BOUNDARY TEST COMPLETE")
print("=" * 70)
