from datetime import date, datetime, time

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


def check(name, actual, expected):
    if actual != expected:
        raise AssertionError(
            f"{name}: expected={expected!r}, actual={actual!r}"
        )

    print(f"PASS  {name}: {actual!r}")


print("=" * 70)
print("HRIS TLM-1 PENGGANTIAN SWITCH TEST")
print("=" * 70)


tanggal = date(2026, 7, 6)


def make_engine(penggantian):
    return AttendanceNormalizationEngine(
        jam_kerja=[
            Row(
                "1",
                "1",
                date(2026, 1, 1),
                time(7, 30),
                time(16, 0),
                1,
                penggantian,
            )
        ],
        load_finger=[],
    )


# ================================================================
# TLM 20 MENIT
# ================================================================

jam_in = datetime(2026, 7, 6, 7, 50)

# Pulang 16:10 -> tambahan 10 menit
jam_out_10 = datetime(2026, 7, 6, 16, 10)

# Pulang 16:20 -> tambahan 20 menit
jam_out_20 = datetime(2026, 7, 6, 16, 20)


print("\n=== PENGGANTIAN = Y ===")

engine_y = make_engine("Y")

row = engine_y.normalize_row(
    nip="TEST",
    finger_id="TEST",
    nama="TEST",
    gol="",
    unit_kerja="",
    tgl_kerja=tanggal,
    jam_in=jam_in,
    jam_out=jam_out_10,
    shift_kerja="1",
    is_libur=False,
)

check(
    "Y / TLM 20 / kompensasi 10",
    row["total_tlm"],
    10.0,
)

row = engine_y.normalize_row(
    nip="TEST",
    finger_id="TEST",
    nama="TEST",
    gol="",
    unit_kerja="",
    tgl_kerja=tanggal,
    jam_in=jam_in,
    jam_out=jam_out_20,
    shift_kerja="1",
    is_libur=False,
)

check(
    "Y / TLM 20 / kompensasi 20",
    row["total_tlm"],
    0,
)


print("\n=== PENGGANTIAN = N ===")

engine_n = make_engine("N")

row = engine_n.normalize_row(
    nip="TEST",
    finger_id="TEST",
    nama="TEST",
    gol="",
    unit_kerja="",
    tgl_kerja=tanggal,
    jam_in=jam_in,
    jam_out=jam_out_20,
    shift_kerja="1",
    is_libur=False,
)

check(
    "N / TLM 20 / pulang +20",
    row["total_tlm"],
    20.0,
)

check(
    "N / kategori tetap TLM-1",
    row["tingkat_tlm"],
    "TLM-1",
)


print("\n=== TLM-2 TIDAK BOLEH DIKOMPENSASI ===")

jam_in_tlm2 = datetime(2026, 7, 6, 8, 1)

row = engine_y.normalize_row(
    nip="TEST",
    finger_id="TEST",
    nama="TEST",
    gol="",
    unit_kerja="",
    tgl_kerja=tanggal,
    jam_in=jam_in_tlm2,
    jam_out=jam_out_20,
    shift_kerja="1",
    is_libur=False,
)

check(
    "Y / TLM-2 31 menit",
    row["total_tlm"],
    31.0,
)

check(
    "Y / TLM-2 kategori",
    row["tingkat_tlm"],
    "TLM-2",
)


print()
print("=" * 70)
print("TLM-1 PENGGANTIAN SWITCH TEST: COMPLETE")
print("=" * 70)
