from datetime import datetime, time, timedelta


class AttendanceNormalizationService:
    """
    Orkestrator normalisasi absensi HRIS Reborn.

    Tugas:
    - membedakan Reguler / Shift 1 / Shift 2
    - menangani konteks Piket Siaga Shift 2
    - memilih fingerprint/manual IN dan OUT
    - menyediakan recovery OUT Shift 2
    - menyerahkan perhitungan TLM/PSW kepada
      AttendanceNormalizationEngine

    Service ini TIDAK mengubah database.
    """

    SHIFT2_OUT_RECOVERY_BEFORE = time(12, 0)

    def __init__(self, engine):
        self.engine = engine

    # ================================================================
    # UTILITAS
    # ================================================================

    @staticmethod
    def _parse_waktu(raw):
        if not raw:
            return None

        value = raw.get("waktu")
        if isinstance(value, datetime):
            return value

        if not value:
            value = raw.get("WAKTU")

        if isinstance(value, datetime):
            return value

        if not value:
            return None

        try:
            return datetime.strptime(
                str(value),
                "%Y-%m-%d %H:%M:%S",
            )
        except ValueError:
            return None

    @staticmethod
    def _punch(raw):
        value = (
            raw.get("punch")
            if raw.get("punch") is not None
            else raw.get("PUNCH")
        )

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_manual(raw):
        return str(
            raw.get("device_ip")
            or raw.get("DEVICE_IP")
            or ""
        ).strip() == "999"

    @classmethod
    def _sort(cls, rows):
        return sorted(
            rows,
            key=lambda raw: cls._parse_waktu(raw)
            or datetime.min,
        )

    # ================================================================
    # PAIRING REGULER / SHIFT 1
    # ================================================================

    def pair_regular(self, raw_person):
        """
        Reguler / Shift 1.

        IN  = IN pertama
        OUT = OUT terakhir

        Tidak menggunakan recovery PUNCH 0 -> OUT.
        """

        rows = self._sort(raw_person)

        ins = [
            raw for raw in rows
            if self._punch(raw) == 0
        ]

        outs = [
            raw for raw in rows
            if self._punch(raw) == 1
        ]

        jam_in = (
            self._parse_waktu(ins[0])
            if ins
            else None
        )

        jam_out = (
            self._parse_waktu(outs[-1])
            if outs
            else None
        )

        return jam_in, jam_out

    # ================================================================
    # PAIRING SHIFT 2 PIKET SIAGA
    # ================================================================

    def pair_shift2(
        self,
        raw_person,
        activity_date,
        target_date,
    ):
        """
        Shift 2 Piket Siaga menggunakan window MF_LOAD_FINGER
        melalui AttendanceNormalizationEngine.

        Ini mengikuti HRIS 2013:
        - IN dipilih dari window StartFinger/EndFinger pada H.
        - OUT dipilih dari window StartFingerOut/EndFingerOut pada H+1.
        - Tidak mengubah PUNCH 0 menjadi OUT secara otomatis.
        """
        return self.engine.pair_shift2(
            raw_person=raw_person,
            activity_date=activity_date,
            target_date=target_date,
        )

    # ================================================================
    # RAW YANG DIKONSUMSI SHIFT 2
    # ================================================================

    def shift2_consumed(
        self,
        raw_person,
        activity_date,
        target_date,
    ):
        """
        Mengembalikan RAW yang benar-benar digunakan
        oleh normalisasi Shift 2.

        Pairing dan consumed harus menggunakan business rule
        yang sama agar RAW Shift 2 tidak diproses ulang sebagai reguler.
        """

        activity_date = self.engine._date(activity_date)
        target_date = self.engine._date(target_date)

        jam_in, jam_out = self.pair_shift2(
            raw_person,
            activity_date,
            target_date,
        )

        if not jam_in:
            return set()

        rows = self._sort(raw_person)
        consumed = set()

        # ============================================================
        # IN SHIFT 2
        #
        # Hanya PUNCH 0 yang benar-benar dipilih oleh pair_shift2().
        # ============================================================
        for raw in rows:
            waktu = self._parse_waktu(raw)
            punch = self._punch(raw)

            if (
                punch == 0
                and waktu
                and waktu == jam_in
            ):
                consumed.add(self.raw_key(raw))
                break

        # ============================================================
        # OUT SHIFT 2
        #
        # PUNCH 1 yang dipilih oleh pair_shift2().
        # ============================================================
        if jam_out:
            for raw in rows:
                waktu = self._parse_waktu(raw)
                punch = self._punch(raw)

                if (
                    punch == 1
                    and waktu
                    and waktu == jam_out
                ):
                    consumed.add(self.raw_key(raw))
                    break

            # ========================================================
            # RECOVERY OUT
            #
            # Jika jam_out berasal dari PUNCH 0 H+1, pair_shift2()
            # menggunakannya sebagai recovery.
            # ========================================================
            if not any(
                self._punch(raw) == 1
                and self._parse_waktu(raw) == jam_out
                for raw in rows
            ):
                for raw in rows:
                    waktu = self._parse_waktu(raw)
                    punch = self._punch(raw)

                    if (
                        punch == 0
                        and waktu
                        and waktu == jam_out
                        and waktu.date() == target_date
                        and waktu.time() < self.SHIFT2_OUT_RECOVERY_BEFORE
                    ):
                        consumed.add(self.raw_key(raw))
                        break

        return consumed

    @staticmethod
    def raw_key(raw):
        finger_id = (
            raw.get("finger_id")
            or raw.get("FINGER_ID")
            or ""
        )

        waktu = (
            raw.get("waktu")
            or raw.get("WAKTU")
            or ""
        )

        if isinstance(waktu, datetime):
            waktu = waktu.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        return (
            str(finger_id),
            str(waktu),
        )
