# app/controllers/dashboard_1InfografisController.py
from datetime import date

from flask import render_template

from app.models.pegawaiModel import Pegawai
from app.models.unitKerjaModel import MfUnitKerja
from app.utils.pegawaiHelper import get_operational_pegawai_query


def _calculate_age(birth_date, today):
    if not birth_date:
        return None

    try:
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age if age >= 0 else None
    except (AttributeError, TypeError):
        return None


def _normalize_gender(value):
    value = str(value or '').strip().upper()

    if value in ('L', 'LAKI-LAKI', 'LAKI LAKI', 'LAKI'):
        return 'Laki-laki'
    if value in ('P', 'PEREMPUAN', 'WANITA'):
        return 'Perempuan'
    return 'Belum diisi'


def _normalize_status(status):
    if status == 1:
        return 'PNS'
    if status == 2:
        return 'Non PNS'
    return 'Lainnya'


def dashboard_infografis():
    """
    Dashboard UMUM - Infografis Pegawai.

    Sumber data langsung dari tabel legacy PEGAWAI.
    Halaman ini read-only dan tidak membuat tabel/statistik baru.
    """
    today = date.today()

    # Populasi dashboard = Pegawai Operasional HRIS.
    # Single Source of Truth:
    #   PEGAWAI.IS_KELUAR = 'N'
    #   MF_UNIT_KERJA.IS_USE = 'Y'
    # Pegawai dengan Unit Kerja nonaktif tidak masuk statistik.
    pegawai_rows = get_operational_pegawai_query().all()

    unit_rows = (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_USE == 'Y')
        .all()
    )
    unit_map = {
        str(row.UNIT_KERJA_ID).strip(): str(
            row.NAMA_UNIT_KERJA or ''
        ).strip()
        for row in unit_rows
        if row.UNIT_KERJA_ID is not None
    }

    total = len(pegawai_rows)
    pns = sum(1 for row in pegawai_rows if row.STATUS_PEG == 1)
    non_pns = sum(1 for row in pegawai_rows if row.STATUS_PEG == 2)

    gender_counts = {
        'Laki-laki': 0,
        'Perempuan': 0,
        'Belum diisi': 0,
    }

    status_counts = {
        'PNS': pns,
        'Non PNS': non_pns,
        'Lainnya': max(total - pns - non_pns, 0),
    }

    age_buckets = {
        '< 30 Tahun': 0,
        '30-39 Tahun': 0,
        '40-49 Tahun': 0,
        '50-59 Tahun': 0,
        '60 Tahun': 0,
    }
    age_unknown = 0

    unit_counts = {}

    for row in pegawai_rows:
        gender = _normalize_gender(row.JENIS_KEL)
        gender_counts[gender] += 1

        age = _calculate_age(row.TGL_LAHIR, today)
        if age is None:
            age_unknown += 1
        elif age < 30:
            age_buckets['< 30 Tahun'] += 1
        elif age < 40:
            age_buckets['30-39 Tahun'] += 1
        elif age < 50:
            age_buckets['40-49 Tahun'] += 1
        elif age < 60:
            age_buckets['50-59 Tahun'] += 1
        elif age == 60:
            age_buckets['60 Tahun'] += 1
        else:
            # Usia > 60 tidak termasuk statistik pegawai aktif.
            continue

        unit_id = str(row.UNIT_KERJA_ID or '').strip()
        unit_name = unit_map.get(unit_id) or str(
            row.UNIT_KERJA or ''
        ).strip() or 'Belum diisi'
        unit_counts[unit_name] = unit_counts.get(unit_name, 0) + 1

    unit_distribution = sorted(
        [
            {'name': name, 'total': count}
            for name, count in unit_counts.items()
        ],
        key=lambda item: (-item['total'], item['name'].lower())
    )

    return render_template(
        'pages/dashboard_1/Dashboard Infografis.html',
        total=total,
        pns=pns,
        non_pns=non_pns,
        gender_counts=gender_counts,
        status_counts=status_counts,
        age_buckets=age_buckets,
        age_unknown=age_unknown,
        unit_distribution=unit_distribution,
    )
