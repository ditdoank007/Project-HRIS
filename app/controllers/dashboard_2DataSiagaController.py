# controllers/dashboard_2DataSiagaController.py
from flask import render_template, request, jsonify, g, current_app, send_file, session
from datetime import datetime, timedelta
import uuid
import io
import os
import hashlib
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from app import db
from app.models.otorisasiModel import Otorisasi
from app.models.jabatanSiagaModel import MfJabatanSiaga
from app.models.pegawaiModel import Pegawai
from app.models.unitKerjaModel import MfUnitKerja
from app.models.logActivityModel import LogActivity
from app.models.shiftModel import MfShift
from app.models.statusModel import MfStatus
from app.models.orgzSiagaModel import MfOrgzSiaga
from app.models.logActivityBackupModel import LogActivityBackup
from app.models.dinasLuarModel import DinasLuar

def data_siaga_absensi_kehadiran():
    """Render halaman Absensi Kehadiran Piket Siaga.

    Master dropdown dibaca dengan SQL fisik agar halaman tidak bergantung
    pada ORM legacy yang beberapa kolomnya tidak parity dengan database.
    """
    unit_kerja_list = db.session.execute(
        db.text("""
            SELECT IDUnitKerja, UnitKerjaName
            FROM MF_UNIT_KERJA
            WHERE isUse = 'Y'
            ORDER BY UrutReport ASC, UnitKerjaName ASC
        """)
    ).mappings().all()

    shift_list = db.session.execute(
        db.text("""
            SELECT ShiftID, NamaShift
            FROM MF_SHIFT
            WHERE COALESCE(NamaShift, '') <> ''
            ORDER BY ShiftID ASC
        """)
    ).mappings().all()

    return render_template(
        'pages/dashboard_2/Data_Siaga_Absensi_Kehadiran.html',
        unit_kerja_list=unit_kerja_list,
        shift_list=shift_list
    )

def api_absensi_kehadiran_get():
    """
    API VIEW DATA Absensi Kehadiran Piket Siaga.

    Sumber:
        LOG_ACTIVITIY

    Aturan:
        Activity     = Piket Siaga
        ActivityDate = tanggal yang dipilih
        Shift        = shift yang dipilih

    Status:
        STATUS_ID = 3  -> Hadir
        STATUS_ID = -1 -> Tidak Hadir
        lainnya          -> Belum

    Catatan:
        Untuk halaman kehadiran kita sengaja menggunakan SQL
        terhadap kolom fisik LOG_ACTIVITIY agar tidak tergantung
        pada ketidaksesuaian model lama.
    """
    try:
        tgl = (
            request.args.get(
                'tgl',
                datetime.now().strftime('%Y-%m-%d')
            )
            or ''
        ).strip()

        unit_kerja_id = (
            request.args.get('unit_kerja_id', '')
            or ''
        ).strip()

        shift = (
            request.args.get('shift', '')
            or ''
        ).strip()

        if not tgl:
            return jsonify({
                'success': False,
                'error': 'Tanggal harus diisi',
                'data': []
            })

        sql = db.text("""
            SELECT
                l.GUIDLog,
                l.NIP,
                l.ActivityDate,
                l.Fungsional,
                l.Shift,
                l.StatusID,
                l.shift1,
                l.shift2,
                l.Pengganti,
                l.StatusTrx,
                l.UpdateBy,
                l.UpdateDate,
                l.IDUnitKerja,
                p.Nama AS NAMA,
                u.UnitKerjaName AS NAMA_UNIT_KERJA,
                COALESCE(ub.Nama, l.UpdateBy) AS UPDATE_BY_NAME,
                (
                    SELECT p0.Nama
                    FROM LOG_ACTIVITIY lo
                    LEFT JOIN PEGAWAI p0 ON p0.NIP = lo.NIP
                    WHERE lo.Activity = 'Piket Siaga'
                      AND lo.ActivityDate = l.ActivityDate
                      AND lo.Shift = l.Shift
                      AND lo.IDUnitKerja = l.IDUnitKerja
                      AND COALESCE(lo.Pengganti, 0) = 0
                      AND NULLIF(TRIM(COALESCE(lo.NIPPengganti, '')), '') IS NOT NULL
                      AND TRIM(lo.NIPPengganti) <> '-'
                      AND TRIM(lo.NIPPengganti) = TRIM(l.NIP)
                    LIMIT 1
                ) AS NAMA_ASLI_PENGGANTI
            FROM LOG_ACTIVITIY l
            LEFT JOIN PEGAWAI p
                ON p.NIP = l.NIP
            LEFT JOIN PEGAWAI ub
                ON ub.NIP = l.UpdateBy
            LEFT JOIN MF_UNIT_KERJA u
                ON u.IDUnitKerja = l.IDUnitKerja
            WHERE l.Activity = 'Piket Siaga'
              AND l.ActivityDate = :tgl
              AND NOT (
                  COALESCE(l.Pengganti, 0) = 0
                  AND NULLIF(TRIM(COALESCE(l.NIPPengganti, '')), '') IS NOT NULL
                  AND TRIM(l.NIPPengganti) <> '-'
              )
        """)

        params = {
            'tgl': tgl
        }

        if unit_kerja_id:
            sql = db.text("""
                SELECT
                    l.GUIDLog,
                    l.NIP,
                    l.ActivityDate,
                    l.Fungsional,
                    l.Shift,
                    l.StatusID,
                    l.shift1,
                    l.shift2,
                    l.Pengganti,
                    l.StatusTrx,
                    l.UpdateBy,
                    l.UpdateDate,
                    l.IDUnitKerja,
                    p.Nama AS NAMA,
                    u.UnitKerjaName AS NAMA_UNIT_KERJA,
                    COALESCE(ub.Nama, l.UpdateBy) AS UPDATE_BY_NAME,
                (
                    SELECT p0.Nama
                    FROM LOG_ACTIVITIY lo
                    LEFT JOIN PEGAWAI p0 ON p0.NIP = lo.NIP
                    WHERE lo.Activity = 'Piket Siaga'
                      AND lo.ActivityDate = l.ActivityDate
                      AND lo.Shift = l.Shift
                      AND lo.IDUnitKerja = l.IDUnitKerja
                      AND COALESCE(lo.Pengganti, 0) = 0
                      AND NULLIF(TRIM(COALESCE(lo.NIPPengganti, '')), '') IS NOT NULL
                      AND TRIM(lo.NIPPengganti) <> '-'
                      AND TRIM(lo.NIPPengganti) = TRIM(l.NIP)
                    LIMIT 1
                ) AS NAMA_ASLI_PENGGANTI
                FROM LOG_ACTIVITIY l
                LEFT JOIN PEGAWAI p
                    ON p.NIP = l.NIP
                LEFT JOIN PEGAWAI ub
                    ON ub.NIP = l.UpdateBy
                LEFT JOIN MF_UNIT_KERJA u
                    ON u.IDUnitKerja = l.IDUnitKerja
                WHERE l.Activity = 'Piket Siaga'
                  AND l.ActivityDate = :tgl
              AND NOT (
                  COALESCE(l.Pengganti, 0) = 0
                  AND NULLIF(TRIM(COALESCE(l.NIPPengganti, '')), '') IS NOT NULL
                  AND TRIM(l.NIPPengganti) <> '-'
              )
                  AND l.IDUnitKerja = :unit_kerja_id
            """)
            params['unit_kerja_id'] = int(unit_kerja_id)

        if shift:
            base = sql.text
            # handled below by rebuilding query with shift
            sql_string = str(sql)
            sql_string = sql_string.replace(
                "AND l.ActivityDate = :tgl",
                "AND l.ActivityDate = :tgl\n"
                "              AND l.Shift = :shift"
            )
            sql = db.text(sql_string)
            params['shift'] = shift

        # Urutan baris mengikuti aturan HRIS 2013:
        # Unit umum   : KGR/Kagahar -> KOM/Komunikasi -> RSC/Rescuer.
        # Unit KN/Kapal: PW/Perwira -> ABK.
        # Nilai lain ditempatkan setelah kelompok utama.
        order_clause = """
            ORDER BY
                l.Shift ASC,
                CASE
                    WHEN UPPER(COALESCE(u.UnitKerjaName, '')) LIKE 'KN %'
                      OR UPPER(COALESCE(u.UnitKerjaName, '')) LIKE '%KAPAL%'
                      OR UPPER(COALESCE(u.UnitKerjaName, '')) LIKE '%KN SAR%'
                    THEN
                        CASE
                            WHEN UPPER(COALESCE(l.Fungsional, '')) IN ('PW', 'PERWIRA')
                              OR UPPER(COALESCE(l.Fungsional, '')) LIKE '%PERWIRA%'
                            THEN 1
                            WHEN UPPER(COALESCE(l.Fungsional, '')) = 'ABK'
                              OR UPPER(COALESCE(l.Fungsional, '')) LIKE '%ABK%'
                            THEN 2
                            ELSE 99
                        END
                    ELSE
                        CASE
                            WHEN UPPER(COALESCE(l.Fungsional, '')) IN ('KGR', 'KAGAHAR')
                              OR UPPER(COALESCE(l.Fungsional, '')) LIKE '%KAGAHAR%'
                            THEN 1
                            WHEN UPPER(COALESCE(l.Fungsional, '')) IN ('KOM', 'KOMUNIKASI')
                              OR UPPER(COALESCE(l.Fungsional, '')) LIKE '%KOMUNIKASI%'
                            THEN 2
                            WHEN UPPER(COALESCE(l.Fungsional, '')) IN ('RSC', 'RESCUER')
                              OR UPPER(COALESCE(l.Fungsional, '')) LIKE '%RESCUER%'
                            THEN 3
                            ELSE 99
                        END
                END,
                l.Fungsional ASC,
                p.Nama ASC
        """

        sql_string = str(sql) + "\n" + order_clause
        sql = db.text(sql_string)

        rows = db.session.execute(
            sql,
            params
        ).mappings().all()

        data = []

        for i, row in enumerate(rows, 1):
            status_id = row['StatusID']

            if status_id == 3:
                status = 'Hadir'
            elif status_id == -1:
                status = 'Tidak Hadir'
            else:
                status = 'Belum'

            data.append({
                'no': i,
                'guid_log': row['GUIDLog'],
                'nip': row['NIP'],
                'nama': row['NAMA'] or '-',
                'activity_date': (
                    row['ActivityDate'].strftime('%d-%m-%Y')
                    if row['ActivityDate']
                    else ''
                ),
                'activity_date_iso': (
                    row['ActivityDate'].strftime('%Y-%m-%d')
                    if row['ActivityDate']
                    else ''
                ),
                'fungsional': row['Fungsional'] or '',
                'fungsional_ket': row['Fungsional'] or '',
                'unit_kerja': row['NAMA_UNIT_KERJA'] or '',
                'shift': row['Shift'] or '',
                'status_id': status_id,
                'status': status,
                'shift_1': row['shift1'] or 0,
                'shift_2': row['shift2'] or 0,
                'pengganti': row['Pengganti'] or 0,
                'nama_asli_pengganti': row['NAMA_ASLI_PENGGANTI'] or '',
                'status_trx': row['StatusTrx'] or '-',
                'update_by': row['UPDATE_BY_NAME'] or row['UpdateBy'] or '',
                'update_date': (
                    row['UpdateDate'].strftime('%d/%m/%Y %H:%M')
                    if row['UpdateDate']
                    else ''
                ),
            })

        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })

    except Exception as e:
        db.session.rollback()

        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })




def _siaga_document_key(tgl, unit_kerja_id, shift):
    return f"{tgl}|{int(unit_kerja_id)}|{str(shift).strip()}"


def _siaga_pdf_relative_path(selected_date, unit_kerja_id, shift):
    return os.path.join(
        "ABSEN_KEHADIRAN_SIAGA",
        selected_date.strftime("%Y"),
        selected_date.strftime("%m"),
        selected_date.strftime("%d"),
        str(int(unit_kerja_id)),
        f"absen-kehadiran-shift{shift}.pdf",
    ).replace(os.sep, "/")


def _siaga_pdf_absolute_path(relative_path):
    root = Path(current_app.config.get("HRIS_DATA_ROOT") or "/mnt/hris-data").resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path storage Absen Kehadiran Siaga tidak valid.")
    return candidate


def _siaga_signature_path(nip, finger_id=None):
    root = Path(
        current_app.config.get("HRIS_TTD_ROOT")
        or "/mnt/hris-data/TTD_PEGAWAI"
    ).resolve()
    candidates = []
    if nip:
        candidates.append(root / f"{str(nip).strip()}.png")
    if finger_id:
        candidates.append(root / f"{str(finger_id).strip()}.png")
    for candidate in candidates:
        if candidate.is_file() and root in candidate.parents:
            return candidate
    return None


def _siaga_kagahar(tgl, unit_kerja_id, shift):
    row = db.session.execute(
        db.text("""
            SELECT
                l.NIP,
                p.Nama AS Nama,
                p.Pangkat AS Pangkat,
                p.FingerID AS FingerID,
                p.Jabatan AS Jabatan
            FROM LOG_ACTIVITIY l
            LEFT JOIN PEGAWAI p ON p.NIP = l.NIP
            WHERE l.Activity = 'Piket Siaga'
              AND l.ActivityDate = :tgl
              AND l.IDUnitKerja = :unit_kerja_id
              AND l.Shift = :shift
              AND UPPER(COALESCE(l.Fungsional, '')) IN ('KGR', 'KAGAHAR')
              AND COALESCE(l.Pengganti, 0) = 0
            ORDER BY l.NIP ASC
            LIMIT 1
        """),
        {
            "tgl": tgl,
            "unit_kerja_id": int(unit_kerja_id),
            "shift": str(shift),
        }
    ).mappings().first()
    return row


def _siaga_atasan_langsung():
    return db.session.execute(
        db.text("""
            SELECT
                NIP,
                Nama,
                Pangkat,
                FingerID,
                Jabatan
            FROM PEGAWAI
            WHERE isKeluar <> 'Y'
              AND UPPER(COALESCE(Jabatan, '')) LIKE '%KEPALA SEKSI OPERASI%'
            ORDER BY NIP ASC
            LIMIT 1
        """)
    ).mappings().first()


def _build_siaga_pdf(tgl, unit_kerja_id, shift):
    with current_app.test_request_context(
        f'/api/absensi-kehadiran/get?tgl={tgl}&unit_kerja_id={int(unit_kerja_id)}&shift={shift}'
    ):
        response = api_absensi_kehadiran_get()
    payload = response.get_json(silent=True) if hasattr(response, 'get_json') else None
    if not payload or not payload.get('success'):
        raise ValueError((payload or {}).get('error', 'Gagal mengambil data absensi.'))

    rows = payload.get('data', [])
    unit_row = db.session.execute(
        db.text("""
            SELECT UnitKerjaName
            FROM MF_UNIT_KERJA
            WHERE IDUnitKerja = :unit_kerja_id
            LIMIT 1
        """),
        {'unit_kerja_id': int(unit_kerja_id)}
    ).mappings().first()

    unit_name = str((unit_row['UnitKerjaName'] if unit_row else 'Unit Kerja') or 'Unit Kerja').strip()
    selected_date = datetime.strptime(tgl, '%Y-%m-%d')
    hari = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'][selected_date.weekday()]
    bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
             'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'][selected_date.month - 1]

    atasan = _siaga_atasan_langsung()
    kagahar = _siaga_kagahar(tgl, unit_kerja_id, shift)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DaftarHadirTitle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=14, leading=17,
        alignment=1, spaceAfter=8
    )
    subtitle_style = ParagraphStyle(
        'DaftarHadirSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, leading=13,
        alignment=1, spaceAfter=14
    )
    cell_style = ParagraphStyle(
        'DaftarHadirCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=10
    )
    cell_center = ParagraphStyle(
        'DaftarHadirCellCenter', parent=cell_style, alignment=1
    )

    elements = [
        Paragraph('DAFTAR HADIR SIAGA SAR', title_style),
        Paragraph(
            f'{hari} {selected_date.day:02d}-{bulan}-{selected_date.year} Shift : {shift}',
            subtitle_style
        )
    ]

    table_data = [[
        Paragraph('<b>No</b>', cell_center),
        Paragraph('<b>Jabatan</b>', cell_center),
        Paragraph('<b>Nama</b>', cell_center),
        Paragraph(f'<b>Tanda Tangan<br/>Shift {shift}</b>', cell_center),
        Paragraph('<b>Keterangan</b>', cell_center)
    ]]

    for idx, item in enumerate(rows, 1):
        table_data.append([
            Paragraph(str(idx), cell_center),
            Paragraph(xml_escape(str(item.get('fungsional') or '-')), cell_center),
            Paragraph(xml_escape(str(item.get('nama') or item.get('nip') or '-')), cell_style),
            '',
            ''
        ])

    if len(table_data) == 1:
        table_data.append([
            Paragraph('-', cell_center),
            Paragraph('-', cell_center),
            Paragraph('Tidak ada data Piket Siaga.', cell_style),
            '',
            ''
        ])

    table = Table(table_data, colWidths=[32, 70, 190, 115, 80], repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (4, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 28))

    def person_cell(person):
        if not person:
            return Paragraph('-', cell_center)
        name = xml_escape(str(person.get('Nama') or '-'))
        nip = xml_escape(str(person.get('NIP') or '-'))
        pangkat = xml_escape(str(person.get('Pangkat') or ''))
        return Paragraph(
            f'<b><u>{name}</u></b><br/>NIP. {nip}'
            + (f'<br/>{pangkat}' if pangkat else ''),
            cell_center
        )

    signature_cells = []
    for person in (atasan, kagahar):
        signature_path = _siaga_signature_path(
            person.get('NIP') if person else None,
            person.get('FingerID') if person else None
        )
        if signature_path:
            from reportlab.platypus import Image
            sig = Image(str(signature_path), width=110, height=42, kind='proportional')
        else:
            sig = ''
        signature_cells.append(sig)

    left_title = Paragraph('<b>Mengetahui</b><br/>Atasan Langsung', cell_center)
    right_title = Paragraph(
        xml_escape(f'{unit_name}, {hari} {selected_date.day:02d}-{bulan}-{selected_date.year}')
        + '<br/><b>KAGAHAR</b>',
        cell_center
    )

    sign_table = Table([
        [left_title, right_title],
        [signature_cells[0], signature_cells[1]],
        [person_cell(atasan), person_cell(kagahar)],
    ], colWidths=[235, 252])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 1), (-1, 1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 5),
        ('TOPPADDING', (0, 2), (-1, 2), 4),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 4),
    ]))
    elements.append(sign_table)
    elements.append(Spacer(1, 8))

    kagahar_log = kagahar.get('NIP') if kagahar else ''
    if kagahar_log:
        latest_log = db.session.execute(
            db.text("""
                SELECT GUIDLog
                FROM LOG_ACTIVITIY
                WHERE Activity = 'Piket Siaga'
                  AND ActivityDate = :tgl
                  AND IDUnitKerja = :unit_kerja_id
                  AND Shift = :shift
                  AND NIP = :nip
                ORDER BY UpdateDate DESC
                LIMIT 1
            """),
            {
                'tgl': tgl,
                'unit_kerja_id': int(unit_kerja_id),
                'shift': str(shift),
                'nip': kagahar_log,
            }
        ).mappings().first()
        if latest_log:
            elements.append(
                Paragraph(
                    xml_escape(f'LogID : {latest_log["GUIDLog"]}'),
                    ParagraphStyle(
                        'LogId', parent=styles['Normal'],
                        fontSize=7.5, textColor=colors.grey
                    )
                )
            )

    doc.build(elements)
    buffer.seek(0)
    return buffer


def _save_siaga_pdf(tgl, unit_kerja_id, shift, created_by=None):
    selected_date = datetime.strptime(tgl, '%Y-%m-%d')
    relative_path = _siaga_pdf_relative_path(selected_date, unit_kerja_id, shift)
    target = _siaga_pdf_absolute_path(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    buffer = _build_siaga_pdf(tgl, unit_kerja_id, shift)
    content = buffer.getvalue()
    sha256 = hashlib.sha256(content).hexdigest()

    fd, temp_path = tempfile.mkstemp(
        prefix='.absen-siaga-', suffix='.tmp', dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    except Exception:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise

    from app.models.hrisDocumentModel import HrisDocument
    document_type = 'ABSEN_KEHADIRAN_SIAGA'
    entity_type = 'PIKET_SIAGA'
    entity_id = _siaga_document_key(tgl, unit_kerja_id, shift)
    now = datetime.now()
    document = (
        HrisDocument.query
        .filter(
            HrisDocument.DOCUMENT_TYPE == document_type,
            HrisDocument.ENTITY_TYPE == entity_type,
            HrisDocument.ENTITY_ID == entity_id,
        )
        .first()
    )
    if document:
        document.ORIGINAL_FILENAME = f'{selected_date.day:02d}-{selected_date.month:02d}-{selected_date.year}-absen-kehadiran-shift{shift}.pdf'
        document.STORAGE_PATH = relative_path
        document.MIME_TYPE = 'application/pdf'
        document.FILE_SIZE = len(content)
        document.SHA256 = sha256
        document.UPDATE_BY = created_by
        document.UPDATE_DATE = now
    else:
        document = HrisDocument(
            DOCUMENT_TYPE=document_type,
            ENTITY_TYPE=entity_type,
            ENTITY_ID=entity_id,
            ORIGINAL_FILENAME=f'{selected_date.day:02d}-{selected_date.month:02d}-{selected_date.year}-absen-kehadiran-shift{shift}.pdf',
            STORAGE_PATH=relative_path,
            MIME_TYPE='application/pdf',
            FILE_SIZE=len(content),
            SHA256=sha256,
            CREATED_BY=created_by or 'HRIS',
            CREATED_DATE=now,
        )
        db.session.add(document)
    db.session.commit()
    return {
        'relative_path': relative_path,
        'absolute_path': str(target),
        'filename': document.ORIGINAL_FILENAME,
        'sha256': sha256,
        'entity_id': entity_id,
    }


def api_absensi_kehadiran_save_pdf():
    try:
        shift = (request.args.get('shift', '') or '').strip()
        unit_kerja_id = (request.args.get('unit_kerja_id', '') or '').strip()
        tgl = (request.args.get('tgl', '') or '').strip()

        if not tgl:
            return jsonify({'success': False, 'error': 'Tanggal harus diisi.'}), 400
        if shift not in ('1', '2'):
            return jsonify({'success': False, 'error': 'Pilih Shift 1 atau Shift 2.'}), 400
        if not unit_kerja_id:
            return jsonify({'success': False, 'error': 'Pilih Unit Kerja terlebih dahulu.'}), 400

        saved = _save_siaga_pdf(
            tgl, unit_kerja_id, shift,
            created_by=getattr(getattr(g, 'user', None), 'NIP', None) or 'HRIS'
        )
        return jsonify({
            'success': True,
            'message': 'Daftar hadir PDF berhasil disimpan ke HRIS-DATA.',
            'data': {
                'filename': saved['filename'],
                'relative_path': saved['relative_path'],
                'entity_id': saved['entity_id'],
                'sha256': saved['sha256'],
            }
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def api_absensi_kehadiran_export_pdf():
    try:
        shift = (request.args.get('shift', '') or '').strip()
        unit_kerja_id = (request.args.get('unit_kerja_id', '') or '').strip()
        tgl = (request.args.get('tgl', '') or '').strip()

        if not tgl:
            return jsonify({'success': False, 'error': 'Tanggal harus diisi.'}), 400
        if shift not in ('1', '2'):
            return jsonify({'success': False, 'error': 'Pilih Shift 1 atau Shift 2 sebelum mengunduh PDF.'}), 400
        if not unit_kerja_id:
            return jsonify({'success': False, 'error': 'Pilih Unit Kerja sebelum mengunduh PDF.'}), 400

        from app.models.hrisDocumentModel import HrisDocument
        entity_id = _siaga_document_key(tgl, unit_kerja_id, shift)
        document = HrisDocument.query.filter(
            HrisDocument.DOCUMENT_TYPE == 'ABSEN_KEHADIRAN_SIAGA',
            HrisDocument.ENTITY_TYPE == 'PIKET_SIAGA',
            HrisDocument.ENTITY_ID == entity_id,
        ).first()

        if not document:
            return jsonify({
                'success': False,
                'error': 'PDF belum disimpan ke HRIS-DATA. Tekan tombol SIMPAN terlebih dahulu.'
            }), 404

        path = _siaga_pdf_absolute_path(document.STORAGE_PATH)
        if not path.is_file():
            return jsonify({
                'success': False,
                'error': 'Metadata PDF tersedia tetapi file tidak ditemukan di HRIS-DATA. Tekan SIMPAN untuk membuat ulang.'
            }), 404

        return send_file(
            path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=document.ORIGINAL_FILENAME,
            max_age=0
        )
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



def api_absensi_kehadiran_internal_pdf():
    from config import Config

    internal_key = request.headers.get('X-Calendar-Internal-Key')
    if not internal_key or internal_key != Config.CALENDAR_INTERNAL_API_KEY:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        from urllib.parse import unquote
        key = unquote(str(request.args.get('key') or '')).strip()
        parts = key.split('|')
        if len(parts) != 3:
            return jsonify({'status': 'error', 'message': 'Dokumen Piket Siaga tidak valid.'}), 400
        tgl, unit_kerja_id, shift = parts
        if shift not in ('1', '2'):
            return jsonify({'status': 'error', 'message': 'Shift tidak valid.'}), 400

        nip = str(request.headers.get('X-Calendar-NIP') or '').strip()
        if not nip:
            return jsonify({'status': 'error', 'message': 'NIP wajib diisi.'}), 400

        allowed = db.session.execute(
            db.text("""
                SELECT 1
                FROM LOG_ACTIVITIY
                WHERE Activity = 'Piket Siaga'
                  AND ActivityDate = :tgl
                  AND IDUnitKerja = :unit_kerja_id
                  AND Shift = :shift
                  AND NIP = :nip
                  AND StatusID = 3
                LIMIT 1
            """),
            {
                'tgl': tgl,
                'unit_kerja_id': int(unit_kerja_id),
                'shift': shift,
                'nip': nip,
            }
        ).first()
        if not allowed:
            return jsonify({'status': 'error', 'message': 'Dokumen belum tersedia untuk pegawai ini.'}), 403

        document_type = 'ABSEN_KEHADIRAN_SIAGA'
        entity_type = 'PIKET_SIAGA'
        entity_id = _siaga_document_key(tgl, unit_kerja_id, shift)
        from app.models.hrisDocumentModel import HrisDocument
        document = HrisDocument.query.filter(
            HrisDocument.DOCUMENT_TYPE == document_type,
            HrisDocument.ENTITY_TYPE == entity_type,
            HrisDocument.ENTITY_ID == entity_id,
        ).first()

        if not document:
            return jsonify({
                'status': 'error',
                'message': 'PDF belum disimpan oleh operator.'
            }), 404

        path = _siaga_pdf_absolute_path(document.STORAGE_PATH)
        if not path.is_file():
            return jsonify({'status': 'error', 'message': 'File PDF tidak ditemukan di central storage.'}), 404

        return send_file(
            path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=document.ORIGINAL_FILENAME,
            max_age=0
        )
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


def api_absensi_kehadiran_update():
    """
    API SIMPAN KEHADIRAN PIKET SIAGA.

    Hadir Shift 1:
        StatusID = 3
        shift1   = 1
        shift2   = 0

    Hadir Shift 2:
        StatusID = 3
        shift1   = 0
        shift2   = 1

    Tidak hadir:
        StatusID = -1
        shift1   = 0
        shift2   = 0
    """
    try:
        data = request.get_json() or {}

        guid_log = (
            str(data.get('guid_log') or '')
            .strip()
        )

        nip = (
            str(data.get('nip') or '')
            .strip()
        )

        shift1 = bool(data.get('shift1'))
        shift2 = bool(data.get('shift2'))

        no_urut = int(data.get('no') or 0)

        activity_date = (
            str(data.get('activity_date') or '')
            .strip()
        )

        if not guid_log or not nip or not activity_date:
            return jsonify({
                'success': False,
                'error': 'GUID Log, NIP, dan tanggal wajib diisi'
            })

        authorization = db.session.execute(
            db.text("""
                SELECT 1
                FROM OTORISASI
                WHERE GUIDOto = :guid_log
                  AND LevelOto = '1'
                  AND act = '3'
                LIMIT 1
            """),
            {'guid_log': guid_log},
        ).first()

        if not authorization:
            return jsonify({
                'success': False,
                'error': (
                    'Absensi Jadwal Piket Gagal. '
                    'Jadwal belum diotorisasi Kasi Operasi.'
                )
            })

        # HRIS 2013: hadir jika minimal satu shift dipilih.
        # Kedua flag boleh aktif bersamaan.
        status_id = 3 if (shift1 or shift2) else -1

        # HRIS 2013 juga mengisi jam baku dan jam aktual ketika hadir.
        # Rumus ini dipertahankan agar data Reborn tetap parity dengan
        # KehadiranPiket.aspx.vb.
        tgl_jam_in = None
        tgl_jam_out = None
        tgl_baku_in = None
        tgl_baku_out = None

        if status_id == 3:
            employee = db.session.execute(
                db.text("""
                    SELECT Nama
                    FROM PEGAWAI
                    WHERE NIP = :nip
                    LIMIT 1
                """),
                {'nip': nip},
            ).mappings().first()

            nama = str((employee or {}).get('Nama') or nip)

            now = datetime.now()
            konstanta = 9
            batas_max = 61
            jam_pulang = 27

            int_jam = int(now.strftime('%I')) + now.second
            tambahan = (
                no_urut
                + konstanta
                + (
                    (
                        now.day
                        + now.month
                        + now.year
                        + int_jam
                        + len(nama)
                    ) * no_urut
                ) % batas_max
            )

            if tambahan > batas_max:
                tambahan = (
                    (tambahan % konstanta)
                    + len(nama)
                    + (no_urut % 19)
                )

            if tambahan < 7:
                jam_pulang = tambahan + len(nama)
            else:
                jam_pulang = tambahan - (no_urut % 7)

            base_date = datetime.strptime(
                activity_date,
                '%Y-%m-%d'
            )

            if shift1:
                baku_in = base_date.replace(hour=16, minute=0, second=0)
                baku_out = base_date.replace(hour=20, minute=0, second=0)
            else:
                next_date = base_date + timedelta(days=1)
                baku_in = next_date.replace(hour=4, minute=0, second=0)
                baku_out = next_date.replace(hour=8, minute=0, second=0)

            tgl_baku_in = baku_in
            tgl_baku_out = baku_out
            tgl_jam_in = baku_in - timedelta(minutes=tambahan)
            tgl_jam_out = baku_out + timedelta(minutes=jam_pulang)

        update_sql = db.text("""
            UPDATE LOG_ACTIVITIY
            SET
                StatusID = :status_id,
                shift1 = :shift1,
                shift2 = :shift2,
                TglClosing = ActivityDate,
                TglJamIn = :tgl_jam_in,
                TglJamOut = :tgl_jam_out,
                TglJamBakuIn = :tgl_baku_in,
                TglJamBakuOut = :tgl_baku_out,
                UpdateBy = :update_by,
                UpdateDate = :update_date
            WHERE GUIDLog = :guid_log
              AND NIP = :nip
              AND Activity = 'Piket Siaga'
              AND ActivityDate = :activity_date
        """)

        result = db.session.execute(
            update_sql,
            {
                'status_id': status_id,
                'shift1': 1 if shift1 else 0,
                'shift2': 1 if shift2 else 0,
                'update_by': (
                    getattr(getattr(g, 'user', None), 'NIP', None)
                    or 'HRIS'
                ),
                'update_date': datetime.now(),
                'guid_log': guid_log,
                'nip': nip,
                'activity_date': activity_date,
                'tgl_jam_in': tgl_jam_in,
                'tgl_jam_out': tgl_jam_out,
                'tgl_baku_in': tgl_baku_in,
                'tgl_baku_out': tgl_baku_out,
            }
        )

        if result.rowcount == 0:
            db.session.rollback()

            return jsonify({
                'success': False,
                'error': 'Data piket siaga tidak ditemukan'
            })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                'Kehadiran Shift 1 berhasil disimpan'
                if shift1
                else
                'Kehadiran Shift 2 berhasil disimpan'
                if shift2
                else
                'Status Tidak Hadir berhasil disimpan'
            )
        })

    except Exception as e:
        db.session.rollback()

        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        })




# ============================================================
# HRIS REBORN - MASTER DROPDOWN BUAT JADWAL SIAGA
# ============================================================

def api_siaga_master_jabatan_aktif():
    """
    Mengambil Master Jabatan Siaga aktif.

    Single Source:
        MF_JABATAN_SIAGA

    Business Rule:
        IsAktif = Y
        ORDER BY NoUrut ASC
    """

    try:

        rows = (
            MfJabatanSiaga.query
            .filter(
                MfJabatanSiaga.IS_AKTIF == 'Y'
            )
            .order_by(
                MfJabatanSiaga.NO_URUT.asc()
            )
            .all()
        )

        return jsonify({
            'success': True,
            'data': [
                {
                    'id_jabatan_siaga':
                        row.ID_JABATAN_SIAGA,

                    'no_urut':
                        row.NO_URUT,

                    'nama_jabatan':
                        row.NAMA_JABATAN,

                    'keterangan':
                        row.KETERANGAN or ''
                }
                for row in rows
            ]
        })

    except Exception:

        current_app.logger.exception(
            'Gagal mengambil Master Jabatan Siaga aktif'
        )

        return jsonify({
            'success': False,
            'error': 'Gagal mengambil Master Jabatan Siaga.'
        }), 500


def api_siaga_master_unit_aktif():
    """
    Mengambil Master Unit Kerja aktif.

    Single Source:
        MF_UNIT_KERJA

    Business Rule:
        IS_USE = Y

    Unit nonaktif tidak boleh muncul pada
    dropdown Buat Jadwal Siaga.
    """

    try:

        rows = (
            MfUnitKerja.query
            .filter(
                MfUnitKerja.IS_USE == 'Y'
            )
            .order_by(
                MfUnitKerja.URUT_REPORT.asc()
            )
            .all()
        )

        return jsonify({
            'success': True,
            'data': [
                {
                    'id_unit_kerja':
                        row.UNIT_KERJA_ID,

                    'nama_unit_kerja':
                        row.NAMA_UNIT_KERJA
                }
                for row in rows
            ]
        })

    except Exception:

        current_app.logger.exception(
            'Gagal mengambil Master Unit Kerja aktif'
        )

        return jsonify({
            'success': False,
            'error': 'Gagal mengambil Master Unit Kerja.'
        }), 500



def api_pembuatan_jadwal_siaga_save():
    """
    API SAVE PEMBUATAN JADWAL PIKET SIAGA.

    Business Rule:

        1. Satu SAVE = satu roster.
        2. Urutan roster otomatis mengikuti roster terakhir
           pada bulan + tahun + unit + fungsional + shift.
        3. Satu roster boleh berisi lebih dari satu pegawai.
        4. Satu pegawai tidak boleh berada pada roster berbeda
           dalam periode yang sama untuk unit + fungsional + shift.
        5. Duplicate NIP dalam satu input ditolak.
        6. Shift 1 = Shift 2 membuat pasangan roster otomatis.
        7. Pasangan otomatis Shift 2 tidak dianggap duplicate.
        8. Pengganti bukan bagian dari master roster dan akan
           ditangani pada proses jadwal harian/rejadwal.
        9. Database legacy tidak diubah struktur.

    Identifier pegawai:
        NIP pada tabel PEGAWAI adalah identifier resmi HRIS.
        Untuk pegawai non-ASN/PPPK, nilai NIP mengikuti ID/FingerID
        yang tersimpan pada master PEGAWAI.
    """

    try:
        data = request.get_json(silent=True) or {}

        bulan = str(
            data.get('bulan') or ''
        ).strip().zfill(2)

        tahun = str(
            data.get('tahun') or ''
        ).strip()

        shift = str(
            data.get('shift') or ''
        ).strip()

        unit_id = str(
            data.get('unit_kerja_id') or ''
        ).strip()

        fungsional = str(
            data.get('fungsional') or ''
        ).strip()

        pegawai = data.get('pegawai') or []

        shift1_sama_shift2 = bool(
            data.get('shift1_sama_shift2')
        )

        # ============================================================
        # VALIDASI INPUT DASAR
        # ============================================================

        if bulan not in {
            '01', '02', '03', '04', '05', '06',
            '07', '08', '09', '10', '11', '12'
        }:
            return jsonify({
                'success': False,
                'error': 'Bulan tidak valid.'
            }), 400

        if (
            len(tahun) != 4
            or not tahun.isdigit()
        ):
            return jsonify({
                'success': False,
                'error': 'Tahun tidak valid.'
            }), 400

        if shift not in ('1', '2'):
            return jsonify({
                'success': False,
                'error': 'Shift harus 1 atau 2.'
            }), 400

        if not unit_id:
            return jsonify({
                'success': False,
                'error': 'Unit kerja wajib dipilih.'
            }), 400

        if not fungsional:
            return jsonify({
                'success': False,
                'error': 'Jabatan siaga wajib dipilih.'
            }), 400

        if not isinstance(pegawai, list):
            return jsonify({
                'success': False,
                'error': 'Daftar pegawai tidak valid.'
            }), 400

        # ============================================================
        # NORMALISASI NIP INPUT
        # ============================================================

        nip_list = []

        for item in pegawai:

            if isinstance(item, dict):
                nip = str(
                    item.get('nip') or ''
                ).strip()
            else:
                nip = str(
                    item or ''
                ).strip()

            if not nip:
                continue

            if nip in nip_list:
                return jsonify({
                    'success': False,
                    'error': (
                        'Pegawai duplicate dalam roster: '
                        + nip
                    )
                }), 400

            nip_list.append(nip)

        if not nip_list:
            return jsonify({
                'success': False,
                'error': 'Minimal satu pegawai harus dipilih.'
            }), 400

        # ============================================================
        # VALIDASI PEGAWAI
        # ============================================================

        placeholders = ','.join(
            f':nip_{i}'
            for i in range(len(nip_list))
        )

        params = {
            f'nip_{i}': nip
            for i, nip in enumerate(nip_list)
        }

        rows = db.session.execute(
            db.text(f"""
                SELECT
                    NIP,
                    Nama,
                    UnitKerja,
                    FingerID
                FROM PEGAWAI
                WHERE NIP IN ({placeholders})
            """),
            params,
        ).mappings().all()

        pegawai_map = {
            str(r['NIP']).strip(): r
            for r in rows
        }

        tidak_ditemukan = [
            nip
            for nip in nip_list
            if nip not in pegawai_map
        ]

        if tidak_ditemukan:
            return jsonify({
                'success': False,
                'error': (
                    'Pegawai tidak ditemukan: '
                    + ', '.join(tidak_ditemukan)
                )
            }), 400

        # ============================================================
        # VALIDASI UNIT
        # ============================================================

        unit = db.session.execute(
            db.text("""
                SELECT
                    IDUnitKerja,
                    UnitKerjaName
                FROM MF_UNIT_KERJA
                WHERE IDUnitKerja = :unit_id
                LIMIT 1
            """),
            {
                'unit_id': unit_id
            },
        ).mappings().first()

        if not unit:
            return jsonify({
                'success': False,
                'error': 'Unit kerja tidak ditemukan.'
            }), 400

        # ============================================================
        # CEK PEGAWAI SUDAH ADA DI ROSTER LAIN
        #
        # Khusus pasangan Shift 1 = Shift 2:
        #   Shift target dianggap bagian dari pasangan roster
        #   yang sedang dibuat.
        #
        # Jadi duplicate dicek terhadap roster yang sudah ada,
        # bukan terhadap roster pasangan yang baru akan dibuat.
        # ============================================================

        existing_rows = db.session.execute(
            db.text("""
                SELECT
                    a.NIP,
                    a.GUIDTim,
                    t.NoUrutTim,
                    t.NamaTim,
                    t.IDUnitKerja,
                    t.FungsionalTIM,
                    t.Shift
                FROM MF_TIM_SIAGA_ANGGOTA a
                INNER JOIN MF_TIM_SIAGA t
                    ON t.GUIDTim = a.GUIDTim
                WHERE a.NIP IN (
                    SELECT NIP
                    FROM MF_TIM_SIAGA_ANGGOTA
                    WHERE NIP IN ("""
                    + placeholders
                    + """)
                )
                  AND a.BulanPeriode = :bulan
                  AND a.TahunPeriode = :tahun
                  AND a.IsAktif = 'Y'
                  AND t.BulanPeriode = :bulan
                  AND t.TahunPeriode = :tahun
                  AND t.IsAktif = 'Y'
            """),
            {
                **params,
                'bulan': bulan,
                'tahun': tahun,
            },
        ).mappings().all()

        if existing_rows:

            duplicate_messages = []

            for row in existing_rows:

                duplicate_messages.append(
                    (
                        f"{row['NIP']} sudah berada di "
                        f"roster {row['NoUrutTim']} "
                        f"({row['FungsionalTIM']} / "
                        f"Shift {row['Shift']})"
                    )
                )

            return jsonify({
                'success': False,
                'error': (
                    'Pegawai sudah memiliki roster: '
                    + '; '.join(
                        duplicate_messages
                    )
                ),
                'duplicates': [
                    dict(row)
                    for row in existing_rows
                ]
            }), 409

        # ============================================================
        # TENTUKAN NOMOR URUT BERIKUTNYA
        #
        # Nomor urut adalah urutan roster dalam kombinasi:
        #   bulan + tahun + unit + fungsional + shift
        #
        # Operator dapat melihat informasi roster terakhir
        # yang tersimpan.
        # ============================================================

        last_roster = db.session.execute(
            db.text("""
                SELECT
                    NoUrutTim,
                    NamaTim,
                    IDUnitKerja,
                    FungsionalTIM,
                    Shift
                FROM MF_TIM_SIAGA
                WHERE BulanPeriode = :bulan
                  AND TahunPeriode = :tahun
                  AND IDUnitKerja = :unit_id
                  AND FungsionalTIM = :fungsional
                  AND Shift = :shift
                  AND IsAktif = 'Y'
                ORDER BY NoUrutTim DESC
                LIMIT 1
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
                'shift': shift,
            },
        ).mappings().first()

        if last_roster:
            no_urut = (
                int(last_roster['NoUrutTim'] or 0)
                + 1
            )
        else:
            no_urut = 1

        # ============================================================
        # INFORMASI DATA TERAKHIR UNTUK OPERATOR
        # ============================================================

        last_saved = db.session.execute(
            db.text("""
                SELECT
                    t.NoUrutTim,
                    t.NamaTim,
                    t.IDUnitKerja,
                    u.UnitKerjaName,
                    t.FungsionalTIM,
                    t.Shift,
                    t.BulanPeriode,
                    t.TahunPeriode
                FROM MF_TIM_SIAGA t
                LEFT JOIN MF_UNIT_KERJA u
                    ON u.IDUnitKerja = t.IDUnitKerja
                WHERE t.BulanPeriode = :bulan
                  AND t.TahunPeriode = :tahun
                  AND t.IsAktif = 'Y'
                ORDER BY
                    t.UpdateDate DESC,
                    t.NoUrutTim DESC
                LIMIT 1
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
            },
        ).mappings().first()

        # ============================================================
        # BUAT GUID
        # ============================================================

        import uuid

        guid_tim = str(
            uuid.uuid4()
        )

        nama_tim = (
            f"{fungsional} "
            f"{unit['UnitKerjaName']} "
            f"#{no_urut} "
            f"{bulan}/{tahun}"
        )[:50]

        now = datetime.now()

        update_by = (
            getattr(
                getattr(g, 'user', None),
                'NIP',
                None,
            )
            or 'HRIS'
        )

        # ============================================================
        # INSERT ROSTER
        # ============================================================

        db.session.execute(
            db.text("""
                INSERT INTO MF_TIM_SIAGA (
                    NoUrutTim,
                    GUIDTim,
                    NamaTim,
                    IDUnitKerja,
                    IsAktif,
                    UpdateBy,
                    UpdateDate,
                    BulanPeriode,
                    TahunPeriode,
                    FungsionalTIM,
                    Shift
                )
                VALUES (
                    :no_urut,
                    :guid_tim,
                    :nama_tim,
                    :unit_id,
                    'Y',
                    :update_by,
                    :update_date,
                    :bulan,
                    :tahun,
                    :fungsional,
                    :shift
                )
            """),
            {
                'no_urut': no_urut,
                'guid_tim': guid_tim,
                'nama_tim': nama_tim,
                'unit_id': unit_id,
                'update_by': update_by,
                'update_date': now,
                'bulan': bulan,
                'tahun': tahun,
                'fungsional': fungsional,
                'shift': shift,
            },
        )

        # ============================================================
        # INSERT ANGGOTA
        # ============================================================

        for nomor, nip in enumerate(
            nip_list,
            start=1
        ):

            db.session.execute(
                db.text("""
                    INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                        GUIDTim,
                        NIP,
                        Fungsional,
                        IsAktif,
                        IDUnitKerja,
                        Nourut,
                        UpdateDate,
                        UpdateBy,
                        BulanPeriode,
                        TahunPeriode,
                        Shift
                    )
                    VALUES (
                        :guid_tim,
                        :nip,
                        :fungsional,
                        'Y',
                        :unit_id,
                        :nomor,
                        :update_date,
                        :update_by,
                        :bulan,
                        :tahun,
                        :shift
                    )
                """),
                {
                    'guid_tim': guid_tim,
                    'nip': nip,
                    'fungsional': fungsional,
                    'unit_id': unit_id,
                    'nomor': nomor,
                    'update_date': now,
                    'update_by': update_by,
                    'bulan': bulan,
                    'tahun': tahun,
                    'shift': shift,
                },
            )

        # ============================================================
        # SHIFT 1 = SHIFT 2
        # ============================================================

        pasangan_guid = None

        if (
            shift == '1'
            and shift1_sama_shift2
        ):

            pasangan_guid = str(
                uuid.uuid4()
            )

            pasangan_nama_tim = (
                f"{fungsional} "
                f"{unit['UnitKerjaName']} "
                f"#{no_urut} "
                f"{bulan}/{tahun}"
            )[:50]

            db.session.execute(
                db.text("""
                    INSERT INTO MF_TIM_SIAGA (
                        NoUrutTim,
                        GUIDTim,
                        NamaTim,
                        IDUnitKerja,
                        IsAktif,
                        UpdateBy,
                        UpdateDate,
                        BulanPeriode,
                        TahunPeriode,
                        FungsionalTIM,
                        Shift
                    )
                    VALUES (
                        :no_urut,
                        :guid_tim,
                        :nama_tim,
                        :unit_id,
                        'Y',
                        :update_by,
                        :update_date,
                        :bulan,
                        :tahun,
                        :fungsional,
                        '2'
                    )
                """),
                {
                    'no_urut': no_urut,
                    'guid_tim': pasangan_guid,
                    'nama_tim': pasangan_nama_tim,
                    'unit_id': unit_id,
                    'update_by': update_by,
                    'update_date': now,
                    'bulan': bulan,
                    'tahun': tahun,
                    'fungsional': fungsional,
                },
            )

            for nomor, nip in enumerate(
                nip_list,
                start=1
            ):

                db.session.execute(
                    db.text("""
                        INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                            GUIDTim,
                            NIP,
                            Fungsional,
                            IsAktif,
                            IDUnitKerja,
                            Nourut,
                            UpdateDate,
                            UpdateBy,
                            BulanPeriode,
                            TahunPeriode,
                            Shift
                        )
                        VALUES (
                            :guid_tim,
                            :nip,
                            :fungsional,
                            'Y',
                            :unit_id,
                            :nomor,
                            :update_date,
                            :update_by,
                            :bulan,
                            :tahun,
                            '2'
                        )
                    """),
                    {
                        'guid_tim': pasangan_guid,
                        'nip': nip,
                        'fungsional': fungsional,
                        'unit_id': unit_id,
                        'nomor': nomor,
                        'update_date': now,
                        'update_by': update_by,
                        'bulan': bulan,
                        'tahun': tahun,
                    },
                )

        # ============================================================
        # COMMIT
        # ============================================================

        db.session.commit()

        # ============================================================
        # RESPONSE
        # ============================================================

        response = {
            'success': True,
            'message': (
                f"Roster #{no_urut} berhasil disimpan."
            ),
            'roster': {
                'guid_tim': guid_tim,
                'no_urut': no_urut,
                'bulan': bulan,
                'tahun': tahun,
                'shift': shift,
                'unit_kerja_id': unit_id,
                'unit_kerja': unit['UnitKerjaName'],
                'fungsional': fungsional,
                'jumlah_pegawai': len(nip_list),
                'pegawai': [
                    {
                        'nip': nip,
                        'nama': (
                            pegawai_map[nip]['Nama']
                            or ''
                        ),
                    }
                    for nip in nip_list
                ],
            },
            'shift2_created': bool(
                pasangan_guid
            ),
            'last_saved_before': (
                dict(last_saved)
                if last_saved
                else None
            ),
        }

        return jsonify(response), 200

    except Exception as exc:

        db.session.rollback()

        current_app.logger.exception(
            "Gagal menyimpan jadwal piket siaga"
        )

        return jsonify({
            'success': False,
            'error': (
                'Gagal menyimpan jadwal piket siaga: '
                + str(exc)
            )
        }), 500


def data_siaga_cetak_daftar_lembur_siaga():
    """Render halaman Data Siaga Cetak Daftar Lembur Siaga."""
    return render_template('pages/dashboard_2/Data_Siaga_Cetak_Daftar_Lembur_Siaga.html')

def data_siaga_cetak_rekap_siaga():
    """Render halaman Data Siaga Cetak Rekap Siaga."""
    return render_template('pages/dashboard_2/Data_Siaga_Cetak_Rekap_Siaga.html')

def data_siaga_cetak_uang_siaga():
    """Render halaman Data Siaga Cetak Uang Siaga."""
    return render_template('pages/dashboard_2/Data_Siaga_Cetak_Uang_Siaga.html')

def data_siaga_jadwal_ulang():
    """Render halaman Data Siaga Jadwal Ulang."""
    return render_template('pages/dashboard_2/Data_Siaga_Jadwal_Ulang.html')

def api_rejadwal_siaga_get_jadwal():
    """Ambil jadwal aktif dan daftar rollback untuk unit, tanggal, dan shift terpilih."""
    try:
        unit_id = str(request.args.get('unit_kerja_id') or '').strip()
        tgl_raw = str(request.args.get('tgl') or '').strip()
        shift = str(request.args.get('shift') or '').strip()
        if not unit_id or not tgl_raw or not shift:
            return jsonify({'success': False, 'error': 'Unit, tanggal, dan shift wajib dipilih.'}), 400

        try:
            unit_id_int = int(unit_id)
            selected_date = datetime.strptime(tgl_raw, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Filter unit atau tanggal tidak valid.'}), 400

        query = LogActivity.query.filter(
            LogActivity.ACTIVITY == 'Piket Siaga',
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.UNIT_KERJA_ID == str(unit_id_int),
            LogActivity.SHIFT == shift
        )
        first_log = query.order_by(LogActivity.GUID_LOG.asc()).first()
        if not first_log:
            return jsonify({
                'success': True, 'guid_log': '', 'jadwal': [], 'rollback': [],
                'message': 'Jadwal tidak ditemukan untuk filter tersebut.'
            })

        guid_log = first_log.GUID_LOG
        try:
            rows = db.session.query(
                LogActivity, Pegawai, MfUnitKerja, MfOrgzSiaga, MfStatus
            ).outerjoin(Pegawai, LogActivity.NIP == Pegawai.NIP).outerjoin(
                MfUnitKerja, LogActivity.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID
            ).outerjoin(
                MfOrgzSiaga, LogActivity.FUNGSIONAL == MfOrgzSiaga.FUNGSIONAL
            ).outerjoin(
                MfStatus, LogActivity.STATUS_ID == MfStatus.STATUS_ID
            ).filter(
                LogActivity.ACTIVITY == 'Piket Siaga',
                LogActivity.GUID_LOG == guid_log,
                db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
                LogActivity.UNIT_KERJA_ID == str(unit_id_int),
                LogActivity.SHIFT == shift
            ).filter(
                db.or_(
                    LogActivity.STATUS_ID != 0,
                    LogActivity.NIP_PENGGANTI.is_(None),
                    LogActivity.NIP_PENGGANTI == ''
                )
            ).order_by(
                db.text("""
                    CASE
                      WHEN UPPER(COALESCE(MfUnitKerja.UNIT_KERJA_NAME, '')) LIKE 'KN %'
                        OR UPPER(COALESCE(MfUnitKerja.UNIT_KERJA_NAME, '')) LIKE '%KAPAL%'
                        OR UPPER(COALESCE(MfUnitKerja.UNIT_KERJA_NAME, '')) LIKE '%KN SAR%'
                      THEN CASE
                        WHEN UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) IN ('PW', 'PERWIRA')
                          OR UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) LIKE '%PERWIRA%' THEN 1
                        WHEN UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) = 'ABK'
                          OR UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) LIKE '%ABK%' THEN 2
                        ELSE 99 END
                      ELSE CASE
                        WHEN UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) IN ('KGR', 'KAGAHAR')
                          OR UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) LIKE '%KAGAHAR%' THEN 1
                        WHEN UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) IN ('KOM', 'KOMUNIKASI')
                          OR UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) LIKE '%KOMUNIKASI%' THEN 2
                        WHEN UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) IN ('RSC', 'RESCUER')
                          OR UPPER(COALESCE(LOG_ACTIVITIY.FUNGSIONAL, '')) LIKE '%RESCUER%' THEN 3
                        ELSE 99 END
                    END,
                    LOG_ACTIVITIY.FUNGSIONAL ASC,
                    LOG_ACTIVITIY.NIP ASC
                """)
            ).all()
        except Exception:
            db.session.rollback()
            rows = db.session.query(
                LogActivity, Pegawai, MfUnitKerja
            ).outerjoin(Pegawai, LogActivity.NIP == Pegawai.NIP).outerjoin(
                MfUnitKerja, LogActivity.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID
            ).filter(
                LogActivity.ACTIVITY == 'Piket Siaga',
                LogActivity.GUID_LOG == guid_log,
                db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
                LogActivity.UNIT_KERJA_ID == str(unit_id_int),
                LogActivity.SHIFT == shift
            ).order_by(LogActivity.NIP.asc()).all()

        jadwal_data = []
        for number, item in enumerate(rows, 1):
            if len(item) == 5:
                log, pegawai, unit, orgz, status = item
                status_text = status.STATUS if status else None
                bg_status = status.BG_STATUS if status else ''
            else:
                log, pegawai, unit = item
                status_text = None
                bg_status = ''
            if not status_text:
                status_text = {3: 'Hadir', 0: 'Tidak Hadir', 1: 'Dinas Luar/Cuti/Sakit', 2: 'Belum'}.get(log.STATUS_ID, 'Belum')
            jadwal_data.append({
                'no': number,
                'guid_log': log.GUID_LOG,
                'nip': log.NIP or '',
                'nama': pegawai.NAMA if pegawai else (log.NIP or '-'),
                'fungsional': log.FUNGSIONAL or '',
                'status_id': log.STATUS_ID,
                'status': status_text,
                'bg_status': bg_status,
                'unit_kerja': unit.UNIT_KERJA_NAME if unit else '',
                'shift': log.SHIFT or '',
                'act_date': log.ACTIVITY_DATE.strftime('%Y.%m.%d') if log.ACTIVITY_DATE else '',
                'status_trx': log.STATUS_TRX or '',
                'pengganti': log.PENGGANTI or 0,
                'transac_form': log.TRANSAKSI_FORM or '',
            })

        # Gunakan SQL fisik untuk tabel backup. Model ORM legacy memilih kolom
        # (mis. Biaya) yang tidak tersedia di database HRIS aktif, sehingga
        # query ORM gagal meskipun kolom itu tidak dipakai halaman ini.
        backups = db.session.execute(
            db.text("""
                SELECT
                    `IDBackUp` AS id_backup,
                    `GUIDLog` AS guid_log,
                    `NIP` AS nip,
                    `Fungsional` AS fungsional,
                    `Shift` AS shift,
                    `ActivityDate` AS activity_date
                FROM `LOG_ACTIVITIY_BACKUP`
                WHERE `Activity` = :activity
                  AND `GUIDBackUp` = :guid_backup
                  AND `GUIDLog` = :guid_log
                  AND DATE(`ActivityDate`) = :selected_date
                  AND `IDUnitKerja` = :unit_id
                  AND `Shift` = :shift
                ORDER BY `IDBackUp` ASC
            """),
            {
                'activity': 'Piket Siaga',
                'guid_backup': 'Delete Rejadwal',
                'guid_log': guid_log,
                'selected_date': selected_date,
                'unit_id': str(unit_id_int),
                'shift': shift,
            }
        ).mappings().all()

        rollback_data = []
        for number, backup in enumerate(backups, 1):
            pegawai = Pegawai.query.filter(Pegawai.NIP == backup['nip']).first()
            activity_date = backup['activity_date']
            rollback_data.append({
                'no': number,
                'id_backup': backup['id_backup'],
                'guid_log': backup['guid_log'],
                'nip': backup['nip'] or '-',
                'nama': pegawai.NAMA if pegawai else (backup['nip'] or '-'),
                'fungsional': backup['fungsional'] or '',
                'shift': backup['shift'] or '',
                'act_date': activity_date.strftime('%Y.%m.%d') if activity_date else '',
            })

        return jsonify({'success': True, 'guid_log': guid_log, 'jadwal': jadwal_data, 'rollback': rollback_data})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Gagal memuat jadwal ulang siaga')
        return jsonify({'success': False, 'error': 'Gagal memuat jadwal. Periksa log aplikasi.'}), 500

def api_rejadwal_siaga_edit_personil():
    """Ganti personel dengan jejak penggantian yang mengikuti pola HRIS 2013."""
    try:
        data = request.get_json(silent=True) or {}
        guid_log = str(data.get('guid_log') or '').strip()
        old_nip = str(data.get('old_nip') or '').strip()
        new_nip = str(data.get('new_nip') or '').strip()
        act_date = str(data.get('act_date') or '').strip().replace('.', '-')
        shift = str(data.get('shift') or '').strip()
        if not all([guid_log, old_nip, new_nip, act_date, shift]):
            return jsonify({'success': False, 'error': 'Data jadwal dan pegawai pengganti wajib lengkap.'}), 400
        if old_nip == new_nip:
            return jsonify({'success': False, 'error': 'Pegawai pengganti sama dengan pegawai saat ini.'}), 400
        try:
            selected_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Tanggal jadwal tidak valid.'}), 400

        old_log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == old_nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.SHIFT == shift,
            LogActivity.ACTIVITY == 'Piket Siaga'
        ).with_for_update().first()
        if not old_log:
            return jsonify({'success': False, 'error': 'Petugas yang akan diganti tidak ditemukan pada jadwal ini.'}), 404
        if int(old_log.PENGGANTI or 0) == 1:
            return jsonify({'success': False, 'error': 'Baris ini sudah merupakan petugas pengganti.'}), 409

        new_pegawai = Pegawai.query.filter(Pegawai.NIP == new_nip).first()
        if not new_pegawai:
            return jsonify({'success': False, 'error': 'Pegawai pengganti tidak ditemukan.'}), 404

        duplicate = LogActivity.query.filter(
            LogActivity.ACTIVITY == 'Piket Siaga',
            LogActivity.NIP == new_nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.SHIFT == shift,
            LogActivity.GUID_LOG == guid_log
        ).first()
        if duplicate:
            return jsonify({'success': False, 'error': 'Pegawai pengganti sudah terdaftar pada jadwal ini.'}), 409

        # HRIS 2013: Shift 1 tidak boleh diganti dengan pegawai yang sedang cuti,
        # sakit, atau dinas luar jenis SD/DL.
        if shift == '1':
            absensi_rows = db.session.execute(db.text("""
                SELECT LOWER(COALESCE(d.Transaksi, '')) AS transaksi,
                       UPPER(COALESCE(d.Jenis, '')) AS jenis
                FROM DinasLuar d
                INNER JOIN Pegawai p ON p.FingerID = d.FingerID
                WHERE p.NIP = :nip
                  AND DATE(d.TglAwalDinasLuar) <= :tgl
                  AND DATE(d.TglAkhirDinasLuar) >= :tgl
                  AND (
                    LOWER(COALESCE(d.Transaksi, '')) IN ('sakit', 'cuti')
                    OR (LOWER(COALESCE(d.Transaksi, '')) = 'dinasluar'
                        AND UPPER(COALESCE(d.Jenis, '')) IN ('SD', 'DL'))
                  )
            """), {'nip': new_nip, 'tgl': selected_date}).mappings().all()
            if absensi_rows:
                return jsonify({'success': False, 'error': 'Pegawai pengganti sedang cuti, sakit, atau dinas luar pada tanggal tersebut.'}), 409

        actor = str(session.get('nip') or session.get('NIP') or 'system')[:50]
        # Salin baris lama ke tabel backup sebelum mengubah roster.
        db.session.execute(db.text("""
            INSERT INTO LOG_ACTIVITIY_BACKUP
                (GUIDLog, Trx, Activity, StatusID, ActivityDate, Note, Tempat,
                 Perihal, UpdateBy, UpdateDate, GUIDTim, NIP, IDUnitKerja,
                 Fungsional, Pengganti, BackUpdate, GUIDBackUp, KetUpdate,
                 NIPPengganti, Shift)
            SELECT GUIDLog, Trx, Activity, StatusID, ActivityDate, Note, Tempat,
                   Perihal, :actor, NOW(), GUIDTim, NIP, IDUnitKerja,
                   Fungsional, Pengganti, NOW(), 'Edit Rejadwal',
                   KetUpdate, NIPPengganti, Shift
            FROM LOG_ACTIVITIY
            WHERE GUIDLog = :guid_log
              AND NIP = :old_nip
              AND DATE(ActivityDate) = :tgl
              AND Shift = :shift
              AND Activity = 'Piket Siaga'
        """), {'actor': actor, 'guid_log': guid_log, 'old_nip': old_nip, 'tgl': selected_date, 'shift': shift})

        # Pola HRIS 2013: baris pengganti mewarisi atribut jadwal; baris lama
        # ditandai StatusID=0 dan NIPPengganti agar riwayatnya tetap dapat ditelusuri.
        db.session.execute(db.text("""
            INSERT INTO LOG_ACTIVITIY
                (GUIDLog, Trx, Activity, StatusID, ActivityDate, Note, Tempat,
                 Perihal, UpdateBy, UpdateDate, GUIDTim, NIP, IDUnitKerja,
                 Fungsional, Pengganti, Shift, StatusTrx, NIPPengganti,
                 KetUpdate, TransacForm)
            SELECT GUIDLog, Trx, Activity, 2, ActivityDate, Note, Tempat,
                   Perihal, :actor, NOW(), GUIDTim, :new_nip, IDUnitKerja,
                   Fungsional, 1, Shift, '-', :new_nip,
                   :ket_update, 'Rejadwal Siaga'
            FROM LOG_ACTIVITIY
            WHERE GUIDLog = :guid_log
              AND NIP = :old_nip
              AND DATE(ActivityDate) = :tgl
              AND Shift = :shift
              AND Activity = 'Piket Siaga'
        """), {
            'actor': actor, 'new_nip': new_nip, 'ket_update': f'Rejadwal Siaga - pengganti {old_nip}',
            'guid_log': guid_log, 'old_nip': old_nip, 'tgl': selected_date, 'shift': shift
        })
        db.session.execute(db.text("""
            UPDATE LOG_ACTIVITIY
            SET StatusID = 0,
                UpdateBy = :actor,
                UpdateDate = NOW(),
                NIPPengganti = :new_nip,
                KetUpdate = :ket_update
            WHERE GUIDLog = :guid_log
              AND NIP = :old_nip
              AND DATE(ActivityDate) = :tgl
              AND Shift = :shift
              AND Activity = 'Piket Siaga'
        """), {
            'actor': actor, 'new_nip': new_nip, 'ket_update': f'Digantikan oleh {new_nip}',
            'guid_log': guid_log, 'old_nip': old_nip, 'tgl': selected_date, 'shift': shift
        })
        db.session.commit()
        return jsonify({'success': True, 'message': f'{old_nip} berhasil diganti oleh {new_pegawai.NAMA}.'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Gagal mengganti personel jadwal siaga')
        return jsonify({'success': False, 'error': 'Penggantian gagal. Perubahan dibatalkan.'}), 500

def api_rejadwal_siaga_delete_personil():
    """Backup satu baris jadwal ke LOG_ACTIVITIY_BACKUP lalu hapus secara atomik."""
    try:
        data = request.get_json(silent=True) or {}
        guid_log = str(data.get('guid_log') or '').strip()
        nip = str(data.get('nip') or '').strip()
        act_date = str(data.get('act_date') or '').strip().replace('.', '-')
        shift = str(data.get('shift') or '').strip()
        if not all([guid_log, nip, act_date, shift]):
            return jsonify({'success': False, 'error': 'Data personel belum lengkap.'}), 400
        try:
            selected_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Tanggal jadwal tidak valid.'}), 400

        log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.SHIFT == shift,
            LogActivity.ACTIVITY == 'Piket Siaga'
        ).with_for_update().first()
        if not log:
            return jsonify({'success': False, 'error': 'Personel tidak ditemukan pada jadwal terpilih.'}), 404

        actor = str(session.get('nip') or session.get('NIP') or 'system')[:50]
        backup = LogActivityBackup(
            GUID_LOG=log.GUID_LOG,
            TRX=log.TRX,
            ACTIVITY=log.ACTIVITY,
            STATUS_ID=log.STATUS_ID,
            ACTIVITY_DATE=log.ACTIVITY_DATE,
            NOTE=log.NOTE,
            TEMPAT=log.TEMPAT,
            PERIHAL=log.PERIHAL,
            UPDATE_BY=actor,
            UPDATE_DATE=datetime.now(),
            GUID_TIM=log.GUID_TIM,
            NIP=log.NIP,
            UNIT_KERJA_ID=log.UNIT_KERJA_ID,
            FUNGSIONAL=log.FUNGSIONAL,
            TGL_CLOSING=log.TGL_CLOSING,
            SHIFT_1=log.SHIFT_1,
            SHIFT_2=log.SHIFT_2,
            PENGGANTI=log.PENGGANTI,
            STATUS_TRX=log.STATUS_TRX,
            BACK_UPDATE=datetime.now(),
            GUID_BACKUP='Delete Rejadwal',
            KET_UPDATE=f'Delete Rejadwal - {log.NIP}',
            NIP_PENGGANTI=log.NIP_PENGGANTI,
            BIAYA=log.BIAYA,
            QTY=log.QTY,
            SATUAN_QTY=log.SATUAN_QTY,
            SHIFT=log.SHIFT,
            TGL_JAM_IN=log.TGL_JAM_IN,
            TGL_JAM_OUT=log.TGL_JAM_OUT,
            TGL_JAM_BAKU_IN=log.TGL_JAM_BAKU_IN,
            TGL_JAM_BAKU_OUT=log.TGL_JAM_BAKU_OUT
        )
        db.session.add(backup)
        db.session.delete(log)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Personel {nip} berhasil dihapus dan disimpan ke daftar rollback.'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Gagal menghapus personel jadwal siaga')
        return jsonify({'success': False, 'error': 'Penghapusan gagal. Tidak ada perubahan yang disimpan.'}), 500

def api_rejadwal_siaga_cancel_request():
    """
    API: Cancel request (ViewData) - Update StatusID = 2, StatusTrx = '-'
    """
    try:
        data = request.get_json()
        guid_log = data.get('guid_log', '')
        nip = data.get('nip', '')
        act_date = data.get('act_date', '')
        shift = data.get('shift', '')
        
        if not guid_log or not nip:
            return jsonify({'success': False, 'error': 'Data tidak lengkap'})
        
        act_date_fixed = act_date.replace('.', '-')
        act_date_obj = datetime.strptime(act_date_fixed, '%Y-%m-%d')
        
        log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == act_date_obj.date(),
            LogActivity.SHIFT == shift
        ).first()
        
        if not log:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        log.STATUS_ID = 2
        log.STATUS_TRX = '-'
        log.UPDATE_BY = 'admin'
        log.UPDATE_DATE = datetime.now()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Request berhasil dicancel'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


def api_rejadwal_siaga_batal_piket():
    """
    API: Batal piket (CloseData dari gridfind) - Update StatusID = 0
    """
    try:
        data = request.get_json()
        guid_log = data.get('guid_log', '')
        nip = data.get('nip', '')
        act_date = data.get('act_date', '')
        shift = data.get('shift', '')
        
        if not guid_log or not nip:
            return jsonify({'success': False, 'error': 'Data tidak lengkap'})
        
        act_date_fixed = act_date.replace('.', '-')
        act_date_obj = datetime.strptime(act_date_fixed, '%Y-%m-%d')
        
        log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == act_date_obj.date(),
            LogActivity.SHIFT == shift
        ).first()
        
        if not log:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        log.STATUS_ID = 0
        log.UPDATE_BY = 'admin'
        log.UPDATE_DATE = datetime.now()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Piket berhasil dibatalkan'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


def api_rejadwal_siaga_ubah_status():
    """Batalkan status request sesuai perilaku Ubahstatus pada HRIS 2013 (StatusID=2)."""
    try:
        data = request.get_json(silent=True) or {}
        guid_log = str(data.get('guid_log') or '').strip()
        nip = str(data.get('nip') or '').strip()
        act_date = str(data.get('act_date') or '').strip().replace('.', '-')
        shift = str(data.get('shift') or '').strip()
        if not all([guid_log, nip, act_date, shift]):
            return jsonify({'success': False, 'error': 'Data personel belum lengkap.'}), 400
        try:
            selected_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Tanggal jadwal tidak valid.'}), 400
        log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.SHIFT == shift,
            LogActivity.ACTIVITY == 'Piket Siaga'
        ).first()
        if not log:
            return jsonify({'success': False, 'error': 'Data jadwal tidak ditemukan.'}), 404
        log.STATUS_ID = 2
        log.STATUS_TRX = '-'
        log.UPDATE_BY = str(session.get('nip') or session.get('NIP') or 'system')[:50]
        log.UPDATE_DATE = datetime.now()
        db.session.commit()
        return jsonify({'success': True, 'message': f'Status request {nip} berhasil dikembalikan ke Pending.'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Gagal mengubah status jadwal siaga')
        return jsonify({'success': False, 'error': 'Status gagal diubah.'}), 500

def api_rejadwal_siaga_rollback():
    """Pulihkan baris yang dihapus dengan mempertahankan GUIDTim, unit, dan atribut legacy."""
    try:
        data = request.get_json(silent=True) or {}
        guid_log = str(data.get('guid_log') or '').strip()
        nip = str(data.get('nip') or '').strip()
        backup_id = data.get('id_backup', data.get('guid_log_backup'))
        if not guid_log or not nip or backup_id in (None, ''):
            return jsonify({'success': False, 'error': 'Data rollback belum lengkap.'}), 400
        try:
            backup_id = int(backup_id)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'ID backup tidak valid.'}), 400

        backup = db.session.get(LogActivityBackup, backup_id)
        if not backup or backup.GUID_BACKUP != 'Delete Rejadwal' or backup.GUID_LOG != guid_log or backup.NIP != nip:
            return jsonify({'success': False, 'error': 'Data backup tidak ditemukan atau tidak sesuai jadwal.'}), 404

        duplicate = LogActivity.query.filter(
            LogActivity.ACTIVITY == 'Piket Siaga',
            LogActivity.NIP == backup.NIP,
            db.func.date(LogActivity.ACTIVITY_DATE) == backup.ACTIVITY_DATE,
            LogActivity.SHIFT == backup.SHIFT
        ).first()
        if duplicate:
            return jsonify({'success': False, 'error': 'Personel sudah terjadwal pada tanggal dan shift ini.'}), 409

        restored = LogActivity(
            GUID_LOG=backup.GUID_LOG,
            TRAKSAKSI_ID=0,
            UNIT_KERJA_ID=backup.UNIT_KERJA_ID,
            GUID_LOG_BACKUP='',
            GUID_TIM=backup.GUID_TIM or '',
            STATUS_ID=2,
            NIP=backup.NIP,
            TRX=backup.TRX,
            ACTIVITY=backup.ACTIVITY,
            ACTIVITY_DATE=backup.ACTIVITY_DATE,
            NOTE=backup.NOTE,
            TEMPAT=backup.TEMPAT,
            PERIHAL=backup.PERIHAL,
            UPDATE_BY=str(session.get('nip') or session.get('NIP') or 'system')[:50],
            UPDATE_DATE=datetime.now(),
            FUNGSIONAL=backup.FUNGSIONAL,
            TGL_CLOSING=backup.TGL_CLOSING,
            SHIFT_1=backup.SHIFT_1,
            SHIFT_2=backup.SHIFT_2,
            PENGGANTI=backup.PENGGANTI or 0,
            STATUS_TRX=backup.STATUS_TRX,
            KET_UPDATE='Rollback personel terhapus',
            NIP_PENGGANTI=backup.NIP_PENGGANTI,
            BIAYA=backup.BIAYA,
            QTY=backup.QTY,
            SATUAN_QTY=backup.SATUAN_QTY,
            SHIFT=backup.SHIFT,
            TRANSAKSI_FORM=None,
            TGL_JAM_IN=backup.TGL_JAM_IN,
            TGL_JAM_OUT=backup.TGL_JAM_OUT,
            TGL_JAM_BAKU_IN=backup.TGL_JAM_BAKU_IN,
            TGL_JAM_BAKU_OUT=backup.TGL_JAM_BAKU_OUT
        )
        db.session.add(restored)
        db.session.delete(backup)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Personel {nip} berhasil dipulihkan.'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Gagal rollback jadwal siaga')
        return jsonify({'success': False, 'error': 'Rollback gagal. Tidak ada perubahan yang disimpan.'}), 500

def api_rejadwal_siaga_get_fungsional():
    """API: Get list Fungsional dari MfOrgzSiaga"""
    try:
        fungsional_list = db.session.query(MfOrgzSiaga.FUNGSIONAL).distinct().order_by(MfOrgzSiaga.URUT_FUNGSIONAL).all()
        data = [f[0] for f in fungsional_list if f[0]]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []})


def api_rejadwal_siaga_get_shift():
    """API: Get list Shift"""
    try:
        shift_list = MfShift.query.filter(MfShift.NAMA_SHIFT != '').order_by(MfShift.SHIFT_ID).all()
        data = [{'id': s.SHIFT_ID, 'nama': s.NAMA_SHIFT} for s in shift_list]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []})

def api_rejadwal_siaga_add_personil():
    """Tambah personel ke roster terpilih dengan validasi yang mengikuti HRIS 2013."""
    try:
        data = request.get_json(silent=True) or {}
        guid_log = str(data.get('guid_log') or '').strip()
        nip = str(data.get('nip') or '').strip()
        fungsional = str(data.get('fungsional') or '').strip()
        unit_raw = str(data.get('unit_kerja_id') or '').strip()
        tgl_raw = str(data.get('tgl') or '').strip()
        shift = str(data.get('shift') or '').strip()
        if not all([guid_log, nip, fungsional, unit_raw, tgl_raw, shift]):
            return jsonify({'success': False, 'error': 'Jadwal, unit, tanggal, shift, personel, dan fungsional wajib lengkap.'}), 400
        try:
            unit_id = int(unit_raw)
            selected_date = datetime.strptime(tgl_raw, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Unit atau tanggal tidak valid.'}), 400

        parent = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.ACTIVITY == 'Piket Siaga',
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.UNIT_KERJA_ID == str(unit_id),
            LogActivity.SHIFT == shift,
            LogActivity.FUNGSIONAL == fungsional,
            db.func.coalesce(LogActivity.PENGGANTI, 0) == 0
        ).first()
        if not parent or not parent.GUID_TIM:
            return jsonify({'success': False, 'error': 'Tim induk untuk fungsional tersebut tidak ditemukan pada jadwal ini.'}), 409

        pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
        if not pegawai:
            return jsonify({'success': False, 'error': 'Pegawai tidak ditemukan.'}), 404
        if str(getattr(pegawai, 'IS_KELUAR', '') or '').strip().upper() == 'Y':
            return jsonify({'success': False, 'error': 'Pegawai sudah tidak aktif.'}), 409

        existing = LogActivity.query.filter(
            LogActivity.ACTIVITY == 'Piket Siaga',
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.SHIFT == shift
        ).first()
        if existing:
            return jsonify({'success': False, 'error': 'Pegawai sudah terjadwal pada tanggal dan shift tersebut.'}), 409

        # Aturan HRIS 2013: shift 1 menolak personel yang sedang cuti/sakit/dinas luar SD atau DL.
        absensi = DinasLuar.query.join(
            Pegawai, DinasLuar.FINGER_ID == Pegawai.FINGER_ID
        ).filter(
            Pegawai.NIP == nip,
            db.func.date(DinasLuar.TGL_AWAL_DINAS_LUAR) <= selected_date,
            db.func.date(DinasLuar.TGL_AKHIR_DINAS_LUAR) >= selected_date,
            db.func.lower(DinasLuar.TRANSAKSI) != 'alpa'
        ).all()
        blocked = [
            row for row in absensi
            if (str(row.TRANSAKSI or '').strip().lower() in ('cuti', 'sakit')
                or (str(row.TRANSAKSI or '').strip().lower() == 'dinasluar'
                    and str(row.JENIS or '').strip().upper() in ('SD', 'DL')))
        ]
        if blocked and shift == '1':
            return jsonify({'success': False, 'error': 'Personel sedang cuti, sakit, atau dinas luar pada tanggal tersebut.'}), 409

        # Personel yang pernah dihapus harus dipulihkan melalui tombol Rollback.
        deleted_backup = LogActivityBackup.query.filter(
            LogActivityBackup.GUID_BACKUP == 'Delete Rejadwal',
            LogActivityBackup.ACTIVITY == 'Piket Siaga',
            LogActivityBackup.NIP == nip,
            db.func.date(LogActivityBackup.ACTIVITY_DATE) == selected_date,
            LogActivityBackup.UNIT_KERJA_ID == str(unit_id),
            LogActivityBackup.SHIFT == shift
        ).first()
        if deleted_backup:
            return jsonify({'success': False, 'error': 'Personel ada di daftar rollback. Gunakan tombol Rollback agar data lama dipulihkan utuh.'}), 409

        new_log = LogActivity(
            GUID_LOG=parent.GUID_LOG,
            TRAKSAKSI_ID=parent.TRAKSAKSI_ID or 0,
            UNIT_KERJA_ID=parent.UNIT_KERJA_ID,
            GUID_LOG_BACKUP='',
            GUID_TIM=parent.GUID_TIM,
            STATUS_ID=2,
            NIP=nip,
            TRX=parent.TRX or 'Jadwal Piket',
            ACTIVITY='Piket Siaga',
            ACTIVITY_DATE=selected_date,
            NOTE=parent.NOTE,
            TEMPAT=parent.TEMPAT,
            PERIHAL=parent.PERIHAL,
            UPDATE_BY=str(session.get('nip') or session.get('NIP') or 'system')[:50],
            UPDATE_DATE=datetime.now(),
            FUNGSIONAL=fungsional,
            TGL_CLOSING=None,
            SHIFT_1=0,
            SHIFT_2=0,
            PENGGANTI=1,
            STATUS_TRX='-',
            KET_UPDATE=f'Rejadwal Siaga - tambah personel {nip}',
            NIP_PENGGANTI=nip,
            SHIFT=shift,
            TRANSAKSI_FORM='Rejadwal Siaga'
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Personel {pegawai.NAMA} berhasil ditambahkan ke jadwal.'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Gagal menambah personel jadwal siaga')
        return jsonify({'success': False, 'error': 'Penambahan gagal. Tidak ada perubahan yang disimpan.'}), 500

def api_rejadwal_siaga_reset():
    """Reset jadwal mengikuti alur HRIS 2013 dalam satu transaksi database."""
    try:
        data = request.get_json(silent=True) or {}
        unit_raw = str(data.get('unit_kerja_id') or '').strip()
        tgl_raw = str(data.get('tgl') or '').strip()
        shift = str(data.get('shift') or '').strip()
        if not all([unit_raw, tgl_raw, shift]):
            return jsonify({'success': False, 'error': 'Unit, tanggal, dan shift wajib dipilih.'}), 400
        try:
            unit_id = int(unit_raw)
            selected_date = datetime.strptime(tgl_raw, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Unit atau tanggal tidak valid.'}), 400

        actor = str(session.get('nip') or session.get('NIP') or 'system')[:50]
        active = LogActivity.query.filter(
            LogActivity.ACTIVITY == 'Piket Siaga',
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.UNIT_KERJA_ID == str(unit_id),
            LogActivity.SHIFT == shift
        ).with_for_update().all()
        guid_logs = {row.GUID_LOG for row in active if row.GUID_LOG}
        if not active:
            return jsonify({'success': False, 'error': 'Tidak ada jadwal untuk di-reset.'}), 404

        # Hapus hanya personel pengganti/entri Rejadwal; roster asli dipertahankan.
        for row in active:
            if (row.PENGGANTI or 0) != 0 or (row.TRANSAKSI_FORM or '').strip().lower() == 'rejadwal siaga':
                db.session.delete(row)
            elif (row.PENGGANTI or 0) == 0:
                row.STATUS_ID = 2
                row.UPDATE_BY = actor
                row.UPDATE_DATE = datetime.now()

        backups = LogActivityBackup.query.filter(
            LogActivityBackup.ACTIVITY == 'Piket Siaga',
            LogActivityBackup.GUID_BACKUP == 'Delete Rejadwal',
            db.func.date(LogActivityBackup.ACTIVITY_DATE) == selected_date,
            LogActivityBackup.UNIT_KERJA_ID == str(unit_id),
            LogActivityBackup.SHIFT == shift,
            db.func.coalesce(LogActivityBackup.PENGGANTI, 0) == 0
        ).with_for_update().all()
        restored_count = 0
        for backup in backups:
            exists = LogActivity.query.filter(
                LogActivity.ACTIVITY == 'Piket Siaga',
                LogActivity.NIP == backup.NIP,
                db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
                LogActivity.UNIT_KERJA_ID == str(unit_id),
                LogActivity.SHIFT == shift
            ).first()
            if not exists:
                db.session.add(LogActivity(
                    GUID_LOG=backup.GUID_LOG,
                    TRAKSAKSI_ID=0,
                    UNIT_KERJA_ID=backup.UNIT_KERJA_ID,
                    GUID_LOG_BACKUP='',
                    GUID_TIM=backup.GUID_TIM or '',
                    STATUS_ID=2,
                    NIP=backup.NIP,
                    TRX=backup.TRX,
                    ACTIVITY=backup.ACTIVITY,
                    ACTIVITY_DATE=backup.ACTIVITY_DATE,
                    NOTE=backup.NOTE,
                    TEMPAT=backup.TEMPAT,
                    PERIHAL=backup.PERIHAL,
                    UPDATE_BY=actor,
                    UPDATE_DATE=datetime.now(),
                    FUNGSIONAL=backup.FUNGSIONAL,
                    TGL_CLOSING=backup.TGL_CLOSING,
                    SHIFT_1=backup.SHIFT_1,
                    SHIFT_2=backup.SHIFT_2,
                    PENGGANTI=backup.PENGGANTI or 0,
                    STATUS_TRX=None,
                    KET_UPDATE='Reset jadwal - pemulihan roster asli',
                    NIP_PENGGANTI=backup.NIP_PENGGANTI,
                    SHIFT=backup.SHIFT,
                    TRANSAKSI_FORM=None
                ))
                restored_count += 1
            db.session.delete(backup)

        # Tandai pegawai yang sedang cuti/sakit/dinas luar sebagaimana HRIS 2013.
        originals = LogActivity.query.filter(
            LogActivity.ACTIVITY == 'Piket Siaga',
            db.func.date(LogActivity.ACTIVITY_DATE) == selected_date,
            LogActivity.UNIT_KERJA_ID == str(unit_id),
            LogActivity.SHIFT == shift,
            db.func.coalesce(LogActivity.PENGGANTI, 0) == 0
        ).all()
        for row in originals:
            absensi_rows = DinasLuar.query.join(
                Pegawai, DinasLuar.FINGER_ID == Pegawai.FINGER_ID
            ).filter(
                Pegawai.NIP == row.NIP,
                db.func.date(DinasLuar.TGL_AWAL_DINAS_LUAR) <= selected_date,
                db.func.date(DinasLuar.TGL_AKHIR_DINAS_LUAR) >= selected_date,
                db.func.lower(DinasLuar.TRANSAKSI) != 'alpa'
            ).all()
            matching = next((item for item in absensi_rows if
                str(item.TRANSAKSI or '').strip().lower() in ('cuti', 'sakit')
                or (str(item.TRANSAKSI or '').strip().lower() == 'dinasluar'
                    and str(item.JENIS or '').strip().upper() in ('SD', 'DL'))), None)
            if matching:
                transaksi = 'DL' if str(matching.TRANSAKSI or '').strip().lower() == 'dinasluar' else matching.TRANSAKSI
                row.STATUS_ID = 1
                row.STATUS_TRX = transaksi
                row.UPDATE_BY = actor
                row.UPDATE_DATE = datetime.now()

        db.session.commit()
        return jsonify({'success': True, 'message': f'Reset jadwal berhasil. {restored_count} personel dipulihkan.'})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Gagal reset jadwal siaga')
        return jsonify({'success': False, 'error': 'Reset gagal. Semua perubahan dibatalkan.'}), 500

def data_siaga_membuat_jadwal_piket_siaga():
    """Render halaman Data Siaga Membuat Jadwal Piket Siaga."""
    return render_template('pages/dashboard_2/Data_Siaga_Membuat_Jadwal_Piket_Siaga.html')

def data_siaga_view_jadwal():
    return render_template(
        'pages/dashboard_2/Data_Siaga_View_Jadwal.html'
    )

def api_siaga_view_jadwal_get():
    """
    API READ-ONLY VIEW JADWAL SIAGA.

    Sumber:
        MF_TIM_SIAGA
        MF_TIM_SIAGA_ANGGOTA
        MF_UNIT_KERJA
        PEGAWAI

    Tidak melakukan INSERT / UPDATE / DELETE.
    """

    try:
        bulan = str(
            request.args.get('bulan') or ''
        ).strip().zfill(2)

        tahun = str(
            request.args.get('tahun') or ''
        ).strip()

        unit_id = str(
            request.args.get('unit_kerja_id') or ''
        ).strip()

        fungsional = str(
            request.args.get('fungsional') or ''
        ).strip()

        if bulan not in {
            '01', '02', '03', '04', '05', '06',
            '07', '08', '09', '10', '11', '12'
        }:
            return jsonify({
                'success': False,
                'error': 'Bulan tidak valid.'
            }), 400

        if len(tahun) != 4 or not tahun.isdigit():
            return jsonify({
                'success': False,
                'error': 'Tahun tidak valid.'
            }), 400

        if not unit_id:
            return jsonify({
                'success': False,
                'error': 'Unit kerja wajib dipilih.'
            }), 400

        if not fungsional:
            return jsonify({
                'success': False,
                'error': 'Jabatan siaga wajib dipilih.'
            }), 400

        rows = db.session.execute(
            db.text("""
                SELECT
                    t.NoUrutTim,
                    t.GUIDTim,
                    t.NamaTim,
                    t.IDUnitKerja,
                    u.UnitKerjaName,
                    t.FungsionalTIM,
                    t.Shift AS RosterShift,
                    t.BulanPeriode,
                    t.TahunPeriode,
                    t.IsAktif AS RosterAktif,
                    a.Nourut,
                    a.NIP,
                    p.Nama AS NamaPegawai,
                    a.Fungsional AS FungsionalAnggota,
                    a.Shift AS AnggotaShift,
                    a.IsAktif AS AnggotaAktif
                FROM MF_TIM_SIAGA t
                LEFT JOIN MF_TIM_SIAGA_ANGGOTA a
                    ON a.GUIDTim = t.GUIDTim
                LEFT JOIN PEGAWAI p
                    ON p.NIP = a.NIP
                LEFT JOIN MF_UNIT_KERJA u
                    ON u.IDUnitKerja = t.IDUnitKerja
                WHERE t.BulanPeriode = :bulan
                  AND t.TahunPeriode = :tahun
                  AND t.IDUnitKerja = :unit_id
                  AND t.FungsionalTIM = :fungsional
                ORDER BY
                    t.NoUrutTim ASC,
                    t.Shift ASC,
                    a.Nourut ASC
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
            }
        ).mappings().all()

        data = []

        for row in rows:
            data.append({
                'no_urut': row['NoUrutTim'],
                'guid_tim': row['GUIDTim'],
                'nama_tim': row['NamaTim'],
                'unit_id': row['IDUnitKerja'],
                'unit_name': row['UnitKerjaName'],
                'fungsional': row['FungsionalTIM'],
                'shift': row['RosterShift'],
                'bulan': row['BulanPeriode'],
                'tahun': row['TahunPeriode'],
                'roster_aktif': row['RosterAktif'],
                'nourut': row['Nourut'],
                'nip': row['NIP'],
                'nama_pegawai': row['NamaPegawai'],
                'fungsional_anggota':
                    row['FungsionalAnggota'],
                'shift_anggota':
                    row['AnggotaShift'],
                'anggota_aktif':
                    row['AnggotaAktif'],
            })

        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e),
        }), 500

def api_siaga_view_jadwal_edit():
    """
    API EDIT SATU ROSTER JADWAL SIAGA.

    BUSINESS RULE FINAL:

    1. Satu request = satu roster logis.
    2. Identitas roster:
           bulan
           tahun
           unit_kerja_id
           fungsional
           no_urut
    3. NIP harus valid di PEGAWAI.
    4. NIP duplicate dalam roster ditolak.
    5. NIP yang sudah aktif pada roster lain ditolak.
    6. Jika roster memiliki Shift 1 + Shift 2:
           kedua shift diperbarui.
    7. Jika roster hanya memiliki Shift 1:
           Shift 1 diperbarui
           DAN Shift 2 otomatis dibuat.
    8. Anggota Shift 2 selalu sama dengan anggota
       roster yang disimpan.
    9. Shift 1 tidak pernah dihapus.
   10. Shift 2 yang sudah ada tidak dibuat ulang.
   11. Tidak mengubah struktur database.
   12. Transactional.
    """

    try:

        data = request.get_json(silent=True) or {}

        bulan = str(
            data.get('bulan') or ''
        ).strip().zfill(2)

        tahun = str(
            data.get('tahun') or ''
        ).strip()

        unit_id = str(
            data.get('unit_kerja_id') or ''
        ).strip()

        fungsional = str(
            data.get('fungsional') or ''
        ).strip()

        no_urut = data.get('no_urut')

        pegawai = data.get('pegawai') or []

        # ========================================================
        # VALIDASI IDENTITAS
        # ========================================================

        if bulan not in {
            '01', '02', '03', '04', '05', '06',
            '07', '08', '09', '10', '11', '12'
        }:
            return jsonify({
                'success': False,
                'error': 'Bulan tidak valid.'
            }), 400

        if (
            len(tahun) != 4
            or not tahun.isdigit()
        ):
            return jsonify({
                'success': False,
                'error': 'Tahun tidak valid.'
            }), 400

        if not unit_id:
            return jsonify({
                'success': False,
                'error': 'Unit kerja wajib diisi.'
            }), 400

        if not fungsional:
            return jsonify({
                'success': False,
                'error': 'Jabatan siaga wajib diisi.'
            }), 400

        try:
            no_urut = int(no_urut)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'error': 'Nomor roster tidak valid.'
            }), 400

        if no_urut < 1:
            return jsonify({
                'success': False,
                'error': 'Nomor roster tidak valid.'
            }), 400

        # ========================================================
        # NORMALISASI NIP
        # ========================================================

        nip_list = []

        for item in pegawai:

            if isinstance(item, dict):
                nip = str(
                    item.get('nip') or ''
                ).strip()
            else:
                nip = str(item or '').strip()

            if nip:
                nip_list.append(nip)

        if not nip_list:
            return jsonify({
                'success': False,
                'error': 'Minimal satu pegawai harus dipilih.'
            }), 400

        if len(nip_list) != len(set(nip_list)):
            return jsonify({
                'success': False,
                'error': 'Terdapat NIP yang sama dalam roster.'
            }), 400

        # ========================================================
        # LOCK ROSTER
        # ========================================================

        rows = db.session.execute(
            db.text("""
                SELECT
                    GUIDTim,
                    Shift,
                    NoUrutTim,
                    NamaTim,
                    IDUnitKerja,
                    IsAktif,
                    UpdateBy,
                    UpdateDate,
                    FungsionalTIM,
                    BulanPeriode,
                    TahunPeriode
                FROM MF_TIM_SIAGA
                WHERE BulanPeriode = :bulan
                  AND TahunPeriode = :tahun
                  AND IDUnitKerja = :unit_id
                  AND FungsionalTIM = :fungsional
                  AND NoUrutTim = :no_urut
                ORDER BY Shift
                FOR UPDATE
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
                'no_urut': no_urut,
            }
        ).mappings().all()

        if not rows:
            return jsonify({
                'success': False,
                'error': 'Roster tidak ditemukan.'
            }), 404

        shift_map = {
            str(row['Shift']): row
            for row in rows
            if row['Shift'] is not None
        }

        if '1' not in shift_map:
            return jsonify({
                'success': False,
                'error': 'Shift 1 pada roster tidak ditemukan.'
            }), 400

        # ========================================================
        # VALIDASI MASTER PEGAWAI
        # ========================================================

        placeholders = ','.join(
            f':nip_{i}'
            for i in range(len(nip_list))
        )

        pegawai_params = {
            f'nip_{i}': nip
            for i, nip in enumerate(nip_list)
        }

        pegawai_rows = db.session.execute(
            db.text(f"""
                SELECT
                    NIP,
                    Nama
                FROM PEGAWAI
                WHERE NIP IN ({placeholders})
            """),
            pegawai_params
        ).mappings().all()

        pegawai_map = {
            str(row['NIP']).strip(): row['Nama']
            for row in pegawai_rows
        }

        missing = [
            nip
            for nip in nip_list
            if nip not in pegawai_map
        ]

        if missing:
            return jsonify({
                'success': False,
                'error': (
                    'Pegawai tidak ditemukan: '
                    + ', '.join(missing)
                )
            }), 400

        # ========================================================
        # VALIDASI DUPLIKASI DI ROSTER LAIN
        # ========================================================

        duplicate_rows = db.session.execute(
            db.text("""
                SELECT
                    a.NIP,
                    t.NoUrutTim,
                    t.Shift
                FROM MF_TIM_SIAGA_ANGGOTA a
                INNER JOIN MF_TIM_SIAGA t
                    ON t.GUIDTim = a.GUIDTim
                WHERE t.BulanPeriode = :bulan
                  AND t.TahunPeriode = :tahun
                  AND t.IDUnitKerja = :unit_id
                  AND t.FungsionalTIM = :fungsional
                  AND a.NIP IN :nip_list
                  AND t.NoUrutTim <> :no_urut
                  AND a.IsAktif = 'Y'
            """).bindparams(
                db.bindparam(
                    'nip_list',
                    expanding=True
                )
            ),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
                'nip_list': nip_list,
                'no_urut': no_urut,
            }
        ).mappings().all()

        if duplicate_rows:

            duplicate_nips = sorted({
                str(row['NIP'])
                for row in duplicate_rows
            })

            return jsonify({
                'success': False,
                'error': (
                    'Pegawai sudah berada pada roster lain: '
                    + ', '.join(duplicate_nips)
                )
            }), 400

        # ========================================================
        # USER / AUDIT
        # ========================================================

        update_by = (
            getattr(
                getattr(g, 'user', None),
                'username',
                None
            )
            or 'HRIS'
        )

        update_date = datetime.now()

        # ========================================================
        # TENTUKAN SHIFT YANG AKAN DIPROSES
        # ========================================================

        shift1 = shift_map['1']

        if '2' in shift_map:
            target_shifts = [
                shift1,
                shift_map['2']
            ]
            shift2_created = False

        else:
            target_shifts = [
                shift1
            ]
            shift2_created = True

        # ========================================================
        # UPDATE ANGGOTA SHIFT YANG SUDAH ADA
        #
        # Tidak DELETE fisik.
        # Record lama dibuat tidak aktif.
        # Jika record NIP sudah pernah ada tetapi tidak aktif,
        # record tersebut diaktifkan kembali agar aman terhadap
        # PRIMARY KEY (GUIDTim, NIP).
        # ========================================================

        for row in target_shifts:

            guid_tim = str(row['GUIDTim'])
            shift = str(row['Shift'])

            db.session.execute(
                db.text("""
                    UPDATE MF_TIM_SIAGA_ANGGOTA
                    SET
                        IsAktif = 'N',
                        UpdateDate = :update_date,
                        UpdateBy = :update_by
                    WHERE GUIDTim = :guid_tim
                      AND IsAktif = 'Y'
                """),
                {
                    'guid_tim': guid_tim,
                    'update_date': update_date,
                    'update_by': update_by,
                }
            )

            for nomor, nip in enumerate(
                nip_list,
                start=1
            ):

                existing = db.session.execute(
                    db.text("""
                        SELECT
                            GUIDTim,
                            NIP
                        FROM MF_TIM_SIAGA_ANGGOTA
                        WHERE GUIDTim = :guid_tim
                          AND NIP = :nip
                        LIMIT 1
                    """),
                    {
                        'guid_tim': guid_tim,
                        'nip': nip,
                    }
                ).mappings().first()

                if existing:

                    db.session.execute(
                        db.text("""
                            UPDATE MF_TIM_SIAGA_ANGGOTA
                            SET
                                Fungsional = :fungsional,
                                IsAktif = 'Y',
                                IDUnitKerja = :unit_id,
                                Nourut = :nomor,
                                UpdateDate = :update_date,
                                UpdateBy = :update_by,
                                BulanPeriode = :bulan,
                                TahunPeriode = :tahun,
                                Shift = :shift
                            WHERE GUIDTim = :guid_tim
                              AND NIP = :nip
                        """),
                        {
                            'guid_tim': guid_tim,
                            'nip': nip,
                            'fungsional': fungsional,
                            'unit_id': unit_id,
                            'nomor': nomor,
                            'update_date': update_date,
                            'update_by': update_by,
                            'bulan': bulan,
                            'tahun': tahun,
                            'shift': shift,
                        }
                    )

                else:

                    db.session.execute(
                        db.text("""
                            INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                                GUIDTim,
                                NIP,
                                Fungsional,
                                IsAktif,
                                IDUnitKerja,
                                Nourut,
                                UpdateDate,
                                UpdateBy,
                                BulanPeriode,
                                TahunPeriode,
                                Shift
                            )
                            VALUES (
                                :guid_tim,
                                :nip,
                                :fungsional,
                                'Y',
                                :unit_id,
                                :nomor,
                                :update_date,
                                :update_by,
                                :bulan,
                                :tahun,
                                :shift
                            )
                        """),
                        {
                            'guid_tim': guid_tim,
                            'nip': nip,
                            'fungsional': fungsional,
                            'unit_id': unit_id,
                            'nomor': nomor,
                            'update_date': update_date,
                            'update_by': update_by,
                            'bulan': bulan,
                            'tahun': tahun,
                            'shift': shift,
                        }
                    )

        # ========================================================
        # BUAT SHIFT 2 JIKA BELUM ADA
        # ========================================================

        if shift2_created:

            new_guid_row = db.session.execute(
                db.text("""
                    SELECT UUID() AS GUIDTim
                """)
            ).mappings().first()

            new_guid = str(
                new_guid_row['GUIDTim']
            )

            db.session.execute(
                db.text("""
                    INSERT INTO MF_TIM_SIAGA (
                        NoUrutTim,
                        GUIDTim,
                        NamaTim,
                        IDUnitKerja,
                        IsAktif,
                        UpdateBy,
                        UpdateDate,
                        BulanPeriode,
                        TahunPeriode,
                        FungsionalTIM,
                        Shift
                    )
                    VALUES (
                        :no_urut,
                        :guid_tim,
                        :nama_tim,
                        :unit_id,
                        :is_aktif,
                        :update_by,
                        :update_date,
                        :bulan,
                        :tahun,
                        :fungsional,
                        '2'
                    )
                """),
                {
                    'no_urut': no_urut,
                    'guid_tim': new_guid,
                    'nama_tim': shift1['NamaTim'],
                    'unit_id': unit_id,
                    'is_aktif': shift1['IsAktif'] or 'Y',
                    'update_by': update_by,
                    'update_date': update_date,
                    'bulan': bulan,
                    'tahun': tahun,
                    'fungsional': fungsional,
                }
            )

            for nomor, nip in enumerate(
                nip_list,
                start=1
            ):

                db.session.execute(
                    db.text("""
                        INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                            GUIDTim,
                            NIP,
                            Fungsional,
                            IsAktif,
                            IDUnitKerja,
                            Nourut,
                            UpdateDate,
                            UpdateBy,
                            BulanPeriode,
                            TahunPeriode,
                            Shift
                        )
                        VALUES (
                            :guid_tim,
                            :nip,
                            :fungsional,
                            'Y',
                            :unit_id,
                            :nomor,
                            :update_date,
                            :update_by,
                            :bulan,
                            :tahun,
                            '2'
                        )
                    """),
                    {
                        'guid_tim': new_guid,
                        'nip': nip,
                        'fungsional': fungsional,
                        'unit_id': unit_id,
                        'nomor': nomor,
                        'update_date': update_date,
                        'update_by': update_by,
                        'bulan': bulan,
                        'tahun': tahun,
                    }
                )

        # ========================================================
        # COMMIT
        # ========================================================

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Roster #{no_urut} berhasil diperbarui.'
            ),
            'data': {
                'bulan': bulan,
                'tahun': tahun,
                'unit_kerja_id': unit_id,
                'fungsional': fungsional,
                'no_urut': no_urut,
                'shift_1': True,
                'shift_2': True,
                'shift_2_created': shift2_created,
                'pegawai': [
                    {
                        'nip': nip,
                        'nama': pegawai_map.get(nip, '')
                    }
                    for nip in nip_list
                ]
            }
        })

    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            'Gagal edit roster jadwal siaga'
        )

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def api_siaga_view_jadwal_lengkapi_shift2():
    """
    API LENGKAPI SHIFT 2 ROSTER JADWAL SIAGA.

    Digunakan untuk roster yang sudah memiliki Shift 1
    tetapi belum memiliki Shift 2.

    Business Rule:

        1. Identitas roster:
               bulan
               tahun
               unit_kerja_id
               fungsional
               no_urut

        2. Shift 1 wajib tersedia.

        3. Shift 2 wajib belum tersedia.

        4. Anggota Shift 2 dibuat sama persis dengan
           anggota Shift 1.

        5. GUIDTim baru dibuat untuk Shift 2.

        6. Nourut mengikuti anggota Shift 1.

        7. Tidak mengubah anggota Shift 1.

        8. Tidak membuat Shift 2 jika sudah ada.

        9. Transactional.

       10. Struktur database tidak diubah.
    """

    try:

        data = request.get_json(silent=True) or {}

        bulan = str(
            data.get('bulan') or ''
        ).strip().zfill(2)

        tahun = str(
            data.get('tahun') or ''
        ).strip()

        unit_id = str(
            data.get('unit_kerja_id') or ''
        ).strip()

        fungsional = str(
            data.get('fungsional') or ''
        ).strip()

        no_urut = data.get('no_urut')

        if bulan not in {
            '01', '02', '03', '04', '05', '06',
            '07', '08', '09', '10', '11', '12'
        }:
            return jsonify({
                'success': False,
                'error': 'Bulan tidak valid.'
            }), 400

        if (
            len(tahun) != 4
            or not tahun.isdigit()
        ):
            return jsonify({
                'success': False,
                'error': 'Tahun tidak valid.'
            }), 400

        if not unit_id:
            return jsonify({
                'success': False,
                'error': 'Unit kerja wajib diisi.'
            }), 400

        if not fungsional:
            return jsonify({
                'success': False,
                'error': 'Jabatan siaga wajib diisi.'
            }), 400

        try:
            no_urut = int(no_urut)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'error': 'Nomor roster tidak valid.'
            }), 400

        if no_urut < 1:
            return jsonify({
                'success': False,
                'error': 'Nomor roster tidak valid.'
            }), 400

        # ============================================================
        # AMBIL ROSTER DAN KUNCI TRANSAKSI
        # ============================================================

        rows = db.session.execute(
            db.text("""
                SELECT
                    GUIDTim,
                    Shift,
                    NoUrutTim,
                    NamaTim,
                    IDUnitKerja,
                    IsAktif,
                    UpdateBy,
                    FungsionalTIM,
                    BulanPeriode,
                    TahunPeriode
                FROM MF_TIM_SIAGA
                WHERE BulanPeriode = :bulan
                  AND TahunPeriode = :tahun
                  AND IDUnitKerja = :unit_id
                  AND FungsionalTIM = :fungsional
                  AND NoUrutTim = :no_urut
                ORDER BY Shift
                FOR UPDATE
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
                'no_urut': no_urut,
            }
        ).mappings().all()

        if not rows:
            return jsonify({
                'success': False,
                'error': 'Roster tidak ditemukan.'
            }), 404

        shifts = {
            str(row['Shift'])
            for row in rows
            if row['Shift'] is not None
        }

        if '1' not in shifts:
            return jsonify({
                'success': False,
                'error': 'Shift 1 pada roster tidak ditemukan.'
            }), 400

        if '2' in shifts:
            return jsonify({
                'success': False,
                'error': 'Shift 2 pada roster sudah tersedia.'
            }), 409

        # ============================================================
        # AMBIL ANGGOTA SHIFT 1
        # ============================================================

        shift1 = next(
            row for row in rows
            if str(row['Shift']) == '1'
        )

        anggota = db.session.execute(
            db.text("""
                SELECT
                    NIP,
                    Fungsional,
                    IsAktif,
                    IDUnitKerja,
                    Nourut,
                    UpdateBy
                FROM MF_TIM_SIAGA_ANGGOTA
                WHERE GUIDTim = :guid_tim
                ORDER BY Nourut
            """),
            {
                'guid_tim': shift1['GUIDTim']
            }
        ).mappings().all()

        if not anggota:
            return jsonify({
                'success': False,
                'error': 'Shift 1 tidak memiliki anggota.'
            }), 400

        # ============================================================
        # BUAT GUID SHIFT 2
        # ============================================================

        pasangan_guid = str(
            uuid.uuid4()
        )

        now = datetime.now()

        update_by = (
            getattr(g, 'username', None)
            or getattr(g, 'user', None)
            or 'system'
        )

        if hasattr(update_by, 'username'):
            update_by = update_by.username

        update_by = str(update_by)[:50]

        # ============================================================
        # NAMA TIM SHIFT 2
        # ============================================================

        nama_tim = shift1['NamaTim']

        # ============================================================
        # INSERT MASTER SHIFT 2
        # ============================================================

        db.session.execute(
            db.text("""
                INSERT INTO MF_TIM_SIAGA (
                    NoUrutTim,
                    GUIDTim,
                    NamaTim,
                    IDUnitKerja,
                    IsAktif,
                    UpdateBy,
                    UpdateDate,
                    BulanPeriode,
                    TahunPeriode,
                    FungsionalTIM,
                    Shift
                )
                VALUES (
                    :no_urut,
                    :guid_tim,
                    :nama_tim,
                    :unit_id,
                    :is_aktif,
                    :update_by,
                    :update_date,
                    :bulan,
                    :tahun,
                    :fungsional,
                    '2'
                )
            """),
            {
                'no_urut': no_urut,
                'guid_tim': pasangan_guid,
                'nama_tim': nama_tim,
                'unit_id': unit_id,
                'is_aktif': shift1['IsAktif'] or 'Y',
                'update_by': update_by,
                'update_date': now,
                'bulan': bulan,
                'tahun': tahun,
                'fungsional': fungsional,
            }
        )

        # ============================================================
        # SALIN ANGGOTA SHIFT 1 -> SHIFT 2
        # ============================================================

        for anggota_row in anggota:

            db.session.execute(
                db.text("""
                    INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                        GUIDTim,
                        NIP,
                        Fungsional,
                        IsAktif,
                        IDUnitKerja,
                        Nourut,
                        UpdateDate,
                        UpdateBy,
                        BulanPeriode,
                        TahunPeriode,
                        Shift
                    )
                    VALUES (
                        :guid_tim,
                        :nip,
                        :fungsional,
                        :is_aktif,
                        :unit_id,
                        :nourut,
                        :update_date,
                        :update_by,
                        :bulan,
                        :tahun,
                        '2'
                    )
                """),
                {
                    'guid_tim': pasangan_guid,
                    'nip': anggota_row['NIP'],
                    'fungsional': anggota_row['Fungsional'] or fungsional,
                    'is_aktif': anggota_row['IsAktif'] or 'Y',
                    'unit_id': anggota_row['IDUnitKerja'] or unit_id,
                    'nourut': anggota_row['Nourut'],
                    'update_date': now,
                    'update_by': update_by,
                    'bulan': bulan,
                    'tahun': tahun,
                }
            )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Shift 2 Roster #{no_urut} berhasil '
                'dilengkapi dari Shift 1.'
            ),
            'data': {
                'bulan': bulan,
                'tahun': tahun,
                'unit_kerja_id': unit_id,
                'fungsional': fungsional,
                'no_urut': no_urut,
                'shift': '2',
                'jumlah_anggota': len(anggota),
            }
        })

    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            'Gagal melengkapi Shift 2 roster siaga'
        )

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

