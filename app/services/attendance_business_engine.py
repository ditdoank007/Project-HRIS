"""
Attendance Business Engine
HRIS Reborn

Version:
    0.2.0

Tujuan:
    Memusatkan business process normalisasi absensi.

Prinsip:
    - Tidak melakukan query database.
    - Tidak melakukan commit database.
    - Tidak mengetahui SQLAlchemy model.
    - Input diberikan oleh resolver/repository.
    - Rule diproses in-memory.
    - Data master di-index sekali.
    - Deterministic / repeatable.
    - Hasil dapat diaudit dan dibandingkan dengan legacy.

Catatan:
    Engine ini belum dihubungkan ke controller produksi.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# CONTEXT
# ============================================================

@dataclass
class AttendanceContext:
    """
    Input business process untuk satu periode normalisasi.

    Seluruh data diberikan dari luar engine.

    Engine tidak melakukan database access.
    """

    employee: Any = None
    work_date: Any = None

    schedule: Any = None
    shift: Any = None
    load_finger: Any = None

    finger_logs: List[Any] = field(default_factory=list)

    dinas_luar: Any = None
    calendar: Any = None

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttendancePeriodContext:
    """
    Input bulk untuk normalisasi satu periode.

    Semua master/reference data sebaiknya sudah di-load
    satu kali oleh resolver/repository.
    """

    employees: List[Any] = field(default_factory=list)

    finger_logs: List[Any] = field(default_factory=list)

    shift2_rows: List[Any] = field(default_factory=list)

    schedules: List[Any] = field(default_factory=list)

    load_fingers: List[Any] = field(default_factory=list)

    calendars: List[Any] = field(default_factory=list)

    dinas_luar: List[Any] = field(default_factory=list)

    potongan: List[Any] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# RESULT
# ============================================================

@dataclass
class AttendanceResult:
    """
    Business result.

    Bukan SQLAlchemy model.
    """

    finger_id: Optional[str] = None
    nip: Optional[str] = None
    nama: Optional[str] = None
    gol: Optional[str] = None
    unit_kerja: Optional[str] = None

    tgl_kerja: Any = None
    hari: Optional[str] = None

    shift: Optional[str] = None
    shift_kerja: Optional[str] = None

    tgl_jam_in: Any = None
    tgl_jam_out: Any = None

    tgl_jam_baku_in: Any = None
    tgl_jam_baku_out: Any = None

    jam_in: Optional[str] = None
    jam_out: Optional[str] = None

    jam_baku_in: Optional[str] = None
    jam_baku_out: Optional[str] = None

    transaksi_in: Optional[str] = None
    transaksi_out: Optional[str] = None

    tingkat_tlm: Optional[str] = None
    total_tlm: Optional[float] = None
    persen_pot_tlm: Optional[float] = None
    awal_tlm: Optional[float] = None

    tingkat_psw: Optional[str] = None
    total_psw: Optional[float] = None
    persen_pot_psw: Optional[float] = None

    is_valid_in: bool = False
    is_valid_out: bool = False

    is_invalid: bool = False
    is_outvalid: bool = False

    is_libur: bool = False

    transaksi_id_from: Optional[str] = None

    pendukung_in: Optional[str] = None
    pendukung_out: Optional[str] = None

    status_um: Optional[int] = None

    shift2_siaga: bool = False
    activity_date_siaga: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# ENGINE
# ============================================================

class AttendanceBusinessEngine:
    """
    Orchestrator business process absensi.

    v0.2.0:
        - normalisasi waktu
        - TLM
        - PSW
        - kompensasi TLM-1
        - cross midnight
        - kalender/libur
        - index master
        - pairing IN/OUT
        - deterministic result

    Belum melakukan persistence.
    """

    ENGINE_NAME = "AttendanceBusinessEngine"
    ENGINE_VERSION = "0.2.0"

    def __init__(
        self,
        *,
        rule_engine=None,
        schedule_index=None,
        load_finger_index=None,
        calendar_index=None,
        potongan_index=None,
    ):
        self.rule_engine = rule_engine

        self.schedule_index = (
            schedule_index
            if schedule_index is not None
            else {}
        )

        self.load_finger_index = (
            load_finger_index
            if load_finger_index is not None
            else {}
        )

        self.calendar_index = (
            calendar_index
            if calendar_index is not None
            else {}
        )

        self.potongan_index = (
            potongan_index
            if potongan_index is not None
            else {}
        )

    # ========================================================
    # PUBLIC ENTRY POINT
    # ========================================================

    def process(
        self,
        context: AttendanceContext,
    ) -> AttendanceResult:
        """
        Memproses satu unit absensi.

        Belum melakukan pairing database.
        """

        self._validate_context(context)

        result = AttendanceResult(
            finger_id=self._get_finger_id(
                context.employee
            ),
            nip=self._get_value(
                context.employee,
                "NIP",
            ),
            nama=self._get_value(
                context.employee,
                "NAMA",
            ),
            tgl_kerja=context.work_date,
        )

        result.metadata.update({
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
        })

        return result

    def process_logs(
        self,
        *,
        employee,
        work_date,
        finger_logs,
        schedule,
        is_libur=False,
        shift_kerja="1",
    ) -> Optional[AttendanceResult]:
        """
        Memproses fingerprint untuk satu pegawai/tanggal.

        Rule pairing legacy:
            IN  = fingerprint PUNCH 0 paling awal
            OUT = fingerprint PUNCH 1 paling akhir
        """

        work_date = self._date(work_date)

        logs = list(
            finger_logs or []
        )

        logs_in = sorted(
            [
                log for log in logs
                if self._punch(log) == 0
            ],
            key=self._log_datetime,
        )

        logs_out = sorted(
            [
                log for log in logs
                if self._punch(log) == 1
            ],
            key=self._log_datetime,
        )

        jam_in = (
            self._log_datetime(logs_in[0])
            if logs_in
            else None
        )

        jam_out = (
            self._log_datetime(logs_out[-1])
            if logs_out
            else None
        )

        if not jam_in and not jam_out:
            return None

        return self.normalize(
            employee=employee,
            work_date=work_date,
            jam_in=jam_in,
            jam_out=jam_out,
            schedule=schedule,
            is_libur=is_libur,
            shift_kerja=shift_kerja,
        )

    def normalize(
        self,
        *,
        employee,
        work_date,
        jam_in=None,
        jam_out=None,
        schedule=None,
        is_libur=False,
        shift_kerja="1",
    ) -> AttendanceResult:
        """
        Normalisasi satu row absensi.

        Business calculation:
            JAM_IN - JAM_BAKU_IN = TLM awal
            JAM_OUT - JAM_BAKU_OUT = PSW
            TLM-1 dapat dikompensasi oleh keterlambatan pulang.
        """

        work_date = self._date(work_date)

        std_jam_in = self._get_schedule_value(
            schedule,
            "STD_JAM_IN",
        )

        std_jam_out = self._get_schedule_value(
            schedule,
            "STD_JAM_OUT",
        )

        jam_baku_in, jam_baku_out = (
            self.build_work_schedule(
                work_date,
                std_jam_in,
                std_jam_out,
            )
        )

        awal_tlm = self.calculate_tlm(
            jam_in,
            jam_baku_in,
        )

        total_psw = self.calculate_psw(
            jam_out,
            jam_baku_out,
        )

        total_tlm = self.calculate_compensation(
            awal_tlm,
            jam_out,
            jam_baku_out,
            is_libur=is_libur,
        )

        if is_libur:
            tingkat_tlm = ""
            persen_tlm = 0
            tingkat_psw = ""
            persen_psw = 0
        else:
            # Kategori TLM ditentukan dari AWAL_TLM,
            # bukan total TLM setelah kompensasi.
            tingkat_tlm, persen_tlm = (
                self.classify_tlm(
                    awal_tlm
                )
            )

            tingkat_psw, persen_psw = (
                self.classify_psw(
                    total_psw
                )
            )

        return AttendanceResult(
            finger_id=self._get_finger_id(employee),
            nip=self._get_value(employee, "NIP"),
            nama=self._get_value(employee, "NAMA"),
            gol=self._get_value(employee, "GOL"),
            unit_kerja=self._get_value(
                employee,
                "UNIT_KERJA",
            ),

            tgl_kerja=work_date,
            hari=work_date.strftime("%A"),

            shift_kerja=str(
                shift_kerja
            ),

            tgl_jam_in=jam_in,
            tgl_jam_out=jam_out,

            tgl_jam_baku_in=jam_baku_in,
            tgl_jam_baku_out=jam_baku_out,

            jam_in=(
                jam_in.strftime("%H:%M:%S")
                if jam_in
                else "00:00:00"
            ),

            jam_out=(
                jam_out.strftime("%H:%M:%S")
                if jam_out
                else "00:00:00"
            ),

            jam_baku_in=(
                jam_baku_in.strftime("%H:%M")
                if jam_baku_in
                else ""
            ),

            jam_baku_out=(
                jam_baku_out.strftime("%H:%M")
                if jam_baku_out
                else ""
            ),

            is_valid_in=bool(jam_in),
            is_valid_out=bool(jam_out),

            is_libur=is_libur,

            awal_tlm=round(
                awal_tlm,
                2,
            ),

            total_tlm=round(
                total_tlm,
                2,
            ),

            tingkat_tlm=tingkat_tlm,
            persen_pot_tlm=persen_tlm,

            total_psw=round(
                total_psw,
                2,
            ),

            tingkat_psw=tingkat_psw,
            persen_pot_psw=persen_psw,

            metadata={
                "engine": self.ENGINE_NAME,
                "engine_version": self.ENGINE_VERSION,
            },
        )

    # ========================================================
    # TLM / PSW
    # ========================================================

    @staticmethod
    def calculate_tlm(
        jam_in,
        jam_baku_in,
    ):
        if not jam_in or not jam_baku_in:
            return 0

        return max(
            0,
            AttendanceBusinessEngine.minutes(
                jam_in - jam_baku_in
            ),
        )

    @staticmethod
    def calculate_psw(
        jam_out,
        jam_baku_out,
    ):
        if not jam_out or not jam_baku_out:
            return 0

        return min(
            0,
            AttendanceBusinessEngine.minutes(
                jam_out - jam_baku_out
            ),
        )

    @staticmethod
    def calculate_compensation(
        awal_tlm,
        jam_out,
        jam_baku_out,
        is_libur=False,
        penggantian_tlm1=True,
    ):
        total_tlm = awal_tlm

        if (
            not is_libur
            and penggantian_tlm1
            and 0 < awal_tlm <= 30
            and jam_out
            and jam_baku_out
        ):
            total_psw = (
                AttendanceBusinessEngine.minutes(
                    jam_out - jam_baku_out
                )
            )

            if total_psw > 0:
                total_tlm = max(
                    0,
                    awal_tlm - total_psw,
                )

        return total_tlm

    @staticmethod
    def classify_tlm(total_tlm):
        if total_tlm <= 0:
            return "", 0

        if total_tlm <= 30:
            return "TLM-1", 0.5

        if total_tlm <= 60:
            return "TLM-2", 1

        if total_tlm <= 90:
            return "TLM-3", 1.25

        return "TLM-4", 1.5

    @staticmethod
    def classify_psw(total_psw):
        if total_psw >= 0:
            return "", 0

        psw = abs(total_psw)

        if psw <= 30:
            return "PSW-1", 0.5

        if psw <= 60:
            return "PSW-2", 1

        if psw <= 90:
            return "PSW-3", 1.25

        return "PSW-4", 1.5

    # ========================================================
    # WORK SCHEDULE
    # ========================================================

    @classmethod
    def build_work_schedule(
        cls,
        tanggal,
        std_jam_in,
        std_jam_out,
    ):
        """
        Membentuk datetime jam kerja.

        Cross midnight:
            19:30 -> 04:00
        menjadi:
            H 19:30 -> H+1 04:00
        """

        tanggal = cls._date(tanggal)

        jam_baku_in = cls._build_datetime(
            tanggal,
            std_jam_in,
        )

        jam_baku_out = cls._build_datetime(
            tanggal,
            std_jam_out,
        )

        if (
            jam_baku_in
            and jam_baku_out
            and jam_baku_out <= jam_baku_in
        ):
            jam_baku_out += timedelta(
                days=1
            )

        return (
            jam_baku_in,
            jam_baku_out,
        )

    # ========================================================
    # INDEX BUILDER
    # ========================================================

    @staticmethod
    def build_calendar_index(rows):
        """
        Index kalender:

            YYYY-MM-DD -> row/value
        """

        result = {}

        for row in rows or []:
            key = AttendanceBusinessEngine._row_date(
                row,
                (
                    "TANGGAL",
                    "TGL_KALENDER",
                    "TGL",
                    "tanggal",
                ),
            )

            if key:
                result[key] = row

        return result

    @staticmethod
    def build_load_finger_index(rows):
        """
        Index MF_LOAD_FINGER berdasarkan SHIFT_KERJA.

        Row dengan TGL_MULAI_BERLAKU terbaru
        menjadi kandidat pertama saat resolver digunakan.
        """

        result = {}

        for row in rows or []:
            shift = str(
                AttendanceBusinessEngine._get_value(
                    row,
                    "SHIFT_KERJA",
                )
                or ""
            )

            if not shift:
                continue

            result.setdefault(
                shift,
                []
            ).append(row)

        for shift in result:
            result[shift].sort(
                key=lambda row: (
                    AttendanceBusinessEngine._get_value(
                        row,
                        "TGL_MULAI_BERLAKU",
                    )
                    or date.min
                ),
                reverse=True,
            )

        return result

    @staticmethod
    def build_schedule_index(rows):
        """
        Index jadwal berdasarkan SHIFT_KERJA.

        Tidak melakukan query.
        """

        result = {}

        for row in rows or []:
            shift = str(
                AttendanceBusinessEngine._get_value(
                    row,
                    "SHIFT_KERJA",
                )
                or ""
            )

            if shift:
                result.setdefault(
                    shift,
                    []
                ).append(row)

        for shift in result:
            result[shift].sort(
                key=lambda row: (
                    AttendanceBusinessEngine._get_value(
                        row,
                        "TGL_MULAI_BERLAKU",
                    )
                    or date.min
                ),
                reverse=True,
            )

        return result

    @staticmethod
    def build_potongan_index(rows):
        """
        Index MF_POT.

        Kunci:
            (KATEGORI, TINGKAT)
        """

        result = {}

        for row in rows or []:
            kategori = str(
                AttendanceBusinessEngine._get_value(
                    row,
                    "KATEGORI",
                )
                or ""
            ).strip().upper()

            tingkat = str(
                AttendanceBusinessEngine._get_value(
                    row,
                    "TINGKAT",
                )
                or ""
            ).strip()

            if kategori and tingkat:
                result[
                    (kategori, tingkat)
                ] = row

        return result

    # ========================================================
    # RESOLVER
    # ========================================================

    @staticmethod
    def resolve_effective_row(
        rows,
        work_date,
    ):
        """
        Mengambil master yang berlaku pada tanggal tertentu.

        Rule:
            TGL_MULAI_BERLAKU <= tanggal
            pilih tanggal berlaku terbaru.
        """

        work_date = (
            AttendanceBusinessEngine._date(
                work_date
            )
        )

        candidates = []

        for row in rows or []:
            mulai = (
                AttendanceBusinessEngine._get_value(
                    row,
                    "TGL_MULAI_BERLAKU",
                )
            )

            if mulai is None:
                continue

            mulai = (
                AttendanceBusinessEngine._date(
                    mulai
                )
            )

            if mulai <= work_date:
                candidates.append(
                    (
                        mulai,
                        row,
                    )
                )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return candidates[0][1]

    # ========================================================
    # PRIVATE HELPERS
    # ========================================================

    @staticmethod
    def minutes(delta):
        return delta.total_seconds() / 60

    @staticmethod
    def _build_datetime(
        tanggal,
        value,
    ):
        if value is None:
            return None

        tanggal = (
            AttendanceBusinessEngine._date(
                tanggal
            )
        )

        if isinstance(value, datetime):
            value = value.time()

        return datetime.combine(
            tanggal,
            value,
        )

    @staticmethod
    def _date(value):
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            for fmt in (
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
            ):
                try:
                    return datetime.strptime(
                        value,
                        fmt,
                    ).date()
                except ValueError:
                    continue

        raise ValueError(
            f"Tanggal tidak valid: {value!r}"
        )

    @staticmethod
    def _get_value(
        obj,
        name,
    ):
        if obj is None:
            return None

        if isinstance(obj, dict):
            return obj.get(name)

        return getattr(
            obj,
            name,
            None,
        )

    @staticmethod
    def _get_finger_id(employee):
        value = (
            AttendanceBusinessEngine._get_value(
                employee,
                "FINGER_ID",
            )
        )

        if value is None:
            value = (
                AttendanceBusinessEngine._get_value(
                    employee,
                    "FingerID",
                )
            )

        if value is None:
            return None

        return str(value).strip()

    @staticmethod
    def _get_schedule_value(
        schedule,
        name,
    ):
        return AttendanceBusinessEngine._get_value(
            schedule,
            name,
        )

    @staticmethod
    def _punch(row):
        value = (
            AttendanceBusinessEngine._get_value(
                row,
                "punch",
            )
        )

        if value is None:
            value = (
                AttendanceBusinessEngine._get_value(
                    row,
                    "PUNCH",
                )
            )

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _log_datetime(row):
        value = (
            AttendanceBusinessEngine._get_value(
                row,
                "waktu",
            )
        )

        if value is None:
            value = (
                AttendanceBusinessEngine._get_value(
                    row,
                    "WAKTU",
                )
            )

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
            ):
                try:
                    return datetime.strptime(
                        value,
                        fmt,
                    )
                except ValueError:
                    continue

        raise ValueError(
            f"Waktu fingerprint tidak valid: {value!r}"
        )

    @classmethod
    def _row_date(
        cls,
        row,
        fields,
    ):
        for field_name in fields:
            value = cls._get_value(
                row,
                field_name,
            )

            if value is not None:
                try:
                    return cls._date(
                        value
                    ).isoformat()
                except ValueError:
                    continue

        return None

    @staticmethod
    def _validate_context(context):
        if context is None:
            raise ValueError(
                "AttendanceContext wajib diisi"
            )

        if context.work_date is None:
            raise ValueError(
                "work_date wajib diisi"
            )
