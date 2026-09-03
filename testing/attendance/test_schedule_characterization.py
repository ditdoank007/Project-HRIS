from datetime import date, time, datetime

from app.services.attendance_business_engine import AttendanceBusinessEngine


def check(name, actual, expected):
    if actual != expected:
        raise AssertionError(
            f"{name}: expected={expected!r}, actual={actual!r}"
        )
    print(f"PASS  {name}: {actual!r}")


print("=" * 70)
print("HRIS ATTENDANCE SCHEDULE CHARACTERIZATION")
print("=" * 70)

cases = [
    (
        "07:30-16:00",
        time(7, 30),
        time(16, 0),
        datetime(2026, 7, 1, 7, 30),
        datetime(2026, 7, 1, 16, 0),
    ),
    (
        "07:30-16:30",
        time(7, 30),
        time(16, 30),
        datetime(2026, 7, 1, 7, 30),
        datetime(2026, 7, 1, 16, 30),
    ),
    (
        "08:00-15:00",
        time(8, 0),
        time(15, 0),
        datetime(2026, 7, 1, 8, 0),
        datetime(2026, 7, 1, 15, 0),
    ),
    (
        "08:00-15:30",
        time(8, 0),
        time(15, 30),
        datetime(2026, 7, 1, 8, 0),
        datetime(2026, 7, 1, 15, 30),
    ),
    (
        "08:00-16:00",
        time(8, 0),
        time(16, 0),
        datetime(2026, 7, 1, 8, 0),
        datetime(2026, 7, 1, 16, 0),
    ),
    (
        "08:00-16:30",
        time(8, 0),
        time(16, 30),
        datetime(2026, 7, 1, 8, 0),
        datetime(2026, 7, 1, 16, 30),
    ),
    (
        "19:30-04:00",
        time(19, 30),
        time(4, 0),
        datetime(2026, 7, 1, 19, 30),
        datetime(2026, 7, 2, 4, 0),
    ),
    (
        "20:00-03:00",
        time(20, 0),
        time(3, 0),
        datetime(2026, 7, 1, 20, 0),
        datetime(2026, 7, 2, 3, 0),
    ),
    (
        "20:00-03:30",
        time(20, 0),
        time(3, 30),
        datetime(2026, 7, 1, 20, 0),
        datetime(2026, 7, 2, 3, 30),
    ),
    (
        "20:00-04:00",
        time(20, 0),
        time(4, 0),
        datetime(2026, 7, 1, 20, 0),
        datetime(2026, 7, 2, 4, 0),
    ),
    (
        "20:00-04:30",
        time(20, 0),
        time(4, 30),
        datetime(2026, 7, 1, 20, 0),
        datetime(2026, 7, 2, 4, 30),
    ),
]

tanggal = date(2026, 7, 1)

print("\n=== BUILD WORK SCHEDULE ===")

for name, jam_in, jam_out, expected_in, expected_out in cases:
    actual_in, actual_out = AttendanceBusinessEngine.build_work_schedule(
        tanggal,
        jam_in,
        jam_out,
    )

    print(f"\n{name}")
    print("  IN :", actual_in)
    print("  OUT:", actual_out)

    check("IN", actual_in, expected_in)
    check("OUT", actual_out, expected_out)


print("\n=== DATE BOUNDARY ===")

actual_in, actual_out = AttendanceBusinessEngine.build_work_schedule(
    date(2026, 12, 31),
    time(20, 0),
    time(4, 0),
)

check(
    "year boundary IN",
    actual_in,
    datetime(2026, 12, 31, 20, 0),
)

check(
    "year boundary OUT",
    actual_out,
    datetime(2027, 1, 1, 4, 0),
)


print("\n" + "=" * 70)
print("SCHEDULE CHARACTERIZATION COMPLETE")
print("=" * 70)
