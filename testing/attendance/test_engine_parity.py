from datetime import date, time, datetime

from app.services.attendance_business_engine import AttendanceBusinessEngine
from app.helpers.attendanceNormalizationHelper import AttendanceNormalizationEngine


def show(name, value):
    print(f"\n{name}")
    print(f"  {value!r}")
    return value


print("=" * 70)
print("HRIS ATTENDANCE ENGINE PARITY CHECK")
print("=" * 70)

# ------------------------------------------------------------
# 1. JAM BAKU REGULER
# ------------------------------------------------------------

tanggal = date(2026, 7, 1)

business_in, business_out = (
    AttendanceBusinessEngine.build_work_schedule(
        tanggal,
        time(7, 30),
        time(16, 0),
    )
)

normalization = AttendanceNormalizationEngine()

normal_in, normal_out = normalization.resolve_jam_baku(
    tanggal,
    type(
        "Schedule",
        (),
        {
            "STD_JAM_IN": time(7, 30),
            "STD_JAM_OUT": time(16, 0),
        },
    )(),
)

show("BusinessEngine regular schedule", (business_in, business_out))
show("NormalizationEngine regular schedule", (normal_in, normal_out))

assert business_in == normal_in
assert business_out == normal_out

print("PASS: regular schedule parity")


# ------------------------------------------------------------
# 2. CROSS MIDNIGHT
# ------------------------------------------------------------

business_in, business_out = (
    AttendanceBusinessEngine.build_work_schedule(
        tanggal,
        time(19, 30),
        time(4, 0),
    )
)

normal_in, normal_out = normalization.resolve_jam_baku(
    tanggal,
    type(
        "Schedule",
        (),
        {
            "STD_JAM_IN": time(19, 30),
            "STD_JAM_OUT": time(4, 0),
        },
    )(),
)

show("BusinessEngine cross-midnight", (business_in, business_out))
show("NormalizationEngine cross-midnight", (normal_in, normal_out))

assert business_in == normal_in
assert business_out == normal_out

print("PASS: cross-midnight parity")


# ------------------------------------------------------------
# 3. TLM
# ------------------------------------------------------------

for value in (0, 15, 30, 31, 60, 61, 90, 91):

    business = AttendanceBusinessEngine.classify_tlm(value)
    normalized = normalization.resolve_penalty(
        value,
        0,
        tanggal,
    )

    show(f"TLM {value} BusinessEngine", business)
    show(f"TLM {value} NormalizationEngine", normalized)


# ------------------------------------------------------------
# 4. PSW
# ------------------------------------------------------------

for value in (0, -1, -30, -31, -60, -61, -90, -91):

    business = AttendanceBusinessEngine.classify_psw(value)

    show(
        f"PSW {value} BusinessEngine",
        business,
    )

    try:
        normalized = normalization.resolve_penalty(
            0,
            value,
            tanggal,
        )
        show(
            f"PSW {value} NormalizationEngine",
            normalized,
        )
    except Exception as exc:
        print(
            f"NormalizationEngine PSW {value}: "
            f"NOT COMPARABLE ({exc})"
        )


# ------------------------------------------------------------
# 5. KOMPENSASI TLM-1
# ------------------------------------------------------------

jam_out = datetime(2026, 7, 1, 16, 10)
jam_baku_out = datetime(2026, 7, 1, 16, 0)

business = AttendanceBusinessEngine.calculate_compensation(
    awal_tlm=20,
    jam_out=jam_out,
    jam_baku_out=jam_baku_out,
    is_libur=False,
    penggantian_tlm1=True,
)

show("BusinessEngine TLM-1 compensation", business)

try:
    normalized = normalization.calculate_compensation(
        awal_tlm=20,
        jam_out=jam_out,
        jam_baku_out=jam_baku_out,
        is_libur=False,
        penggantian_tlm1=True,
    )
    show("NormalizationEngine TLM-1 compensation", normalized)
except Exception as exc:
    print(
        "NormalizationEngine compensation: "
        f"NOT COMPARABLE ({exc})"
    )


print("\n" + "=" * 70)
print("PARITY CHECK COMPLETE")
print("=" * 70)
