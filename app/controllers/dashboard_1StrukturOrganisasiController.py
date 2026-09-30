# app/controllers/dashboard_1StrukturOrganisasiController.py

from flask import render_template

from app.models.jabatanModel import MfJabatan
from app.utils.pegawaiHelper import get_operational_pegawai_query


def _is_active_jabatan(row):
    value = str(row.IS_USE).strip().upper() if row.IS_USE is not None else ''
    return value in ('1', 'Y', 'YA', 'TRUE')


def _sort_jabatan(rows):
    return sorted(
        rows,
        key=lambda row: (
            row.URUT_JABATAN if row.URUT_JABATAN is not None else 999999,
            int(row.JABATAN_ID) if row.JABATAN_ID is not None else 999999999,
        )
    )


def _build_structure(active_rows):
    """
    Struktur yang sama dengan Master Jabatan, tetapi untuk Dashboard
    hanya mengirim Nama Jabatan. Kode Jabatan dipakai internal untuk
    relasi struktur dan pencocokan Pegawai.JABATAN_ID.
    """
    by_code = {str(row.JABATAN_ID): row for row in active_rows}
    root = by_code.get('10')

    if root is None:
        return None

    def make_node(row, relation='structural'):
        return {
            'id': int(row.JABATAN_ID),
            'name': row.NAMA_JABATAN or '-',
            'relation': relation,
            'children': [],
        }

    root_node = make_node(root)

    # Semua jabatan 4 digit aktif menjadi anak root 10.
    # PKPP 1050 selalu ditempatkan paling kanan.
    top_rows = sorted(
        [
            row for row in active_rows
            if len(str(row.JABATAN_ID)) == 4
            and str(row.JABATAN_ID).startswith('10')
            and str(row.JABATAN_ID) != '10'
        ],
        key=lambda row: (
            1 if str(row.JABATAN_ID) == '1050' else 0,
            row.URUT_JABATAN if row.URUT_JABATAN is not None else 999999,
            int(row.JABATAN_ID) if row.JABATAN_ID is not None else 999999999,
        )
    )

    for parent_row in top_rows:
        parent_code = str(parent_row.JABATAN_ID)
        relation = 'functional' if parent_code == '1050' else 'structural'
        parent_node = make_node(parent_row, relation=relation)

        if parent_code == '1050':
            # Struktur PKPP mengikuti struktur yang dipakai Master Jabatan.
            pkpp_rows = _sort_jabatan([
                row for row in active_rows
                if len(str(row.JABATAN_ID)) == 6
                and str(row.JABATAN_ID).startswith('1050')
            ])

            if pkpp_rows:
                group_row = next(
                    (
                        row for row in pkpp_rows
                        if str(row.JABATAN_ID).endswith('010')
                    ),
                    pkpp_rows[0]
                )

                group_node = make_node(
                    group_row,
                    relation='functional'
                )

                for child_row in pkpp_rows:
                    if child_row.JABATAN_ID == group_row.JABATAN_ID:
                        continue

                    group_node['children'].append(
                        make_node(child_row, relation='functional')
                    )

                parent_node['children'].append(group_node)

        else:
            child_rows = _sort_jabatan([
                row for row in active_rows
                if len(str(row.JABATAN_ID)) > len(parent_code)
                and str(row.JABATAN_ID).startswith(parent_code)
            ])

            for child_row in child_rows:
                parent_node['children'].append(
                    make_node(child_row, relation='structural')
                )

        root_node['children'].append(parent_node)

    return root_node


def dashboard_struktur_organisasi():
    """
    Dashboard Struktur Organisasi.

    Sumber:
      - MF_JABATAN untuk struktur organisasi.
      - PEGAWAI.JABATAN_ID untuk daftar pegawai per jabatan.

    Pegawai yang ditampilkan mengikuti populasi operasional HRIS:
      PEGAWAI.IS_KELUAR = 'N'
      AND MF_UNIT_KERJA.IS_USE = 'Y'
    """
    jabatan_rows = [
        row
        for row in MfJabatan.query.all()
        if _is_active_jabatan(row)
    ]

    root = _build_structure(jabatan_rows)

    pegawai_rows = get_operational_pegawai_query().all()

    employees_by_jabatan = {}

    for row in pegawai_rows:
        if row.JABATAN_ID is None:
            continue

        key = str(row.JABATAN_ID)
        employees_by_jabatan.setdefault(key, []).append({
            'nama': row.NAMA or '-',
            'nip': row.NIP or '-',
        })

    for items in employees_by_jabatan.values():
        items.sort(
            key=lambda item: (
                str(item['nama']).upper(),
                str(item['nip'])
            )
        )

    return render_template(
        'pages/dashboard_1/Dashboard Struktur Organisasi.html',
        structure=root,
        employees_by_jabatan=employees_by_jabatan,
    )
