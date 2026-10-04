from app import db
from datetime import timedelta

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
    """Deteksi Shift 2 hanya dari metadata final ABSENSI."""
    rekap_code = str(
        absensi.HISTORY_TRANSAKSI_IN or ''
    ).strip().upper()

    if rekap_code == 'SIAGA':
        return True

    value = absensi.TGL_JAM_BAKU_IN
    return bool(
        value
        and getattr(value, 'hour', 0) >= 18
    )


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


def _absensi_rekap_priority(absensi):
    """
    Prioritas ketika satu NIP + TglKerja mempunyai beberapa ABSENSI
    karena pegawai memiliki lebih dari satu FingerID.

    Shift 2/SIAGA harus menang atas record reguler pada tanggal target.
    Setelah itu prioritaskan record yang mempunyai jam aktual non-00:00.
    """
    score = 0

    if _is_shift2_absensi(absensi):
        score += 100

    if not _is_placeholder_time(absensi.TGL_JAM_IN):
        score += 20

    if not _is_placeholder_time(absensi.TGL_JAM_OUT):
        score += 10

    if str(absensi.HISTORY_TRANSAKSI_IN or '').strip():
        score += 2

    if str(absensi.TRANSAKSI_IN or '').strip():
        score += 1

    return score


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


def _active_pegawai(unit_ids, tgl_awal, tgl_akhir):
    rows = (
        Pegawai.query
        .outerjoin(MfJabatan, Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID)
        .outerjoin(MfEselon, Pegawai.ESELON == MfEselon.ESELON)
        .outerjoin(MfGolongan, Pegawai.GOL == MfGolongan.GOL)
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(Pegawai.TGL_MASUK <= tgl_akhir)
        .all()
    )
    rows = [
        p for p in rows
        if is_pegawai_aktif_periode(p, tgl_awal, tgl_akhir)
    ]
    return sort_pegawai_rows(rows)


def generate_rekap_absensi_matrix(unit_ids, tgl_awal, tgl_akhir):
    """Rekap Absensi Bulanan adalah READ-ONLY consumer dari ABSENSI final."""
    kalender_rows = _calendar_rows(tgl_awal, tgl_akhir)
    pegawai_rows = _active_pegawai(unit_ids, tgl_awal, tgl_akhir)

    absensi_rows = (
        db.session.query(Absensi, Pegawai)
        .join(Pegawai, Absensi.FINGER_ID == Pegawai.FINGER_ID)
        .filter(
            Absensi.TGL_KERJA >= tgl_awal,
            Absensi.TGL_KERJA <= tgl_akhir,
        )
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .all()
    )

    absensi_index = {}

    for absensi, pegawai in absensi_rows:
        if not absensi.TGL_KERJA:
            continue

        key = (
            str(pegawai.NIP or '').strip(),
            absensi.TGL_KERJA.date(),
        )
        current = absensi_index.get(key)

        # Satu pegawai dapat mempunyai beberapa FingerID. Jangan biarkan
        # urutan query acak menimpa record Shift 2 yang sudah benar dengan
        # record reguler/sentinel 00:00 pada NIP + tanggal kerja yang sama.
        if (
            current is None
            or _absensi_rekap_priority(absensi)
            > _absensi_rekap_priority(current)
        ):
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
