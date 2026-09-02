from datetime import datetime, timedelta


class AttendanceNormalizationEngine:
    """
    Engine normalisasi absensi HRIS Reborn.

    Sumber aturan:
    - MF_JAM_KERJA  : jam baku + aturan kompensasi TLM-1
    - MF_LOAD_FINGER: window fingerprint
    - MF_POT        : kategori/potongan TLM/PSW
    - MF_KALENDER   : hari libur
    - FINGER_HARVEST_RAW : fingerprint aktual
    - LOG_ACTIVITIY  : penentuan petugas Siaga Shift 2

    Engine ini TIDAK mengubah database.
    """

    def __init__(
        self,
        jam_kerja=None,
        potongan=None,
        load_finger=None,
        kalender=None,
        default_tdk_check=180,
    ):
        self.jam_kerja = jam_kerja or []
        self.potongan = potongan or []
        self.load_finger = load_finger or []
        self.kalender = kalender or {}
        self.default_tdk_check = float(default_tdk_check)

        self.xdefault = self.default_tdk_check + 1

    # ================================================================
    # UTILITAS
    # ================================================================

    @staticmethod
    def _date(value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        return value

    @staticmethod
    def _time(value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.time()

        return value

    @staticmethod
    def _same_or_before(value, target):
        value = AttendanceNormalizationEngine._date(value)
        target = AttendanceNormalizationEngine._date(target)

        return (
            value is not None
            and target is not None
            and value <= target
        )

    # ================================================================
    # SHIFT HARI
    # ================================================================

    def resolve_shift_hari(self, tgl_kerja):
        """
        MF_JAM_KERJA:
            Shift 1 = Senin-Kamis
            Shift 2 = Jumat
        """

        tgl_kerja = self._date(tgl_kerja)

        if tgl_kerja.weekday() == 4:
            return '2'

        return '1'

    # ================================================================
    # MASTER JAM KERJA
    # ================================================================

    def resolve_jam_kerja(
        self,
        tgl_kerja,
        shift_kerja='1',
    ):
        """
        Ambil konfigurasi MF_JAM_KERJA terbaru yang berlaku.

        shift_kerja:
            1 = reguler
            2 = siaga
        """

        tgl_kerja = self._date(tgl_kerja)

        shift = self.resolve_shift_hari(tgl_kerja)

        kandidat = []

        for jk in self.jam_kerja:
            if str(
                getattr(jk, 'SHIFT', '') or ''
            ) != str(shift):
                continue

            if str(
                getattr(jk, 'SHIFT_KERJA', '') or ''
            ) != str(shift_kerja):
                continue

            mulai = getattr(
                jk,
                'TGL_MULAI_BERLAKU',
                None,
            )

            if not self._same_or_before(
                mulai,
                tgl_kerja,
            ):
                continue

            kandidat.append(jk)

        if not kandidat:
            return None

        kandidat.sort(
            key=lambda x: (
                self._date(
                    getattr(
                        x,
                        'TGL_MULAI_BERLAKU',
                        None,
                    )
                ) or datetime.min.date(),
                getattr(
                    x,
                    'IDJKERJA',
                    0,
                ) or 0,
            ),
            reverse=True,
        )

        return kandidat[0]

    # ================================================================
    # JAM BAKU
    # ================================================================

    def resolve_jam_baku(
        self,
        tgl_kerja,
        jk,
    ):
        if not jk:
            return None, None

        in_time = self._time(
            getattr(jk, 'STD_JAM_IN', None)
        )

        out_time = self._time(
            getattr(jk, 'STD_JAM_OUT', None)
        )

        baku_in = (
            datetime.combine(
                self._date(tgl_kerja),
                in_time,
            )
            if in_time
            else None
        )

        baku_out = (
            datetime.combine(
                self._date(tgl_kerja),
                out_time,
            )
            if out_time
            else None
        )

        # Shift malam:
        # OUT berada pada hari berikutnya.
        if (
            baku_in
            and baku_out
            and baku_out <= baku_in
        ):
            baku_out += timedelta(days=1)

        return baku_in, baku_out

    # ================================================================
    # WINDOW FINGERPRINT
    # ================================================================

    def resolve_load_finger(
        self,
        tgl_kerja,
        shift_kerja='1',
    ):
        """
        MF_LOAD_FINGER menentukan window fingerprint,
        BUKAN jam baku kerja.
        """

        tgl_kerja = self._date(tgl_kerja)

        kandidat = []

        for lf in self.load_finger:
            if str(
                getattr(lf, 'SHIFT_KERJA', '') or ''
            ) != str(shift_kerja):
                continue

            mulai = self._date(
                getattr(
                    lf,
                    'TGL_MULAI_BERLAKU',
                    None,
                )
            )

            if mulai is None or mulai > tgl_kerja:
                continue

            kandidat.append(lf)

        if not kandidat:
            return None

        kandidat.sort(
            key=lambda x: (
                self._date(
                    getattr(
                        x,
                        'TGL_MULAI_BERLAKU',
                        None,
                    )
                ) or datetime.min.date(),
                getattr(
                    x,
                    'TRAKSAKSI_ID',
                    0,
                ) or 0,
            ),
            reverse=True,
        )

        return kandidat[0]

    # ================================================================
    # NORMALISASI PUNCH
    # ================================================================

    @staticmethod
    def punch_status(raw):
        punch = raw.get('punch')

        if punch == 0:
            return 'IN'

        if punch == 1:
            return 'OUT'

        status = str(
            raw.get('status') or ''
        ).strip().upper()

        if status in ('IN', 'OUT'):
            return status

        return None

    # ================================================================
    # PAIRING SHIFT 1
    # ================================================================

    def pair_regular(
        self,
        logs,
    ):
        """
        Shift 1:
            IN  = punch 0 pertama
            OUT = punch 1 terakhir
        """

        valid = [
            r for r in logs
            if self.punch_status(r)
        ]

        valid.sort(
            key=lambda r: r.get('waktu') or ''
        )

        logs_in = [
            r for r in valid
            if self.punch_status(r) == 'IN'
        ]

        logs_out = [
            r for r in valid
            if self.punch_status(r) == 'OUT'
        ]

        jam_in = self._parse_waktu(
            logs_in[0]
            if logs_in
            else None
        )

        jam_out = self._parse_waktu(
            logs_out[-1]
            if logs_out
            else None
        )

        return jam_in, jam_out

    # ================================================================
    # PAIRING SHIFT 2
    # ================================================================

    def pair_shift2(
        self,
        raw_person,
        activity_date,
        target_date,
    ):
        """
        Shift 2:
            IN  = window fingerprint pada tanggal SIAGA
            OUT = window fingerprint pada tanggal berikutnya
        """

        # ------------------------------------------------------------
        # MF_LOAD_FINGER Shift 2 mengikuti TANGGAL MULAI SIAGA.
        #
        # ActivityDate = H
        #   IN  fingerprint = H
        #   OUT fingerprint = H+1
        #
        # target_date adalah tanggal record ABSENSI (H+1),
        # sehingga TIDAK boleh dipakai untuk memilih master
        # MF_LOAD_FINGER.
        # ------------------------------------------------------------
        load_finger = self.resolve_load_finger(
            activity_date,
            '2',
        )

        if not load_finger:
            return None, None

        activity_date = self._date(
            activity_date
        )

        target_date = self._date(
            target_date
        )

        start_in = self._combine_config(
            activity_date,
            getattr(
                load_finger,
                'START_FINGER',
                None,
            ),
        )

        end_in = self._combine_config(
            activity_date,
            getattr(
                load_finger,
                'END_FINGER',
                None,
            ),
        )

        start_out = self._combine_config(
            target_date,
            getattr(
                load_finger,
                'START_FINGER_OUT',
                None,
            ),
        )

        end_out = self._combine_config(
            target_date,
            getattr(
                load_finger,
                'END_FINGER_OUT',
                None,
            ),
        )

        shift2_in = []
        shift2_out = []

        for raw in raw_person:

            waktu = self._parse_waktu(raw)

            if not waktu:
                continue

            # RAW SQL menggunakan PUNCH, sedangkan RAW hasil
            # grouping menggunakan punch.
            punch = (
                raw.get('punch')
                if raw.get('punch') is not None
                else raw.get('PUNCH')
            )

            if (
                punch == 0
                and start_in
                and end_in
                and start_in <= waktu <= end_in
            ):
                shift2_in.append(raw)

            elif (
                punch == 1
                and start_out
                and end_out
                and start_out <= waktu <= end_out
            ):
                shift2_out.append(raw)

        shift2_in.sort(
            key=lambda r: r.get('waktu') or ''
        )

        shift2_out.sort(
            key=lambda r: r.get('waktu') or ''
        )

        jam_in = self._parse_waktu(
            shift2_in[0]
            if shift2_in
            else None
        )

        jam_out = self._parse_waktu(
            shift2_out[-1]
            if shift2_out
            else None
        )

        return jam_in, jam_out

    # ================================================================
    # PERHITUNGAN TLM
    # ================================================================

    def calculate_tlm(
        self,
        jam_in,
        baku_in,
    ):
        if not jam_in or not baku_in:
            return self.xdefault

        return max(
            0,
            (
                jam_in - baku_in
            ).total_seconds() / 60,
        )

    # ================================================================
    # PERHITUNGAN PSW
    # ================================================================

    def calculate_psw(
        self,
        jam_out,
        baku_out,
    ):
        if not jam_out or not baku_out:
            return -1 * self.xdefault

        return min(
            0,
            (
                jam_out - baku_out
            ).total_seconds() / 60,
        )

    # ================================================================
    # KOMPENSASI TLM-1
    # ================================================================

    def calculate_compensation(
        self,
        awal_tlm,
        jam_out,
        baku_out,
        jk,
        is_libur=False,
    ):
        if is_libur:
            return awal_tlm

        if not (
            0 < awal_tlm <= 30
        ):
            return awal_tlm

        penggantian = str(
            getattr(
                jk,
                'PENGGANTIAN_TLM1',
                'Y',
            ) or 'Y'
        ).strip().upper()

        if penggantian == 'N':
            return awal_tlm

        if not jam_out or not baku_out:
            return awal_tlm

        tambahan_pulang = max(
            0,
            (
                jam_out - baku_out
            ).total_seconds() / 60,
        )

        return max(
            0,
            awal_tlm - tambahan_pulang,
        )

    # ================================================================
    # KATEGORI / POTONGAN
    # ================================================================

    def resolve_penalty(
        self,
        total_tlm,
        total_psw,
        tgl_kerja,
    ):
        """
        Menentukan kategori TLM / PSW berdasarkan BUSINESS RULE HRIS.

        TLM:
            0       -> tidak ada
            1 - 30  -> TLM-1
            31 - 60 -> TLM-2
            61 - 90 -> TLM-3
            > 90    -> TLM-4

        PSW:
            0         -> tidak ada
            -1 - -30  -> PSW-1
            -31 - -60 -> PSW-2
            -61 - -90 -> PSW-3
            <= -91   -> PSW-4

        RANGE_AWAL / RANGE_AKHIR MF_POT TIDAK digunakan
        untuk menentukan kategori karena data legacy memiliki
        overlap historis.

        MF_POT hanya digunakan untuk mengambil PERSEN_POT
        dari kategori yang sudah ditentukan.
        """

        total_tlm = float(total_tlm or 0)
        total_psw = float(total_psw or 0)

        tgl_kerja = self._date(tgl_kerja)

        tk_tlm = ''
        pot_tlm = 0

        tk_psw = ''
        pot_psw = 0

        # ============================================================
        # TLM
        # ============================================================

        if total_tlm > 0:

            if total_tlm <= 30:
                tk_tlm = 'TLM-1'

            elif total_tlm <= 60:
                tk_tlm = 'TLM-2'

            elif total_tlm <= 90:
                tk_tlm = 'TLM-3'

            else:
                tk_tlm = 'TLM-4'

        # ============================================================
        # PSW
        # ============================================================

        if total_psw < 0:

            if total_psw >= -30:
                tk_psw = 'PSW-1'

            elif total_psw >= -60:
                tk_psw = 'PSW-2'

            elif total_psw >= -90:
                tk_psw = 'PSW-3'

            else:
                tk_psw = 'PSW-4'

        # ============================================================
        # AMBIL PERSENTASE TLM DARI MF_POT
        # ============================================================

        if tk_tlm:

            kandidat_tlm = []

            for pot in self.potongan:

                kategori = str(
                    getattr(
                        pot,
                        'KATEGORI',
                        '',
                    ) or ''
                ).strip().upper()

                tingkat = str(
                    getattr(
                        pot,
                        'TINGKAT',
                        '',
                    ) or ''
                ).strip().upper()

                if kategori != 'TLM':
                    continue

                if tingkat != tk_tlm:
                    continue

                mulai = self._date(
                    getattr(
                        pot,
                        'TGL_MULAI',
                        None,
                    )
                )

                if (
                    mulai
                    and tgl_kerja
                    and mulai > tgl_kerja
                ):
                    continue

                kandidat_tlm.append(pot)

            if kandidat_tlm:

                kandidat_tlm.sort(
                    key=lambda x: (
                        self._date(
                            getattr(
                                x,
                                'TGL_MULAI',
                                None,
                            )
                        ) or datetime.min.date()
                    ),
                    reverse=True,
                )

                pot_tlm = (
                    getattr(
                        kandidat_tlm[0],
                        'PERSEN_POT',
                        0,
                    ) or 0
                )

        # ============================================================
        # AMBIL PERSENTASE PSW DARI MF_POT
        # ============================================================

        if tk_psw:

            kandidat_psw = []

            for pot in self.potongan:

                kategori = str(
                    getattr(
                        pot,
                        'KATEGORI',
                        '',
                    ) or ''
                ).strip().upper()

                tingkat = str(
                    getattr(
                        pot,
                        'TINGKAT',
                        '',
                    ) or ''
                ).strip().upper()

                if kategori != 'PSW':
                    continue

                if tingkat != tk_psw:
                    continue

                mulai = self._date(
                    getattr(
                        pot,
                        'TGL_MULAI',
                        None,
                    )
                )

                if (
                    mulai
                    and tgl_kerja
                    and mulai > tgl_kerja
                ):
                    continue

                kandidat_psw.append(pot)

            if kandidat_psw:

                kandidat_psw.sort(
                    key=lambda x: (
                        self._date(
                            getattr(
                                x,
                                'TGL_MULAI',
                                None,
                            )
                        ) or datetime.min.date()
                    ),
                    reverse=True,
                )

                pot_psw = (
                    getattr(
                        kandidat_psw[0],
                        'PERSEN_POT',
                        0,
                    ) or 0
                )

        return (
            tk_tlm,
            pot_tlm,
            tk_psw,
            pot_psw,
        )

    # ================================================================
    # NORMALIZE ONE ROW
    # ================================================================

    def normalize_row(
        self,
        *,
        nip,
        finger_id,
        nama,
        gol,
        unit_kerja,
        tgl_kerja,
        jam_in,
        jam_out,
        shift_kerja='1',
        is_libur=False,
        tgl_jam_baku=None,
    ):
        # ------------------------------------------------------------
        # Tanggal ABSENSI dan tanggal JAM BAKU dapat berbeda.
        #
        # Shift 1:
        #   tgl_kerja    = tanggal absensi
        #   tgl_jam_baku = tanggal yang sama
        #
        # Shift 2 Siaga:
        #   tgl_kerja    = H+1
        #   tgl_jam_baku = H (tanggal mulai siaga)
        #
        # Ini penting karena Shift 2 bekerja lintas tengah malam.
        # ------------------------------------------------------------

        tgl_kerja = self._date(tgl_kerja)

        if tgl_jam_baku is None:
            tgl_jam_baku = tgl_kerja
        else:
            tgl_jam_baku = self._date(
                tgl_jam_baku
            )

        jk = self.resolve_jam_kerja(
            tgl_jam_baku,
            shift_kerja,
        )

        if not jk:
            return None

        baku_in, baku_out = (
            self.resolve_jam_baku(
                tgl_jam_baku,
                jk,
            )
        )

        awal_tlm = self.calculate_tlm(
            jam_in,
            baku_in,
        )

        total_psw = self.calculate_psw(
            jam_out,
            baku_out,
        )

        total_tlm = (
            self.calculate_compensation(
                awal_tlm,
                jam_out,
                baku_out,
                jk,
                is_libur,
            )
        )

        if is_libur:
            tk_tlm = ''
            pot_tlm = 0
            tk_psw = ''
            pot_psw = 0
        else:
            # ========================================================
            # KATEGORI TLM DITENTUKAN DARI AWAL_TLM
            #
            # Kompensasi TLM-1 hanya mengurangi NILAI total_tlm.
            # Kompensasi tidak boleh mengubah kategori.
            #
            # Contoh:
            #   awal_tlm  = 10 menit -> TLM-1
            #   kompensasi = 8 menit
            #   total_tlm = 2 menit
            #
            # Hasil tetap:
            #   TLM-1
            # ========================================================

            (
                tk_tlm,
                pot_tlm,
                _unused_tk_psw,
                _unused_pot_psw,
            ) = self.resolve_penalty(
                total_tlm,
                0,
                tgl_kerja,
            )

            (
                _,
                _,
                tk_psw,
                pot_psw,
            ) = self.resolve_penalty(
                0,
                total_psw,
                tgl_kerja,
            )

        return {
            'finger_id': str(
                finger_id or ''
            ),
            'nip': str(
                nip or ''
            ),
            'nama': nama or '',
            'gol': gol or '',
            'unit_kerja': unit_kerja or '',
            'tgl_kerja': tgl_kerja.strftime(
                '%Y-%m-%d'
            ),
            'hari': tgl_kerja.strftime(
                '%A'
            ),
            'shift': (
                self.resolve_shift_hari(
                    tgl_kerja
                )
            ),
            'shift_kerja': str(
                shift_kerja
            ),
            'jam_baku_in': (
                baku_in.strftime('%H:%M')
                if baku_in
                else ''
            ),
            'jam_baku_out': (
                baku_out.strftime('%H:%M')
                if baku_out
                else ''
            ),
            'jam_in': (
                jam_in.strftime('%H:%M:%S')
                if jam_in
                else '00:00:00'
            ),
            'jam_out': (
                jam_out.strftime('%H:%M:%S')
                if jam_out
                else '00:00:00'
            ),
            'is_valid_in': bool(jam_in),
            'is_valid_out': bool(jam_out),
            'is_libur': (
                'LIBUR'
                if is_libur
                else 'TDKLIBUR'
            ),
            'awal_tlm': round(
                awal_tlm,
                2,
            ),
            'total_tlm': round(
                total_tlm,
                2,
            ),
            'tingkat_tlm': tk_tlm,
            'persen_pot_tlm': pot_tlm,
            'total_psw': round(
                total_psw,
                2,
            ),
            'tingkat_psw': tk_psw,
            'persen_pot_psw': pot_psw,
        }

    # ================================================================
    # PRIVATE
    # ================================================================

    @staticmethod
    def _parse_waktu(raw):
        if not raw:
            return None

        # RAW fingerprint dapat berasal dari:
        #
        # 1. hasil grouping controller -> 'waktu'
        # 2. hasil SQL FINGER_HARVEST_RAW -> 'WAKTU'
        #
        # Engine menerima keduanya agar tidak terjadi perbedaan
        # struktur data antar jalur normalisasi.

        waktu = (
            raw.get('waktu')
            if raw.get('waktu') is not None
            else raw.get('WAKTU')
        )

        if isinstance(waktu, datetime):
            return waktu

        if not waktu:
            return None

        try:
            return datetime.strptime(
                str(waktu),
                '%Y-%m-%d %H:%M:%S',
            )
        except ValueError:
            return None

    @staticmethod
    def _combine_config(
        base_date,
        value,
    ):
        if value is None:
            return None

        base_date = (
            base_date.date()
            if isinstance(
                base_date,
                datetime,
            )
            else base_date
        )

        value_time = (
            value.time()
            if isinstance(
                value,
                datetime,
            )
            else value
        )

        return datetime.combine(
            base_date,
            value_time,
        )
