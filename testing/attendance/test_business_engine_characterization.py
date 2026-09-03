from datetime import date, time, datetime

from app.services.attendance_business_engine import AttendanceBusinessEngine


def check(name, actual, expected):
    if actual != expected:
        raise AssertionError(
            f"{name}: expected={expected!r}, actual={actual!r}"
        )
    print(f"PASS  {name}: {actual!r}")


print("=" * 60)
print("ATTENDANCE BUSINESS ENGINE CHARACTERIZATION")
print("=" * 60)

print("\n=== ENGINE IDENTITY ===")
check(
    "ENGINE_NAME",
    AttendanceBusinessEngine.ENGINE_NAME,
    "AttendanceBusinessEngine",
)

print("\n=== WORK SCHEDULE ===")
jam_in, jam_out = AttendanceBusinessEngine.build_work_schedule(
    date(2026, 7, 1),
    time(7, 30),
    time(16, 0),
)

check(
    "regular IN",
    jam_in,
    datetime(2026, 7, 1, 7, 30),
)

check(
    "regular OUT",
    jam_out,
    datetime(2026, 7, 1, 16, 0),
)

jam_in, jam_out = AttendanceBusinessEngine.build_work_schedule(
    date(2026, 7, 1),
    time(19, 30),
    time(4, 0),
)

check(
    "cross-midnight IN",
    jam_in,
    datetime(2026, 7, 1, 19, 30),
)

check(
    "cross-midnight OUT",
    jam_out,
    datetime(2026, 7, 2, 4, 0),
)

print("\n=== TLM ===")
check(
    "TLM 0",
    AttendanceBusinessEngine.classify_tlm(0),
    ("", 0),
)

check(
    "TLM 15",
    AttendanceBusinessEngine.classify_tlm(15),
    ("TLM-1", 0.5),
)

check(
    "TLM 30",
    AttendanceBusinessEngine.classify_tlm(30),
    ("TLM-1", 0.5),
)

check(
    "TLM 31",
    AttendanceBusinessEngine.classify_tlm(31),
    ("TLM-2", 1),
)

check(
    "TLM 60",
    AttendanceBusinessEngine.classify_tlm(60),
    ("TLM-2", 1),
)

check(
    "TLM 61",
    AttendanceBusinessEngine.classify_tlm(61),
    ("TLM-3", 1.25),
)

check(
    "TLM 90",
    AttendanceBusinessEngine.classify_tlm(90),
    ("TLM-3", 1.25),
)

check(
    "TLM 91",
    AttendanceBusinessEngine.classify_tlm(91),
    ("TLM-4", 1.5),
)

print("\n=== PSW ===")
print(
    "PSW classification currently implemented as:",
    [
        (value, AttendanceBusinessEngine.classify_psw(value))
        for value in (0, -1, -30, -31, -60, -61, -90, -91)
    ],
)

print("\n=== TLM-1 COMPENSATION ===")

check(
    "TLM-1 no PSW",
    AttendanceBusinessEngine.calculate_compensation(
        awal_tlm=20,
        jam_out=datetime(2026, 7, 1, 16, 0),
        jam_baku_out=datetime(2026, 7, 1, 16, 0),
        is_libur=False,
        penggantian_tlm1=True,
    ),
    20,
)

check(
    "TLM-1 compensated by 10m PSW",
    AttendanceBusinessEngine.calculate_compensation(
        awal_tlm=20,
        jam_out=datetime(2026, 7, 1, 16, 10),
        jam_baku_out=datetime(2026, 7, 1, 16, 0),
        is_libur=False,
        penggantian_tlm1=True,
    ),
    10,
)

check(
    "TLM-1 cannot compensate >30",
    AttendanceBusinessEngine.calculate_compensation(
        awal_tlm=31,
        jam_out=datetime(2026, 7, 1, 16, 10),
        jam_baku_out=datetime(2026, 7, 1, 16, 0),
        is_libur=False,
        penggantian_tlm1=True,
    ),
    31,
)

print("\n=== DATE PARSING ===")
check(
    "ISO date",
    AttendanceBusinessEngine._date("2026-07-01"),
    date(2026, 7, 1),
)

check(
    "DD-MM-YYYY",
    AttendanceBusinessEngine._date("01-07-2026"),
    date(2026, 7, 1),
)

check(
    "DD/MM/YYYY",
    AttendanceBusinessEngine._date("01/07/2026"),
    date(2026, 7, 1),
)

print("\n" + "=" * 60)
print("CHARACTERIZATION COMPLETE")
print("=" * 60)
