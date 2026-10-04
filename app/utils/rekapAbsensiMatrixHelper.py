from app import db
from datetime import timedelta
from sqlalchemy import text

from app.models.pegawaiModel import Pegawai
from app.models.absensiModel import Absensi
from app.models.kalenderModel import MfKalender
from app.models.jabatanModel import MfJabatan
from app.models.eselonModel import MfEselon
from app.models.golonganModel import MfGolongan

from app.utils.pegawaiHelper import is_pegawai_aktif_periode
from app.utils.pegawaiSortHelper import sort_pegawai_rows


def format_jam_absensi(value):
    if not value:
        return ""
    if (
        hasattr(value, "year")
        and value.year == 1900
        and value.month == 1
        and value.day == 1
    ):
        return ""
    return value.strftime("%H.%M")


def format_status_absensi(status):
    mapping = {
        "DINASLUAR": "DL",
        "DINAS_LUAR": "DL",
        "CUTI": "CT",
        "SAKIT": "S",
        "IJIN": "I",
        "IZIN": "I",
        "ALPA": "A",
        "WFH": "WFH",
    }
    if not status:
        return ""
    return mapping.get(str(status).strip().upper(), str(status))


def _sprin_code_from_absensi(absensi):
    """Ambil kode DL/OP/SD yang dipersist oleh hasil export final."""
    transaction = str(absensi.TRANSAKSI_IN or '').strip().upper()
    if transaction != 'DINASLUAR':
        return ''

    display_code = str(
        absensi.HISTORY_TRANSAKSI_IN or ''
    ).strip().upper()

    if display_code in ('DL', 'OP', 'SD'):
        return display_code

    return 'DL'


def _is_shift2_absensi(absensi):
    """
    Deteksi Shift 2 dari HASIL EXPORT ABSENSI final.

    Sumber kebenaran utama:
      1. HISTORY_TRANSAKSI_IN = SIAGA.
      2. TGL_JAM_IN berada pada tanggal sebelum TglKerja.

    Aturan nomor 2 penting karena hasil export normalisasi Shift 2
    memang menyimpan:
        TglKerja  = H+1
        TglJamIn  = H + jam masuk fingerprint

    Jadi row seperti:
        TglKerja = 2026-09-05
        TglJamIn = 2026-09-04 17:52
        TglJamOut = 2026-09-05 08:27

    harus diperlakukan sebagai satu absensi Shift 2 pada 05-09-2026.
    Ini berlaku universal untuk semua pegawai, tanpa hardcode NIP
    maupun tanggal.

    Tidak ada inferensi Shift-2 dari jam baku >= 18.
    Penentuan Shift-2 harus berasal dari hasil export SIAGA atau
    timestamp IN H-1 yang memang merupakan bentuk penyimpanan
    Shift-2 hasil normalisasi.
    """
    rekap_code = str(
        absensi.HISTORY_TRANSAKSI_IN or ''
    ).strip().upper()

    if rekap_code == 'SIAGA':
        return True

    tgl_kerja = absensi.TGL_KERJA
    tgl_jam_in = absensi.TGL_JAM_IN

    if tgl_kerja and tgl_jam_in:
        try:
            if tgl_jam_in.date() < tgl_kerja.date():
                return True
        except AttributeError:
            pass

    return False


def _is_placeholder_time(value):
    """True untuk jam kosong / sentinel 00:00 yang tidak boleh menang dedupe."""
    if not value:
        return True
    if getattr(value, 'year', None) == 1900:
        return True
    return (
        getattr(value, 'hour', None) == 0
        and getattr(value, 'minute', None) == 0
        and getattr(value, 'second', 0) == 0
    )


def _absensi_rekap_priority(absensi, shift2_keys=None):
    """
    Prioritas record ABSENSI final untuk Rekap.

    StatusID = 3 pada LOG_ACTIVITIY adalah penanda HADIR untuk
    Piket Siaga Shift 2. Untuk key (NIP, H+1) yang ditandai kode 3,
    Rekap wajib mengambil hasil EXPORT ABSENSI yang mempunyai:

        TglKerja = H+1
        TglJamIn = H + jam IN

    Jadi record IN H-1 selalu mengalahkan record reguler 00:00
    pada tanggal H+1.

    LOG_ACTIVITIY hanya dipakai sebagai penanda bisnis Shift 2.
    Jam IN/OUT tetap diambil dari ABSENSI hasil EXPORT normalisasi.
    """
    shift2_keys = shift2_keys or set()
    key = None

    if absensi.TGL_KERJA:
        try:
            # NIP ditambahkan oleh caller melalui atribut sementara.
            key = (
                str(getattr(absensi, '_rekap_nip', '') or '').strip(),
                absensi.TGL_KERJA.date(),
            )
        except AttributeError:
            key = None

    is_marked_shift2 = key in shift2_keys
    is_shift2 = is_marked_shift2 or _is_shift2_absensi(absensi)
    has_in = not _is_placeholder_time(absensi.TGL_JAM_IN)
    has_out = not _is_placeholder_time(absensi.TGL_JAM_OUT)

    # Untuk StatusID=3, yang paling penting adalah IN berasal dari H-1.
    has_h_minus_1_in = (
        bool(absensi.TGL_KERJA)
        and bool(absensi.TGL_JAM_IN)
        and absensi.TGL_JAM_IN.date() < absensi.TGL_KERJA.date()
        and has_in
    )

    if is_marked_shift2 and has_h_minus_1_in:
        return (10, 1 if has_out else 0)

    if is_marked_shift2 and has_in:
        return (9, 1 if has_out else 0)

    if is_shift2 and has_h_minus_1_in:
        return (8, 1 if has_out else 0)

    if is_shift2 and has_in:
        return (7, 1 if has_out else 0)

    if is_shift2 and has_out:
        return (6, 1)

    if has_in:
        return (3, 1 if has_out else 0)

    if has_out:
        return (2, 1)

    if is_shift2:
        return (1, 0)

    return (0, 0)


def _jam_in_rekap(absensi):
    """Rekap menampilkan TGL_JAM_IN final dari ABSENSI apa adanya."""
    return absensi.TGL_JAM_IN


def _warna_absensi(absensi):
    """Warna presentation Rekap berdasarkan hasil final ABSENSI."""
    transaction = str(absensi.TRANSAKSI_IN or '').strip().upper()

    if transaction == 'DINASLUAR':
        return (
            'orange'
            if int(absensi.STATUS_UM or 0) == 1
            else 'dark-blue'
        )

    if transaction == 'WFH':
        return 'wfh'

    rekap_code = str(
        absensi.HISTORY_TRANSAKSI_IN or ''
    ).strip().upper()

    if rekap_code == 'SIAGA' or _is_shift2_absensi(absensi):
        return 'siaga'

    return 'normal'


def _calendar_rows(tgl_awal, tgl_akhir):
    rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA >= tgl_awal)
        .filter(MfKalender.TGL_KERJA <= tgl_akhir)
        .order_by(MfKalender.TGL_KERJA.asc())
        .all()
    )

    if rows:
        return rows

    generated = []
    d = tgl_awal
    while d <= tgl_akhir:
        generated.append(type("CalendarRow", (), {
            "TGL_KERJA": d,
            "IS_LIBUR": "Y" if d.weekday() >= 5 else "N",
            "KET": None,
        })())
        d += timedelta(days=1)
    return generated


def _is_holiday(row):
    d = row.TGL_KERJA
    if d.weekday() in (5, 6):
        return True
    if str(row.IS_LIBUR or "N").upper() == "Y":
        return True
    if d.strftime("%m-%d") in ("01-01", "08-17", "12-25"):
        return True
    return False


def _active_pegawai(unit_ids, tgl_awal, tgl_akhir, pegawai_nips=None):
    query = (
        Pegawai.query
        .outerjoin(MfJabatan, Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID)
        .outerjoin(MfEselon, Pegawai.ESELON == MfEselon.ESELON)
        .outerjoin(MfGolongan, Pegawai.GOL == MfGolongan.GOL)
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(Pegawai.TGL_MASUK <= tgl_akhir)
    )

    if pegawai_nips:
        query = query.filter(Pegawai.NIP.in_(pegawai_nips))

    rows = query.all()
    rows = [
        p for p in rows
        if is_pegawai_aktif_periode(p, tgl_awal, tgl_akhir)
    ]
    return sort_pegawai_rows(rows)


def generate_rekap_absensi_matrix(unit_ids, tgl_awal, tgl_akhir, pegawai_nips=None):
    """Rekap Absensi Bulanan adalah READ-ONLY consumer dari ABSENSI final."""
    kalender_rows = _calendar_rows(tgl_awal, tgl_akhir)
    pegawai_rows = _active_pegawai(
        unit_ids,
        tgl_awal,
        tgl_akhir,
        pegawai_nips=pegawai_nips,
    )

    absensi_query = (
        db.session.query(Absensi, Pegawai)
        .join(Pegawai, Absensi.FINGER_ID == Pegawai.FINGER_ID)
        .filter(
            Absensi.TGL_KERJA >= tgl_awal,
            Absensi.TGL_KERJA <= tgl_akhir,
        )
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
    )

    if pegawai_nips:
        absensi_query = absensi_query.filter(
            Pegawai.NIP.in_(pegawai_nips)
        )

    absensi_rows = absensi_query.all()

    # ============================================================
    # PENANDA SIAGA SHIFT 2
    #
    # LOG_ACTIVITIY adalah sumber penentu bahwa pegawai benar-benar
    # SIAGA Shift 2 pada H. StatusID = 3 berarti HADIR.
    #
    # Target absensi selalu H+1. Ini hanya penanda pemilihan record;
    # jam IN/OUT tetap diambil dari ABSENSI hasil EXPORT normalisasi.
    # ============================================================
    shift2_rows = db.session.execute(
        text("""
            SELECT NIP, ActivityDate
            FROM LOG_ACTIVITIY
            WHERE Activity = 'Piket Siaga'
              AND Shift = '2'
              AND StatusID = 3
              AND ActivityDate >= :activity_awal
              AND ActivityDate <= :activity_akhir
        """),
        {
            'activity_awal': (tgl_awal - timedelta(days=1)).date(),
            'activity_akhir': (tgl_akhir - timedelta(days=1)).date(),
        }
    ).mappings().all()

    # (NIP, TglKerja) -> ActivityDate (tanggal H).
    #
    # IN Shift-2 HARUS berasal dari H, sedangkan TglKerja Rekap adalah
    # H+1. Jangan biarkan row reguler 00:00 menjadi wakil Shift-2 hanya
    # karena row tersebut kebetulan punya TglKerja yang sama.
    shift2_keys = set()
    shift2_activity_dates = {}

    for row in shift2_rows:
        nip = str(row['NIP'] or '').strip()
        activity_date = row['ActivityDate']

        if not nip or not activity_date:
            continue

        if hasattr(activity_date, 'date'):
            activity_date = activity_date.date()

        target_date = activity_date + timedelta(days=1)

        if tgl_awal.date() <= target_date <= tgl_akhir.date():
            key = (nip, target_date)
            shift2_keys.add(key)
            shift2_activity_dates[key] = activity_date

    # Kumpulkan SEMUA hasil EXPORT ABSENSI terlebih dahulu.
    # Rekap tidak melakukan pairing fingerprint lagi.
    absensi_candidates = {}

    for absensi, pegawai in absensi_rows:
        if not absensi.TGL_KERJA:
            continue

        key = (
            str(pegawai.NIP or '').strip(),
            absensi.TGL_KERJA.date(),
        )

        # _absensi_rekap_priority membutuhkan NIP untuk mencocokkan
        # StatusID=3. Jangan mengubah data database; hanya tempel
        # metadata sementara pada object SQLAlchemy selama proses request.
        absensi._rekap_nip = key[0]

        absensi_candidates.setdefault(key, []).append(absensi)

    absensi_index = {}

    # ============================================================
    # WAJIB: PILIH HASIL EXPORT SHIFT-2 UNTUK SETIAP KODE 3
    #
    # LOG_ACTIVITIY StatusID=3 adalah daftar pegawai yang HADIR
    # Piket Siaga Shift-2.
    #
    # Untuk setiap (NIP, H+1):
    #   - cari hasil EXPORT ABSENSI pada TglKerja = H+1
    #   - IN wajib bertanggal H
    #   - OUT bertanggal H+1
    #
    # Row reguler 00:00 pada H+1 TIDAK BOLEH menang.
    # Ini berlaku untuk SEMUA pegawai dan SEMUA tanggal kode 3.
    # ============================================================
    for key, activity_date in shift2_activity_dates.items():
        candidates = absensi_candidates.get(key, [])

        # Hasil export final Shift-2 pada ABSENSI menggunakan:
        #   TglKerja = H+1
        #   TglJamIn = H+1 + jam IN
        #   TglJamOut = H+1 + jam OUT
        #   HistoryTransaksiIn = SIAGA
        #
        # LOG_ACTIVITIY hanya menentukan bahwa key (NIP, H+1)
        # memang merupakan Shift-2 HADIR. Jam tetap 100% berasal
        # dari ABSENSI final.
        # ABSENSI final adalah satu-satunya sumber jam untuk Rekap.
        # LOG_ACTIVITIY hanya menentukan bahwa (NIP, H+1) adalah
        # Shift-2 HADIR. Jangan menyaring berdasarkan tanggal TGL_JAM_IN.
        # Pada hasil export saat ini TglKerja sudah = H+1 dan jam IN/OUT
        # tersimpan pada row ABSENSI tersebut.
        shift2_export = [
            candidate
            for candidate in candidates
            if not (
                _is_placeholder_time(candidate.TGL_JAM_IN)
                and _is_placeholder_time(candidate.TGL_JAM_OUT)
            )
        ]

        if shift2_export:
            # Prioritas absolut: row SIAGA dengan jam aktual.
            # Jika tidak ada, pilih row dengan IN/OUT aktual terbanyak.
            selected = max(
                shift2_export,
                key=lambda candidate: (
                    1 if str(
                        candidate.HISTORY_TRANSAKSI_IN or ''
                    ).strip().upper() == 'SIAGA' else 0,
                    1 if not _is_placeholder_time(candidate.TGL_JAM_IN) else 0,
                    1 if not _is_placeholder_time(candidate.TGL_JAM_OUT) else 0,
                ),
            )
            absensi_index[key] = selected


    # ============================================================
    # NON-SIAGA: pilih hasil EXPORT reguler dengan prioritas lama.
    # Untuk key yang sudah dimiliki kode 3, hasil di atas sudah final
    # dan tidak boleh ditimpa oleh row reguler.
    # ============================================================
    for key, candidates in absensi_candidates.items():
        if key in shift2_activity_dates:
            continue

        for absensi in candidates:
            current = absensi_index.get(key)

            candidate_priority = _absensi_rekap_priority(
                absensi,
                shift2_keys=shift2_keys,
            )

            current_priority = (
                _absensi_rekap_priority(
                    current,
                    shift2_keys=shift2_keys,
                )
                if current is not None
                else None
            )

            if current is None or candidate_priority > current_priority:
                absensi_index[key] = absensi

    matrix = {}

    for pegawai in pegawai_rows:
        nip = str(pegawai.NIP or '').strip()
        matrix[nip] = {}

        for kalender in kalender_rows:
            tanggal_obj = kalender.TGL_KERJA
            tanggal = tanggal_obj.strftime('%Y-%m-%d')
            key = (nip, tanggal_obj.date())

            cell = {
                'status': 'LIBUR' if _is_holiday(kalender) else '',
                'jam_in': None,
                'jam_out': None,
                'keterangan': kalender.KET or '',
                'sumber_absensi': '',
                'warna': 'holiday' if _is_holiday(kalender) else '',
                'layer': 'KALENDER',
                'status_um': None,
                'siaga_shift': None,
            }

            absensi = absensi_index.get(key)

            if absensi:
                transaksi_in = str(absensi.TRANSAKSI_IN or '').strip().upper()
                status = format_status_absensi(transaksi_in)

                if transaksi_in == 'DINASLUAR':
                    status = _sprin_code_from_absensi(absensi)
                elif transaksi_in in ('CUTI', 'SAKIT'):
                    tingkat = str(
                        absensi.TINGKAT_TLM
                        or absensi.TINGKAT_PSW
                        or ''
                    ).strip().upper()
                    if tingkat:
                        status = tingkat
                elif status in ('', 'LOGFP', 'MANUAL', 'INJECT'):
                    status = 'HADIR'

                cell.update({
                    'status': status,
                    'jam_in': _jam_in_rekap(absensi),
                    'jam_out': absensi.TGL_JAM_OUT,
                    'sumber_absensi': 'ABSENSI',
                    'warna': _warna_absensi(absensi),
                    'layer': 'ABSENSI',
                    'status_um': absensi.STATUS_UM,
                    'siaga_shift': 2 if _is_shift2_absensi(absensi) else None,
                })

            if (
                _is_holiday(kalender)
                and cell.get('warna') not in (
                    'siaga',
                    'blue',
                    'dark-blue',
                    'orange',
                )
            ):
                cell['warna'] = 'holiday'

            matrix[nip][tanggal] = cell

    return {
        'kalender': kalender_rows,
        'pegawai': pegawai_rows,
        'matrix': matrix,
    }
