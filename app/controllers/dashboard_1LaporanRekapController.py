# controllers/dashboard_1LaporanRekapController.py
from flask import render_template, request, send_file
from io import BytesIO
from sqlalchemy import func
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side, Font, PatternFill
from openpyxl.drawing.image import Image as XLImage
from app import db
from app.models.absensiModel import Absensi
from app.models.pegawaiModel import Pegawai
from app.models.kalenderModel import MfKalender
from app.models.dinasLuarModel import DinasLuar
from app.models.unitKerjaModel import MfUnitKerja
from app.models.timeRecorderModel import TimeRecorder
from app.models.tunjanganModel import MfTunjangan
from app.models.potModel import MfPot
from app.models.classModel import MfClass
from app.models.lemburModel import Lembur

def laporan_cetak_daftar_lembur_umum():
    """Render halaman Cetak Daftar Lembur Umum."""
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Laporan Cetak Daftar Lembur Umum.html',
        unit_kerja_list=unit_kerja_list
    )


def export_rekap_daftar_lembur_umum():
    """Export Rekap Daftar Lembur Umum (Tab 1) - matriks + perhitungan uang."""
    unit_list = request.form.getlist('unit_kerja[]')
    bulan_str = request.form.get('bulan', '')
    bendahara = request.form.get('bendahara', '')
    pppk = request.form.get('pppk', '')
    pembuat = request.form.get('pembuat', '')
    
    if not unit_list or not bulan_str:
        return {'error': 'Unit atau bulan kosong'}, 400
    
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    tahun, bulan = map(int, bulan_str.split('-'))
    tgl_awal = datetime(tahun, bulan, 1)
    if bulan == 12:
        tgl_akhir = datetime(tahun + 1, 1, 1) - timedelta(days=1)
    else:
        tgl_akhir = datetime(tahun, bulan + 1, 1) - timedelta(days=1)
    
    # Ambil data lembur join pegawai via NIP
    rows = (
        db.session.query(Lembur, Pegawai)
        .join(Pegawai, Lembur.FINGER_ID == Pegawai.FINGER_ID)
        .filter(Lembur.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .order_by(Pegawai.NAMA, Lembur.TGL_KERJA)
        .all()
    )
    
    if not rows:
        return {'error': 'Data tidak ada'}, 400
    
    # Ambil pegawai distinct
    pegawai_list = list(set(p for _, p in rows))
    pegawai_list.sort(key=lambda x: x.NAMA)
    
    # Ambil kalender
    kalender_rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .order_by(MfKalender.TGL_KERJA.asc())
        .all()
    )
    
    # Ambil tunjangan
    tunjangan_list = (
        MfTunjangan.query
        .filter(MfTunjangan.ACTIVITY == 'Piket siaga')
        .filter(MfTunjangan.JENIS_TUNJANGAN.in_(['U.Makan', 'U.Lembur']))
        .filter(MfTunjangan.TGL_MULAI <= tgl_akhir.date())
        .all()
    )
    
    n_tgl = (tgl_akhir - tgl_awal).days + 1
    
    # Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Daftar Lembur"
    ws.sheet_properties.tabColor = "FF7B00"
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    
    coltgl = 5 + n_tgl - 1
    col_total = coltgl + 9
    
    # Logo
    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except:
        pass
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    
    # Judul
    ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=col_total)
    ws.cell(row=2, column=4, value='DAFTAR LEMBUR UMUM').font = Font(bold=True, size=14)
    ws.cell(row=2, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=3, start_column=4, end_row=3, end_column=col_total)
    ws.cell(row=3, column=4, value=f"Periode {tgl_awal:%d.%m.%Y} s/d {tgl_akhir:%d.%m.%Y}")
    ws.cell(row=3, column=4).alignment = Alignment(horizontal='center')
    
    # Header
    ws.merge_cells('B5:B7')
    ws.cell(row=5, column=2, value='No').border = border
    ws.cell(row=5, column=2).alignment = Alignment(horizontal='center', vertical='center')
    
    ws.merge_cells('C5:C7')
    ws.cell(row=5, column=3, value='Nama').border = border
    ws.cell(row=5, column=3).alignment = Alignment(horizontal='center', vertical='center')
    
    ws.merge_cells('D5:D7')
    ws.cell(row=5, column=4, value='Gol').border = border
    ws.cell(row=5, column=4).alignment = Alignment(horizontal='center', vertical='center')
    
    # Header: Jumlah Jam Kegiatan Lembur Pada Tanggal
    ws.merge_cells(start_row=5, start_column=5, end_row=5, end_column=coltgl)
    ws.cell(row=5, column=5, value='Jumlah Jam Kegiatan Lembur Pada Tanggal').border = border
    ws.cell(row=5, column=5).alignment = Alignment(horizontal='center')
    
    # Isi tanggal
    for i, d in enumerate(range(n_tgl)):
        col = 5 + i
        hari = (tgl_awal + timedelta(days=d))
        cell = ws.cell(row=6, column=col, value=hari.day)
        cell.border = border
        cell.alignment = Alignment(horizontal='center')
        if hari.weekday() >= 5:
            cell.font = Font(color='FF0000')
    
    # Header: Jumlah Jam, Makan, Uang
    for col, val in {
        coltgl+1: 'Jumlah Jam\nHari Kerja', coltgl+2: 'Jumlah Jam\nHari Libur',
        coltgl+3: 'Jumlah\nMakan Libur', coltgl+4: 'Lembur', coltgl+5: 'Makan Libur',
        coltgl+6: 'Jumlah Dari\nKolom', coltgl+7: 'Potongan\nPPH', coltgl+8: 'Jumlah\nBersih', coltgl+9: 'Tanda\nTangan'
    }.items():
        ws.merge_cells(start_row=5, start_column=col, end_row=7, end_column=col)
        ws.cell(row=5, column=col, value=val).border = border
        ws.cell(row=5, column=col).font = Font(bold=True)
        ws.cell(row=5, column=col).alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Lebar kolom
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 5
    for i in range(5, coltgl + 1):
        col_letter = chr(64 + i) if i <= 26 else 'A'
        ws.column_dimensions[col_letter].width = 5
    for i in range(coltgl + 1, col_total + 1):
        col_letter = chr(64 + i) if i <= 26 else 'A'
        ws.column_dimensions[col_letter].width = 12
    
    # Isi data
    row = 8
    no = 1
    
    for peg in pegawai_list:
        lembur_peg = [(l, p) for l, p in rows if p.NIP == peg.NIP]
        
        # Merge 2 baris per pegawai
        for r in [row, row + 1]:
            for c in range(2, col_total + 1):
                ws.cell(row=r, column=c).border = border
        
        ws.cell(row=row, column=2, value=no)
        ws.cell(row=row, column=3, value=peg.NAMA)
        ws.cell(row=row + 1, column=3, value=peg.NIP)
        ws.cell(row=row, column=4, value=peg.GOL_ID)
        
        # Isi jam lembur per tanggal
        tot_hk = tot_hl = tot_makan = 0
        for i, d in enumerate(range(n_tgl)):
            tgl_iter = tgl_awal + timedelta(days=d)
            is_libur = tgl_iter.weekday() >= 5
            
            jam_lembur = 0
            for l, _ in lembur_peg:
                if l.TGL_KERJA and l.TGL_KERJA.date() == tgl_iter.date():
                    jam_in = l.JAM_BAKU_IN if l.JAM_BAKU_IN else l.JAM_IN
                    jam_out = l.JAM_BAKU_OUT if l.JAM_BAKU_OUT else l.JAM_OUT
                    
                    if jam_in and jam_out:
                        delta = (jam_out - jam_in).total_seconds() / 3600
                        if delta > 0:
                            jam_lembur = delta
                    break
            
            if jam_lembur > 0:
                col = 5 + i
                ws.cell(row=row, column=col, value=round(jam_lembur, 1))
            
            if is_libur:
                tot_hl += jam_lembur
            else:
                tot_hk += jam_lembur
            
            if jam_lembur > 0:
                tot_makan += 1
        
        ws.cell(row=row, column=coltgl + 1, value=round(tot_hk, 1))
        ws.cell(row=row, column=coltgl + 2, value=round(tot_hl, 1))
        ws.cell(row=row, column=coltgl + 3, value=tot_makan)
        
        # Hitung uang
        uang_lembur = 0
        uang_makan = 0
        for t in tunjangan_list:
            if t.JENIS_TUNJANGAN == 'U.Lembur':
                uang_lembur = t.NOMINAL or 0
            elif t.JENIS_TUNJANGAN == 'U.Makan':
                uang_makan = t.NOMINAL or 0
        
        total_lembur = (tot_hk + tot_hl) * uang_lembur
        total_makan = tot_makan * uang_makan
        total_bersih = total_lembur + total_makan
        
        ws.cell(row=row, column=coltgl + 4, value=total_lembur).number_format = '#,##0'
        ws.cell(row=row, column=coltgl + 5, value=total_makan).number_format = '#,##0'
        ws.cell(row=row, column=coltgl + 6, value=total_bersih).number_format = '#,##0'
        ws.cell(row=row, column=coltgl + 7, value=0).number_format = '#,##0'
        ws.cell(row=row, column=coltgl + 8, value=total_bersih).number_format = '#,##0'
        ws.cell(row=row, column=coltgl + 9, value=no)
        
        no += 1
        row += 2
    
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
        download_name=f"Daftar_Lembur_{tgl_awal:%Y%m}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def export_detail_jam_lembur_umum():
    """Export Detail Jam Lembur Umum (Tab 2) - jam in/out per hari."""
    unit_list = request.form.getlist('unit_kerja[]')
    bulan_str = request.form.get('bulan', '')
    
    if not unit_list or not bulan_str:
        return {'error': 'Unit atau bulan kosong'}, 400
    
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    tahun, bulan = map(int, bulan_str.split('-'))
    tgl_awal = datetime(tahun, bulan, 1)
    if bulan == 12:
        tgl_akhir = datetime(tahun + 1, 1, 1) - timedelta(days=1)
    else:
        tgl_akhir = datetime(tahun, bulan + 1, 1) - timedelta(days=1)
    
    rows = (
        db.session.query(Lembur, Pegawai)
        .join(Pegawai, Lembur.FINGER_ID == Pegawai.FINGER_ID)
        .filter(Lembur.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .order_by(Pegawai.NAMA, Lembur.TGL_KERJA)
        .all()
    )
    
    if not rows:
        return {'error': 'Data tidak ada'}, 400
    
    n_tgl = (tgl_akhir - tgl_awal).days + 1
    pegawai_list = sorted(set(p for _, p in rows), key=lambda x: x.NAMA)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Detail Lembur"
    ws.sheet_properties.tabColor = "FF7B00"
    ws.page_setup.orientation = 'landscape'
    
    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except:
        pass
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    col_total = 5 + n_tgl - 1
    
    ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=col_total)
    ws.cell(row=2, column=4, value='DAFTAR DETAIL LEMBUR UMUM').font = Font(bold=True, size=12)
    ws.cell(row=2, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=3, start_column=4, end_row=3, end_column=col_total)
    ws.cell(row=3, column=4, value=f"Periode {tgl_awal:%d.%m.%Y} s/d {tgl_akhir:%d.%m.%Y}")
    ws.cell(row=3, column=4).alignment = Alignment(horizontal='center')
    
    # Header
    for col, val in {2: 'No', 3: 'Nama', 4: 'Gol', 5: 'Jumlah Jam Kegiatan Lembur Pada Tanggal'}.items():
        if col == 5:
            ws.merge_cells(start_row=5, start_column=5, end_row=5, end_column=col_total)
        ws.cell(row=5, column=col, value=val).border = border
        ws.cell(row=5, column=col).font = Font(bold=True)
        ws.cell(row=5, column=col).alignment = Alignment(horizontal='center', vertical='center')
    
    for i, d in enumerate(range(n_tgl)):
        col = 5 + i
        ws.cell(row=6, column=col, value=(tgl_awal + timedelta(days=d)).day).border = border
        ws.cell(row=6, column=col).alignment = Alignment(horizontal='center')
    
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 5
    for i in range(5, col_total + 1):
        col_letter = chr(64 + i) if i <= 26 else 'A'
        ws.column_dimensions[col_letter].width = 8
    
    row = 7
    no = 1
    for peg in pegawai_list:
        for c in range(2, col_total + 1):
            ws.cell(row=row, column=c).border = border
        
        ws.cell(row=row, column=2, value=no)
        ws.cell(row=row, column=3, value=f"{peg.NAMA}\n{peg.NIP}")
        ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True)
        ws.cell(row=row, column=4, value=peg.GOL_ID)
        
        lembur_peg = [(l, p) for l, p in rows if p.NIP == peg.NIP]
        for i, d in enumerate(range(n_tgl)):
            tgl_iter = tgl_awal + timedelta(days=d)
            col = 5 + i
            
            for l, _ in lembur_peg:
                if l.TGL_KERJA and l.TGL_KERJA.date() == tgl_iter.date():
                    jam_in = l.JAM_IN.strftime('%H:%M') if l.JAM_IN else '-'
                    jam_out = l.JAM_OUT.strftime('%H:%M') if l.JAM_OUT else '-'
                    ws.cell(row=row, column=col, value=f"{jam_in}-{jam_out}")
                    break
        
        no += 1
        row += 1
    
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
        download_name=f"Detail_Lembur_{tgl_awal:%Y%m}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def laporan_rekap_absensi_all():
    """
    Render halaman Laporan Rekap Absensi All.
    Unit Kerja dropdown diisi dari tabel MF_UNIT_KERJA (server-side render),
    bukan hardcode di HTML.
    """
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()

    return render_template(
        'pages/dashboard_1/Laporan Rekap Absensi All.html',
        unit_kerja_list=unit_kerja_list
    )

def export_rekap_absensi_all():
    unit_list = request.form.getlist('unit_kerja[]')
    tgl_awal_str = request.form.get('tgl_awal')
    tgl_akhir_str = request.form.get('tgl_akhir')
    
    if not unit_list or not tgl_awal_str or not tgl_akhir_str:
        return {'error': 'Unit kosong atau format tanggal salah'}, 400
    
    # Konversi unit_list ke integer
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
    tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d')
    tampilkan_ket = request.form.get('kolom_keterangan') == 'tampilkan'
    nama_eselon3 = request.form.get('nama_eselon3', '')
    pangkat_eselon3 = request.form.get('pangkat_eselon3', '')
    petugas1 = request.form.get('petugas1', '')
    petugas2 = request.form.get('petugas2', '')

    # Cek tanggal server
    tgl_server = datetime.now()
    if tgl_server.date() < tgl_awal.date():
        return {'error': 'Tgl server lebih kecil dari tanggal awal periode'}, 400
    if tgl_server.date() < tgl_akhir.date():
        tgl_akhir = tgl_server

    # Query — JOIN VIA NIP, BUKAN FINGER_ID
    q = (
        db.session.query(Absensi, Pegawai)
        .join(Pegawai, Absensi.NIP == Pegawai.NIP)  # ✅ JOIN VIA NIP
        .join(MfKalender, Absensi.TGL_KERJA == MfKalender.TGL_KERJA)
        .filter(Absensi.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(MfKalender.IS_LIBUR == 'N')
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))  # ✅ pakai integer
    )
    rows = q.all()
    df_absensi = pd.DataFrame([{**a.__dict__, **p.__dict__} for a, p in rows]) if rows else pd.DataFrame()

    if df_absensi.empty:
        return {'error': 'Record tidak ada atau kalender belum dibuat'}, 400

    # Agregasi — ganti 'tingkat_tlm' jadi 'TINGKAT_TLM' (sesuai kolom model)
    hasil = []
    for nip, grp in df_absensi.groupby('NIP'):
        hasil.append({
            'nip': nip,
            'nama': grp['NAMA'].iloc[0],
            'tlm1': (grp['TINGKAT_TLM'] == 'TLM-1').sum(),
            'tlm2': (grp['TINGKAT_TLM'] == 'TLM-2').sum(),
            'tlm3': (grp['TINGKAT_TLM'] == 'TLM-3').sum(),
            'tlm4': (grp['TINGKAT_TLM'] == 'TLM-4').sum(),
            'psw1': (grp['TINGKAT_PSW'] == 'PSW-1').sum(),
            'psw2': (grp['TINGKAT_PSW'] == 'PSW-2').sum(),
            'psw3': (grp['TINGKAT_PSW'] == 'PSW-3').sum(),
            'psw4': (grp['TINGKAT_PSW'] == 'PSW-4').sum(),
            'dl': (grp['TRANSAKSI_IN'] == 'DinasLuar').sum(),
            'cuti': ((grp['TRANSAKSI_IN'] == 'Cuti') & (grp['TINGKAT_TLM'] == 'CT')).sum(),
            'cb1': ((grp['TRANSAKSI_IN'] == 'Cuti') & (grp['TINGKAT_TLM'] == 'CB-1')).sum(),
            'cb2': ((grp['TRANSAKSI_IN'] == 'Cuti') & (grp['TINGKAT_TLM'] == 'CB-2')).sum(),
            'cb3': ((grp['TRANSAKSI_IN'] == 'Cuti') & (grp['TINGKAT_TLM'] == 'CB-3')).sum(),
            'capm2': ((grp['TRANSAKSI_IN'] == 'Cuti') & (grp['TINGKAT_TLM'] == 'CAP-M2')).sum(),
            'cap': ((grp['TRANSAKSI_IN'] == 'Cuti') & (grp['TINGKAT_TLM'] == 'CAP')).sum(),
            'sakit': ((grp['TRANSAKSI_IN'] == 'Sakit') & (grp['TINGKAT_TLM'] == 'S-1')).sum(),
            'sakit2': ((grp['TRANSAKSI_IN'] == 'Sakit') & (grp['TINGKAT_TLM'] == 'S-2')).sum(),
            'sakit3': ((grp['TRANSAKSI_IN'] == 'Sakit') & (grp['TINGKAT_TLM'] == 'S-3')).sum(),
            'sakit4': ((grp['TRANSAKSI_IN'] == 'Sakit') & (grp['TINGKAT_TLM'] == 'S-4')).sum(),
            'sakit5': ((grp['TRANSAKSI_IN'] == 'Sakit') & (grp['TINGKAT_TLM'] == 'S-5')).sum(),
            'alpa': ((grp['TRANSAKSI_IN'] == 'Alpa') & (grp['PENDUKUNG_IN'] == 'Y')).sum(),
            'alpa_tanpa_ket': ((grp['TRANSAKSI_IN'] == 'Alpa') & (grp['PENDUKUNG_IN'] == 'N')).sum(),
        })
    df_hasil = pd.DataFrame(hasil)

    # 4. (Opsional) keterangan dinas luar/cuti kalau tampilkan_ket True
    if tampilkan_ket:
        dl_rows = (
            DinasLuar.query
            .filter(DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_akhir)
            .filter(DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_awal)
            .all()
        )
        # susun jadi dict {nip: "1. ... \n2. ..."} sesuai format lama

    # 5. Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Daftar"
    ws.sheet_properties.tabColor = "FF7B00"

    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except FileNotFoundError:
        pass

    ws.merge_cells('D2:AL2')
    ws['D2'] = 'Laporan Rekap Daftar Hadir Pegawai'
    ws['D2'].font = Font(bold=True)
    ws['D2'].alignment = Alignment(horizontal='center')

    ws.merge_cells('D3:AL3')
    ws['D3'] = f"Periode {tgl_awal:%d.%m.%Y} s/d {tgl_akhir:%d.%m.%Y}"
    ws['D3'].alignment = Alignment(horizontal='center')

    ws.merge_cells('D4:AL4')
    ws['D4'] = f"Unit : {', '.join(unit_list)}"
    ws['D4'].alignment = Alignment(horizontal='center')

    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)

    header_row = 5
    headers = ['No', 'Nama', 'TLM1', 'TLM2', 'TLM3', 'TLM4', 'Cuti', 'Sakit', 'Alpa']  # lengkapi sesuai kebutuhan
    for col, h in enumerate(headers, start=2):
        c = ws.cell(row=header_row, column=col, value=h)
        c.border = border
        c.alignment = Alignment(horizontal='center', vertical='center')

    row = header_row + 1
    for i, r in enumerate(df_hasil.to_dict('records'), start=1):
        ws.cell(row=row, column=2, value=i).border = border
        ws.cell(row=row, column=3, value=f"{r['nip']}\n{r['nama']}").border = border
        ws.cell(row=row, column=4, value=r['tlm1'] or None).border = border
        ws.cell(row=row, column=5, value=r['tlm2'] or None).border = border
        ws.cell(row=row, column=6, value=r['tlm3'] or None).border = border
        ws.cell(row=row, column=7, value=r['tlm4'] or None).border = border
        ws.cell(row=row, column=8, value=r['cuti'] or None).border = border
        ws.cell(row=row, column=9, value=r['sakit'] or None).border = border
        ws.cell(row=row, column=10, value=r['alpa'] or None).border = border
        row += 1

    row += 2
    ws.cell(row=row, column=4, value='Mengetahui,')
    ws.cell(row=row+1, column=4, value='Pejabat Eselon III')
    ws.cell(row=row+4, column=4, value=nama_eselon3).font = Font(underline='single')
    ws.cell(row=row+5, column=4, value=pangkat_eselon3)

    ws.cell(row=row, column=32, value=f"Surabaya, {tgl_akhir:%d %B %Y}")
    ws.cell(row=row+1, column=32, value='Petugas Pengelola Daftar Hadir')
    ws.cell(row=row+3, column=32, value=f"1. {petugas1}")
    ws.cell(row=row+5, column=32, value=f"2. {petugas2}")

    # 6. Stream sebagai download, bukan simpan ke disk
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"Laporan_Rekap_Daftar_Hadir_Peg_{tgl_awal:%Y%m%d}_{tgl_akhir:%Y%m%d}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


def laporan_rekap_absensi_individu():
    """
    Render halaman Laporan Rekap Absensi Individu.
    """
    return render_template('pages/dashboard_1/Laporan Rekap Absensi Individu.html')

def export_rekap_absensi_individu():
    """
    Export Laporan Rekap Absensi Individu (per pegawai, detail per hari).
    Mirip dengan FillRekapAbsensiPerson di VB.NET.
    """
    nip_list = request.form.getlist('nip[]')  # ['198501232009122002', ...]
    tgl_awal_str = request.form.get('tgl_awal')
    tgl_akhir_str = request.form.get('tgl_akhir')
    
    if not nip_list or not tgl_awal_str or not tgl_akhir_str:
        return {'error': 'NIP atau tanggal kosong'}, 400
    
    tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
    tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d')
    
    # Cek tanggal server
    tgl_server = datetime.now()
    if tgl_server.date() < tgl_awal.date():
        return {'error': 'Tgl server lebih kecil dari tanggal awal periode'}, 400
    if tgl_server.date() < tgl_akhir.date():
        tgl_akhir = tgl_server
    
    # 1. Ambil data kalender (hari kerja saja)
    kalender_rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(MfKalender.IS_LIBUR == 'N')
        .order_by(MfKalender.TGL_KERJA.asc())
        .all()
    )
    
    if not kalender_rows:
        return {'error': 'Tidak ada hari kerja dalam periode tersebut'}, 400
    
    # 2. Ambil data absensi untuk NIP yang dipilih
    absensi_rows = (
        db.session.query(Absensi, Pegawai)
        .join(Pegawai, Absensi.NIP == Pegawai.NIP)
        .filter(Absensi.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(Absensi.NIP.in_(nip_list))
        .order_by(Pegawai.NAMA, Absensi.TGL_KERJA)
        .all()
    )
    
    # 3. Ambil data pegawai
    pegawai_rows = (
        Pegawai.query
        .filter(Pegawai.NIP.in_(nip_list))
        .order_by(Pegawai.NAMA)
        .all()
    )
    
    if not pegawai_rows:
        return {'error': 'Pegawai tidak ditemukan'}, 400
    
    # 4. Build data per pegawai per tanggal
    # Struktur: {nip: {nama: ..., unit_kerja: ..., rows: [{tgl, tlm, kategori_tlm, psw, kategori_psw, cuti, dl, sakit, sakit_a, alpa, alpa_a, ket}]}}
    absensi_dict = {}
    for a, p in absensi_rows:
        tgl_key = a.TGL_KERJA.strftime('%Y-%m-%d') if a.TGL_KERJA else None
        if a.NIP not in absensi_dict:
            absensi_dict[a.NIP] = {}
        absensi_dict[a.NIP][tgl_key] = a
    
    # 5. Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Daftar Individu"
    ws.sheet_properties.tabColor = "FF7B00"
    
    # Setup printer
    ws.sheet_properties.pageSetUpPr = None
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    
    # Header
    ws.merge_cells('D2:N2')
    ws['D2'] = 'Laporan Rekap Daftar Hadir Pegawai'
    ws['D2'].font = Font(bold=True, size=12)
    ws['D2'].alignment = Alignment(horizontal='center')
    
    ws.merge_cells('D3:N3')
    ws['D3'] = f"Periode {tgl_awal:%d.%m.%Y} s/d {tgl_akhir:%d.%m.%Y}"
    ws['D3'].alignment = Alignment(horizontal='center')
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    
    # Kolom header
    headers = ['No.', 'Tanggal', 'TLM\n(menit)', 'Kategori\nTLM', 'PSW\n(menit)', 
               'Kategori\nPSW', 'Cuti\n(hari)', 'Dinas\nLuar', 'Sakit\nDokter', 
               'Sakit\ntnp dr', 'Tdk Hadir\ndgn Izin', 'Tdk Hadir\nTanpa Ket', 'Keterangan']
    
    header_row = 5
    for col, h in enumerate(headers, start=2):
        c = ws.cell(row=header_row, column=col, value=h)
        c.border = border
        c.font = Font(bold=True, size=9)
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Set lebar kolom
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 11
    ws.column_dimensions['D'].width = 9
    ws.column_dimensions['E'].width = 9
    ws.column_dimensions['F'].width = 9
    ws.column_dimensions['G'].width = 9
    ws.column_dimensions['H'].width = 9
    ws.column_dimensions['I'].width = 9
    ws.column_dimensions['J'].width = 9
    ws.column_dimensions['K'].width = 9
    ws.column_dimensions['L'].width = 9
    ws.column_dimensions['M'].width = 9
    ws.column_dimensions['N'].width = 25
    
    row = header_row + 1
    
    for pegawai in pegawai_rows:
        # Baris nama pegawai (merge)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=14)
        ws.cell(row=row, column=2, value=pegawai.NAMA).font = Font(bold=True)
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='left')
        for col in range(2, 15):
            ws.cell(row=row, column=col).border = border
        row += 1
        
        # Detail per hari
        no = 0
        for kl in kalender_rows:
            no += 1
            tgl_str = kl.TGL_KERJA.strftime('%Y-%m-%d') if kl.TGL_KERJA else ''
            
            # Border
            for col in range(2, 15):
                ws.cell(row=row, column=col).border = border
            
            ws.cell(row=row, column=2, value=no).alignment = Alignment(horizontal='right', vertical='center')
            ws.cell(row=row, column=3, value=kl.TGL_KERJA.strftime('%d-%m-%Y') if kl.TGL_KERJA else '').alignment = Alignment(horizontal='left', vertical='center')
            
            # Cek absensi untuk tanggal ini
            absensi = absensi_dict.get(pegawai.NIP, {}).get(tgl_str)
            
            if absensi:
                ws.cell(row=row, column=4, value=absensi.AWAL_TLM or 0).alignment = Alignment(horizontal='right', vertical='center')
                ws.cell(row=row, column=5, value=absensi.TINGKAT_TLM or '').alignment = Alignment(horizontal='center', vertical='center')
                ws.cell(row=row, column=6, value=absensi.TOTAL_PSW or 0).alignment = Alignment(horizontal='right', vertical='center')
                ws.cell(row=row, column=7, value=absensi.TINGKAT_PSW or '').alignment = Alignment(horizontal='center', vertical='center')
                ws.cell(row=row, column=14, value=absensi.KET_IN or '').alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
                
                # Kategori transaksi
                transaksi = (absensi.TRANSAKSI_IN or '').upper()
                pendukung = (absensi.PENDUKUNG_IN or '').upper()
                
                if transaksi == 'CUTI':
                    ws.cell(row=row, column=8, value=1)
                elif transaksi == 'DINASLUAR':
                    ws.cell(row=row, column=9, value=1)
                elif transaksi == 'SAKIT':
                    if pendukung == 'Y':
                        ws.cell(row=row, column=10, value=1)
                    else:
                        ws.cell(row=row, column=11, value=1)
                elif transaksi == 'ALPA':
                    if pendukung == 'Y':
                        ws.cell(row=row, column=12, value=1)
                    else:
                        ws.cell(row=row, column=13, value=1)
                elif transaksi == 'IJIN':
                    if pendukung == 'Y':
                        ws.cell(row=row, column=12, value=1)
                    else:
                        ws.cell(row=row, column=13, value=1)
            else:
                # Tidak ada record = Alpa tanpa keterangan
                ws.cell(row=row, column=13, value=1)
            
            # Alignment untuk kolom angka
            for col in [8, 9, 10, 11, 12, 13]:
                ws.cell(row=row, column=col).alignment = Alignment(horizontal='right', vertical='center')
            
            row += 1
        
        row += 1  # Spasi antar pegawai
    
    # Keterangan di bawah
    row += 1
    ws.cell(row=row, column=2, value='Keterangan:').font = Font(bold=True)
    row += 1
    ws.cell(row=row, column=2, value='TLM')
    ws.cell(row=row, column=4, value=': Terlambat Masuk')
    row += 1
    ws.cell(row=row, column=2, value='PSW')
    ws.cell(row=row, column=4, value=': Pulang Sebelum Waktu')
    row += 1
    ws.cell(row=row, column=2, value='TLM (-)')
    ws.cell(row=row, column=4, value=': Datang Lebih Awal')
    
    # Stream download
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"Laporan_Rekap_Daftar_Hadir_Per_Pegawai_{tgl_awal:%Y%m%d}_{tgl_akhir:%Y%m%d}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def search_pegawai_by_name():
    """
    API untuk search pegawai berdasarkan nama (untuk dropdown autocomplete).
    """
    keyword = request.args.get('keyword', '').strip()
    if len(keyword) < 2:
        return {'data': []}
    
    pegawai_list = (
        Pegawai.query
        .filter(Pegawai.NAMA.ilike(f'%{keyword}%'))
        .order_by(Pegawai.NAMA.asc())
        .limit(15)
        .all()
    )
    
    return {
        'data': [
            {
                'nip': p.NIP,
                'nama': p.NAMA,
                'jabatan': p.JABATAN,
            }
            for p in pegawai_list
        ]
    }

def laporan_rekap_absensi_log_finger():
    """
    Render halaman Laporan Rekap Absensi Log Finger.
    Unit Kerja dropdown diisi dari tabel MF_UNIT_KERJA.
    """
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()

    return render_template(
        'pages/dashboard_1/Laporan Rekap Absensi Log Finger.html',
        unit_kerja_list=unit_kerja_list
    )

def laporan_rekap_absensi_log_finger():
    """
    Render halaman Laporan Rekap Absensi Log Finger.
    Unit Kerja dropdown diisi dari tabel MF_UNIT_KERJA.
    """
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()

    return render_template(
        'pages/dashboard_1/Laporan Rekap Absensi Log Finger.html',
        unit_kerja_list=unit_kerja_list
    )

def export_rekap_absensi_log_finger():
    """Export Laporan Log Finger via TIME_RECORDER -> ABSENSI -> PEGAWAI"""
    unit_list = request.form.getlist('unit_kerja[]')
    tgl_awal_str = request.form.get('tgl_awal')
    tgl_akhir_str = request.form.get('tgl_akhir')
    
    if not unit_list or not tgl_awal_str or not tgl_akhir_str:
        return {'error': 'Unit kosong atau format tanggal salah'}, 400
    
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
    tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d') + timedelta(days=1)
    
    # Subquery: ambil 1 NIP per FINGER_ID dari ABSENSI (hindari duplikat)
    subquery = (
        db.session.query(
            Absensi.FINGER_ID,
            func.min(Absensi.NIP).label('NIP')
        )
        .filter(Absensi.NIP.isnot(None))
        .group_by(Absensi.FINGER_ID)
        .subquery()
    )
    
    # Query utama: TIME_RECORDER -> subquery -> PEGAWAI -> MF_UNIT_KERJA
    rows = (
        db.session.query(TimeRecorder, Pegawai, MfUnitKerja)
        .join(subquery, TimeRecorder.FINGER_ID == subquery.c.FINGER_ID)
        .join(Pegawai, subquery.c.NIP == Pegawai.NIP)
        .join(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
        .filter(TimeRecorder.WAKTU.between(tgl_awal, tgl_akhir))
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .order_by(Pegawai.NAMA, TimeRecorder.WAKTU)
        .all()
    )
    
    if not rows:
        return {'error': 'Record tidak ada'}, 400
    
    # Ambil nama unit untuk judul
    unit_names_list = MfUnitKerja.query.filter(MfUnitKerja.UNIT_KERJA_ID.in_(unit_ids)).all()
    unit_names = ', '.join([u.NAMA_UNIT_KERJA for u in unit_names_list])
    
    # Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Log Finger"
    ws.sheet_properties.tabColor = "FF7B00"
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    
    # Logo
    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except:
        pass
    
    # Judul
    ws.merge_cells('D2:F2')
    ws['D2'] = 'Rekap Log Finger'
    ws['D2'].font = Font(bold=True, size=12)
    ws['D2'].alignment = Alignment(horizontal='center')
    
    ws.merge_cells('D3:F3')
    ws['D3'] = f"Periode {tgl_awal:%d.%m.%Y} s/d {(tgl_akhir - timedelta(days=1)):%d.%m.%Y}"
    ws['D3'].alignment = Alignment(horizontal='center')
    
    ws.merge_cells('D4:F4')
    ws['D4'] = f"Unit : {unit_names}"
    ws['D4'].alignment = Alignment(horizontal='center')
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    
    # Header kolom
    headers = ['No.', 'Tanggal', 'Jam', 'Status', 'Device']
    for col, h in enumerate(headers, start=2):
        c = ws.cell(row=5, column=col, value=h)
        c.border = border
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal='center', vertical='center')
    
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 13
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 8
    ws.column_dimensions['F'].width = 30
    
    row = 6
    prev_name = ''
    no = 0
    
    for tr, pg, uk in rows:
        current_name = f"{tr.FINGER_ID} - {pg.NAMA}"
        
        if current_name != prev_name:
            # Baris nama pegawai
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
            ws.cell(row=row, column=2, value=current_name)
            ws.cell(row=row, column=2).font = Font(bold=True, italic=True)
            for col in range(2, 7):
                ws.cell(row=row, column=col).border = border
            row += 1
            prev_name = current_name
            no = 0
        
        no += 1
        for col in range(2, 7):
            ws.cell(row=row, column=col).border = border
        
        ws.cell(row=row, column=2, value=no)
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=tr.WAKTU.strftime('%d %b %Y') if tr.WAKTU else '')
        ws.cell(row=row, column=3).alignment = Alignment(horizontal='left')
        ws.cell(row=row, column=4, value=tr.WAKTU.strftime('%H:%M:%S') if tr.WAKTU else '')
        ws.cell(row=row, column=4).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=5, value=tr.STATUS or '')
        ws.cell(row=row, column=5).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=6, value=f"{tr.MESIN or '-'} @ {uk.NAMA_UNIT_KERJA or '-'}")
        ws.cell(row=row, column=6).alignment = Alignment(horizontal='left')
        
        row += 1
    
    # Stream download
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"Rekap_Log_Finger_{tgl_awal:%Y%m%d}_{(tgl_akhir - timedelta(days=1)):%Y%m%d}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


def laporan_rekap_clock_exception():
    """Render halaman Laporan Rekap Clock Exception."""
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Laporan Rekap Clock Exception.html',
        unit_kerja_list=unit_kerja_list
    )

def export_rekap_clock_exception():
    """Export Rekap Exception Clock (matriks pegawai x tanggal)."""
    unit_list = request.form.getlist('unit_kerja[]')
    tgl_awal_str = request.form.get('tgl_awal')
    tgl_akhir_str = request.form.get('tgl_akhir')
    
    if not unit_list or not tgl_awal_str or not tgl_akhir_str:
        return {'error': 'Unit kosong atau format tanggal salah'}, 400
    
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
    tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d')
    
    # 1. Ambil kalender (semua, termasuk libur)
    kalender_rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .order_by(MfKalender.TGL_KERJA.asc())
        .all()
    )
    
    if not kalender_rows:
        # Fallback: generate dari rentang tanggal
        kalender_rows = []
        d = tgl_awal
        while d <= tgl_akhir:
            kalender_rows.append(type('obj', (object,), {
                'TGL_KERJA': datetime.combine(d, datetime.min.time()),
                'IS_LIBUR': 'N',
                'KET': None
            })())
            d += timedelta(days=1)
    
    n_tgl = len(kalender_rows)
    
    # 2. Ambil data absensi
    absensi_rows = (
        db.session.query(Absensi, Pegawai, MfUnitKerja)
        .join(Pegawai, Absensi.NIP == Pegawai.NIP)
        .join(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
        .filter(Absensi.TGL_KERJA.between(tgl_awal, tgl_akhir + timedelta(days=1)))
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .all()
    )
    
    # 3. Ambil data pegawai distinct
    pegawai_list = (
        Pegawai.query
        .join(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(
            db.or_(
                db.and_(Pegawai.TGL_MASUK <= tgl_akhir, Pegawai.IS_KELUAR == 0),
                db.and_(Pegawai.IS_KELUAR == 1, Pegawai.TGL_KELUAR >= tgl_awal)
            )
        )
        .order_by(Pegawai.NAMA)
        .all()
    )
    
    if not pegawai_list:
        return {'error': 'Pegawai tidak ditemukan'}, 400
    
    # 4. Build dict absensi: {nip: {tgl_str: absensi_obj}}
    absensi_dict = {}
    for a, p, uk in absensi_rows:
        tgl_key = a.TGL_KERJA.strftime('%Y-%m-%d') if a.TGL_KERJA else None
        if p.NIP not in absensi_dict:
            absensi_dict[p.NIP] = {}
        absensi_dict[p.NIP][tgl_key] = a
    
    # 5. Nama unit
    unit_names = ', '.join([u.NAMA_UNIT_KERJA for u in MfUnitKerja.query.filter(MfUnitKerja.UNIT_KERJA_ID.in_(unit_ids)).all()])
    
    # 6. Build Excel
    from openpyxl.styles import PatternFill, Font as OpFont
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Exception Clock"
    ws.sheet_properties.tabColor = "FF7B00"
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    
    col_paraf = 4 + n_tgl  # Kolom terakhir
    
    # Logo
    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except:
        pass
    
    # Judul
    ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=col_paraf)
    ws.cell(row=2, column=4, value='Rekap Exception Clock').font = Font(bold=True, size=12)
    ws.cell(row=2, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=3, start_column=4, end_row=3, end_column=col_paraf)
    ws.cell(row=3, column=4, value=f"Periode {tgl_awal:%d.%m.%Y} s/d {tgl_akhir:%d.%m.%Y}")
    ws.cell(row=3, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=4, start_column=4, end_row=4, end_column=col_paraf)
    ws.cell(row=4, column=4, value=f"Unit : {unit_names}").font = Font(bold=True)
    ws.cell(row=4, column=4).alignment = Alignment(horizontal='center')
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    
    # Header: No, Nama
    ws.merge_cells(start_row=5, start_column=2, end_row=6, end_column=2)
    ws.cell(row=5, column=2, value='No').border = border
    ws.cell(row=5, column=2).alignment = Alignment(horizontal='center', vertical='center')
    
    ws.merge_cells(start_row=5, start_column=3, end_row=6, end_column=3)
    ws.cell(row=5, column=3, value='Nama').border = border
    ws.cell(row=5, column=3).alignment = Alignment(horizontal='center', vertical='center')
    
    # Header: Tanggal (merge row 5)
    ws.merge_cells(start_row=5, start_column=4, end_row=5, end_column=col_paraf)
    ws.cell(row=5, column=4, value='Tanggal').border = border
    ws.cell(row=5, column=4).alignment = Alignment(horizontal='center')
    
    # Isi tanggal per kolom
    red_font = Font(color='FF0000')
    for i, kl in enumerate(kalender_rows):
        col = 4 + i
        tgl_val = kl.TGL_KERJA
        hari = tgl_val.strftime('%a').lower() if hasattr(kl, 'TGL_KERJA') else ''
        is_libur = kl.IS_LIBUR == 'Y' if hasattr(kl, 'IS_LIBUR') else (tgl_val.weekday() >= 5)
        
        cell = ws.cell(row=6, column=col, value=f"{tgl_val.day}\n{hari}")
        cell.border = border
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        if is_libur:
            cell.font = Font(color='FF0000')
    
    # Lebar kolom
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 30
    for i in range(4, col_paraf + 1):
        ws.column_dimensions[chr(64 + i) if i <= 26 else 'A'].width = 6
    
    # Isi data
    row = 7
    no = 0
    fill_red = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')
    fill_green = PatternFill(start_color='00FF00', end_color='00FF00', fill_type='solid')
    fill_blue = PatternFill(start_color='0000FF', end_color='0000FF', fill_type='solid')
    fill_orange = PatternFill(start_color='FFA500', end_color='FFA500', fill_type='solid')
    
    for peg in pegawai_list:
        for c in range(2, col_paraf + 1):
            ws.cell(row=row, column=c).border = border
        
        ws.cell(row=row, column=2, value=no + 1).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=peg.NAMA)
        
        for i, kl in enumerate(kalender_rows):
            col = 4 + i
            tgl_str = kl.TGL_KERJA.strftime('%Y-%m-%d') if hasattr(kl, 'TGL_KERJA') else ''
            is_libur = kl.IS_LIBUR == 'Y' if hasattr(kl, 'IS_LIBUR') else (kl.TGL_KERJA.weekday() >= 5)
            
            absensi = absensi_dict.get(peg.NIP, {}).get(tgl_str)
            cell = ws.cell(row=row, column=col)
            
            if absensi:
                transaksi = (absensi.TRANSAKSI_IN or '').upper()
                jam_in = absensi.TGL_JAM_IN.strftime('%H:%M') if absensi.TGL_JAM_IN else ''
                jam_out = absensi.TGL_JAM_OUT.strftime('%H:%M') if absensi.TGL_JAM_OUT else ''
                
                if transaksi == 'WFH':
                    cell.value = 'WFH'
                elif transaksi == 'DINASLUAR':
                    cell.value = f"{jam_in}\n{jam_out}"
                    if absensi.STATUS_UM in [1, 2]:
                        cell.font = Font(color='FFA500')  # Orange
                    else:
                        cell.font = Font(color='0000FF')  # Blue
                elif transaksi == 'CUTI':
                    cell.value = '- CT -'
                    cell.font = Font(color='FFA500')
                elif transaksi == 'SAKIT':
                    cell.value = '- S -'
                    cell.font = Font(color='FFA500')
                elif transaksi == 'ALPA':
                    cell.value = 'i'
                    cell.font = Font(color='FFA500')
                else:
                    if absensi.IS_INVALID == 'Y':
                        cell.value = f"{jam_in}\n{jam_out}"
            else:
                cell.value = ''
            
            if is_libur:
                cell.font = Font(color='FF0000')
        
        no += 1
        row += 1
    
    # Legend
    row += 2
    ws.cell(row=row, column=2).fill = fill_red
    ws.cell(row=row, column=3, value='HARI LIBUR')
    row += 1
    ws.cell(row=row, column=2).fill = fill_green
    ws.cell(row=row, column=3, value='SIAGA')
    row += 1
    ws.cell(row=row, column=2).fill = fill_blue
    ws.cell(row=row, column=3, value='DL TIDAK TERPOTONG UANG MAKAN')
    row += 1
    ws.cell(row=row, column=2).fill = fill_orange
    ws.cell(row=row, column=3, value='TERPOTONG UANG MAKAN')
    
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf, as_attachment=True,
        download_name=f"Rekap_Exception_Clock_{tgl_awal:%Y%m%d}_{tgl_akhir:%Y%m%d}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


def laporan_rekap_ketidakhadiran_pegawai():
    """Render halaman Laporan Rekap Ketidakhadiran Pegawai."""
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Laporan Rekap Ketidakhadiran Pegawai.html',
        unit_kerja_list=unit_kerja_list
    )

def export_rekap_ketidakhadiran_pegawai():
    """Export Rekap Sprin (DL, Sakit, Ijin, Cuti)."""
    unit_list = request.form.getlist('unit_kerja[]')
    jenis_list = request.form.getlist('jenis[]')
    tgl_awal_str = request.form.get('tgl_awal')
    tgl_akhir_str = request.form.get('tgl_akhir')
    
    if not unit_list or not tgl_awal_str or not tgl_akhir_str:
        return {'error': 'Unit kosong atau format tanggal salah'}, 400
    
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
    tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d')
    
    # Query DinasLuar join Pegawai via NIP
    query = (
        db.session.query(DinasLuar, Pegawai, MfUnitKerja)
        .join(Pegawai, DinasLuar.NIP == Pegawai.NIP)
        .join(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
        .filter(DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_akhir)
        .filter(DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_awal)
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
    )
    
    if jenis_list:
        query = query.filter(DinasLuar.TRANSAKSI.in_(jenis_list))
    
    rows = query.order_by(DinasLuar.TGL_AWAL_DINAS_LUAR, DinasLuar.TRANSAKSI, Pegawai.NAMA).all()
    
    if not rows:
        return {'error': 'Data tidak ada'}, 400
    
    unit_names = ', '.join([u.NAMA_UNIT_KERJA for u in MfUnitKerja.query.filter(MfUnitKerja.UNIT_KERJA_ID.in_(unit_ids)).all()])
    jenis_names = ', '.join(jenis_list) if jenis_list else 'Semua'
    
    # Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Sprin"
    ws.sheet_properties.tabColor = "FF7B00"
    
    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except:
        pass
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    
    # Judul
    ws.merge_cells('D2:F2')
    ws.cell(row=2, column=4, value=f"Rekap {jenis_names}").font = Font(bold=True, size=12)
    ws.cell(row=2, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells('D3:F3')
    ws.cell(row=3, column=4, value=f"Periode {tgl_awal:%d.%m.%Y} s/d {tgl_akhir:%d.%m.%Y}")
    ws.cell(row=3, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells('D4:F4')
    ws.cell(row=4, column=4, value=f"Unit : {unit_names}").font = Font(bold=True)
    ws.cell(row=4, column=4).alignment = Alignment(horizontal='center')
    
    # Header
    for col, val in {2: 'No', 3: 'Nama', 4: 'Tanggal', 5: 'Penempatan', 6: 'Keterangan'}.items():
        c = ws.cell(row=5, column=col, value=val)
        c.border = border; c.font = Font(bold=True)
        c.alignment = Alignment(horizontal='center', vertical='center')
    
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 22
    ws.column_dimensions['F'].width = 26
    
    # Isi data
    for i, (dl, peg, uk) in enumerate(rows, 1):
        for c in range(2, 7):
            ws.cell(row=5+i, column=c).border = border
        
        transaksi = dl.TRANSAKSI or ''
        if transaksi.upper() == 'ALPA':
            transaksi = 'Ijin'
        
        tgl_a = dl.TGL_AWAL_DINAS_LUAR.strftime('%d.%b.%Y') if dl.TGL_AWAL_DINAS_LUAR else ''
        tgl_b = dl.TGL_AKHIR_DINAS_LUAR.strftime('%d.%b.%Y') if dl.TGL_AKHIR_DINAS_LUAR else ''
        
        ws.cell(row=5+i, column=2, value=i).alignment = Alignment(horizontal='center', vertical='top')
        ws.cell(row=5+i, column=3, value=f"{peg.NIP}\n{peg.NAMA}").alignment = Alignment(vertical='top', wrap_text=True)
        ws.cell(row=5+i, column=4, value=f"{tgl_a}\n{tgl_b}").alignment = Alignment(vertical='top', wrap_text=True)
        ws.cell(row=5+i, column=5, value=dl.PENEMPATAN_DINAS_LUAR or '').alignment = Alignment(vertical='top', wrap_text=True)
        ws.cell(row=5+i, column=6, value=f"({transaksi}) {dl.KETERANGAN_DINAS_LUAR or ''}").alignment = Alignment(vertical='top', wrap_text=True)
    
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
        download_name=f"Rekap_Ketidakhadiran_{tgl_awal:%Y%m%d}_{tgl_akhir:%Y%m%d}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def laporan_rekap_pelanggaran_disiplin():
    """Render halaman Laporan Rekap Pelanggaran Disiplin."""
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Laporan Rekap Pelanggaran Disiplin.html',
        unit_kerja_list=unit_kerja_list
    )

def export_rekap_pelanggaran_disiplin():
    """Export Ranking Pelanggaran Disiplin Absensi."""
    unit_list = request.form.getlist('unit_kerja[]')
    tgl_awal_str = request.form.get('tgl_awal')
    tgl_akhir_str = request.form.get('tgl_akhir')
    
    if not unit_list or not tgl_awal_str or not tgl_akhir_str:
        return {'error': 'Unit kosong atau format tanggal salah'}, 400
    
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
    tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d')
    
    tgl_server = datetime.now()
    if tgl_server.date() < tgl_awal.date():
        return {'error': 'Tgl server lebih kecil dari tanggal awal periode'}, 400
    if tgl_server.date() < tgl_akhir.date():
        tgl_akhir = tgl_server
    
    # Kalender hari kerja
    kalender_rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(MfKalender.IS_LIBUR == 'N')
        .all()
    )
    default_tgl_kerja = len(kalender_rows)
    
    # Ambil data absensi (join via NIP)
    absensi_rows = (
        db.session.query(Absensi, Pegawai)
        .join(Pegawai, Absensi.NIP == Pegawai.NIP)
        .join(MfKalender, Absensi.TGL_KERJA == MfKalender.TGL_KERJA)
        .filter(Absensi.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(MfKalender.IS_LIBUR == 'N')
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(Pegawai.IS_VIP == 0)  # Exclude VIP
        .all()
    )
    
    if not absensi_rows:
        return {'error': 'Record tidak ada atau kalender belum dibuat'}, 400
    
    # Ambil data pegawai
    pegawai_list = (
        Pegawai.query
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(Pegawai.IS_VIP == 0)
        .filter(Pegawai.TGL_MASUK <= tgl_akhir)
        .filter(
            db.or_(
                Pegawai.IS_KELUAR == 0,
                db.and_(Pegawai.IS_KELUAR == 1, Pegawai.TGL_KELUAR >= tgl_awal)
            )
        )
        .order_by(Pegawai.NAMA)
        .all()
    )
    
    # Build dict absensi per NIP
    from collections import defaultdict
    absensi_dict = defaultdict(list)
    for a, p in absensi_rows:
        absensi_dict[p.NIP].append(a)
    
    # Hitung pelanggaran per pegawai
    hasil = []
    for peg in pegawai_list:
        abs_list = absensi_dict.get(peg.NIP, [])
        
        # TLM tanpa keterangan
        tot_tlm_a = sum(a.AWAL_TLM or 0 for a in abs_list 
                       if a.TINGKAT_TLM in ('TLM-1','TLM-2','TLM-3','TLM-4') 
                       and a.PENDUKUNG_IN == 'N' 
                       and a.TRANSAKSI_IN in ('LogFP','Manual','-','IN NonFP'))
        
        # PSW tanpa keterangan
        tot_psw_a = sum(a.TOTAL_PSW or 0 for a in abs_list 
                       if a.TINGKAT_PSW in ('PSW-1','PSW-2','PSW-3','PSW-4') 
                       and a.PENDUKUNG_OUT == 'N' 
                       and a.TRANSAKSI_OUT in ('LogFP','Manual','-','OUT NonFP'))
        
        # Sakit tanpa keterangan
        sakit_a = sum(1 for a in abs_list 
                     if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'SAKIT' 
                     and a.PENDUKUNG_IN == 'N')
        
        # Alpa tanpa keterangan + tidak masuk tanpa ket
        tgl_masuk = peg.TGL_MASUK
        if tgl_masuk and tgl_masuk.date() > tgl_awal.date():
            xn_tgl_kerja = len([k for k in kalender_rows if k.TGL_KERJA and k.TGL_KERJA > tgl_masuk])
        else:
            xn_tgl_kerja = default_tgl_kerja
        
        alpa_a = sum(1 for a in abs_list 
                    if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'ALPA' 
                    and a.PENDUKUNG_IN == 'N')
        
        tdk_masuk_tanpa_ket = alpa_a + (xn_tgl_kerja - len(abs_list))
        if tdk_masuk_tanpa_ket < 0:
            tdk_masuk_tanpa_ket = 0
        
        # Grand total menit
        grand_tot_menit = abs(tot_psw_a) + tot_tlm_a + (sakit_a * 60 * 8) + (tdk_masuk_tanpa_ket * 60 * 8)
        
        if grand_tot_menit > 0:
            tot_hr = grand_tot_menit // (60 * 8)
            sisa_menit = grand_tot_menit % (60 * 8)
            tot_jam = sisa_menit // 60
            tot_menit = sisa_menit % 60
            
            hasil.append({
                'nip': peg.NIP,
                'nama': peg.NAMA,
                'grand_tot_menit': grand_tot_menit,
                'tot_tlm_a': tot_tlm_a,
                'tot_psw_a': abs(tot_psw_a),
                'sakit_a': sakit_a,
                'tdk_masuk': tdk_masuk_tanpa_ket,
                'tot_hr': tot_hr,
                'tot_jam': tot_jam,
                'tot_menit': tot_menit,
            })
    
    if not hasil:
        return {'error': 'Tidak ada pegawai yang melanggar disiplin absensi'}, 400
    
    # Sort by grand_tot_menit descending
    hasil.sort(key=lambda x: x['grand_tot_menit'], reverse=True)
    
    # Nama unit
    unit_names = ', '.join([u.NAMA_UNIT_KERJA for u in MfUnitKerja.query.filter(MfUnitKerja.UNIT_KERJA_ID.in_(unit_ids)).all()])
    
    # Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Pelanggaran"
    ws.sheet_properties.tabColor = "FF7B00"
    
    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except:
        pass
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    col_paraf = 10
    
    # Judul
    ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=col_paraf)
    ws.cell(row=2, column=4, value='Ranking Pelanggaran Disiplin Absensi').font = Font(bold=True, size=12)
    ws.cell(row=2, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=3, start_column=4, end_row=3, end_column=col_paraf)
    ws.cell(row=3, column=4, value=f"Periode {tgl_awal:%d.%m.%Y} s/d {tgl_akhir:%d.%m.%Y}")
    ws.cell(row=3, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=4, start_column=4, end_row=4, end_column=col_paraf)
    ws.cell(row=4, column=4, value=f"Unit : {unit_names}").font = Font(bold=True)
    ws.cell(row=4, column=4).alignment = Alignment(horizontal='center')
    
    # Header
    ws.merge_cells('B5:B6')
    ws.cell(row=5, column=2, value='No').border = border
    ws.cell(row=5, column=2).font = Font(bold=True)
    ws.cell(row=5, column=2).alignment = Alignment(horizontal='center', vertical='center')
    
    ws.merge_cells('C5:C6')
    ws.cell(row=5, column=3, value='Nama').border = border
    ws.cell(row=5, column=3).font = Font(bold=True)
    ws.cell(row=5, column=3).alignment = Alignment(horizontal='center', vertical='center')
    
    ws.merge_cells('D5:G5')
    ws.cell(row=5, column=4, value='Tanpa Keterangan').border = border
    ws.cell(row=5, column=4).font = Font(bold=True)
    ws.cell(row=5, column=4).alignment = Alignment(horizontal='center')
    
    for col, val in {4: 'TLM\n(menit)', 5: 'PSW\n(menit)', 6: 'Sakit\n(Hr Kerja)', 7: 'Ketidakhadiran\n(Hr Kerja)'}.items():
        c = ws.cell(row=6, column=col, value=val)
        c.border = border; c.font = Font(bold=True)
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    ws.merge_cells('H5:J5')
    ws.cell(row=5, column=8, value='Total').border = border
    ws.cell(row=5, column=8).font = Font(bold=True)
    ws.cell(row=5, column=8).alignment = Alignment(horizontal='center')
    
    for col, val in {8: 'Hr\nKerja', 9: 'Jam', 10: 'Menit'}.items():
        c = ws.cell(row=6, column=col, value=val)
        c.border = border; c.font = Font(bold=True)
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Lebar kolom
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 30
    for c in ['D','E','F','G','H','I','J']:
        ws.column_dimensions[c].width = 10
    
    # Isi data
    for i, row_data in enumerate(hasil, 1):
        for c in range(2, 11):
            ws.cell(row=6+i, column=c).border = border
        
        ws.cell(row=6+i, column=2, value=i).alignment = Alignment(horizontal='center', vertical='top')
        ws.cell(row=6+i, column=3, value=f"{row_data['nama']}\n{row_data['nip']}").alignment = Alignment(vertical='top', wrap_text=True)
        ws.cell(row=6+i, column=4, value=row_data['tot_tlm_a'] or None).alignment = Alignment(horizontal='right')
        ws.cell(row=6+i, column=5, value=row_data['tot_psw_a'] or None).alignment = Alignment(horizontal='right')
        ws.cell(row=6+i, column=6, value=row_data['sakit_a'] or None).alignment = Alignment(horizontal='right')
        ws.cell(row=6+i, column=7, value=row_data['tdk_masuk'] or None).alignment = Alignment(horizontal='right')
        ws.cell(row=6+i, column=8, value=row_data['tot_hr'] or None).alignment = Alignment(horizontal='right')
        ws.cell(row=6+i, column=9, value=row_data['tot_jam'] or None).alignment = Alignment(horizontal='right')
        ws.cell(row=6+i, column=10, value=row_data['tot_menit'] or None).alignment = Alignment(horizontal='right')
    
    last_row = 6 + len(hasil)
    ws.cell(row=last_row+2, column=3, value='Keterangan')
    ws.cell(row=last_row+3, column=3, value='TLM : Terlambat Masuk')
    ws.cell(row=last_row+4, column=3, value='PSW : Pulang Sebelum Waktu')
    
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
        download_name=f"Rekap_Pelanggaran_Disiplin_{tgl_awal:%Y%m%d}_{tgl_akhir:%Y%m%d}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def laporan_rekap_uang_makan():
    """Render halaman Laporan Rekap Uang Makan."""
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Laporan Rekap Uang Makan.html',
        unit_kerja_list=unit_kerja_list
    )

def export_rekap_uang_makan():
    """Export Rekap Uang Makan (seperti RekapUM di VB.NET)."""
    unit_list = request.form.getlist('unit_kerja[]')
    bulan_str = request.form.get('bulan', '')  # Format: YYYY-MM
    staf_kepegawaian = request.form.get('staf_kepegawaian', '')
    kasubag_umum = request.form.get('kasubag_umum', '')
    
    if not unit_list or not bulan_str:
        return {'error': 'Unit atau bulan kosong'}, 400
    
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    # Parse bulan -> tgl_awal & tgl_akhir
    tahun, bulan = map(int, bulan_str.split('-'))
    tgl_awal = datetime(tahun, bulan, 1)
    # Akhir bulan
    if bulan == 12:
        tgl_akhir = datetime(tahun + 1, 1, 1) - timedelta(days=1)
    else:
        tgl_akhir = datetime(tahun, bulan + 1, 1) - timedelta(days=1)
    
    # Cek tgl server
    tgl_server = datetime.now()
    if tgl_server.date() < tgl_awal.date():
        return {'error': 'Tgl server lebih kecil dari tanggal awal periode'}, 400
    if tgl_server.date() < tgl_akhir.date():
        tgl_akhir = tgl_server
    
    # Ambil kalender hari kerja
    kalender_rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(MfKalender.IS_LIBUR == 'N')
        .all()
    )
    default_tgl_kerja = len(kalender_rows)
    
    # Ambil nominal uang makan terbaru
    um_row = (
        MfTunjangan.query
        .filter(MfTunjangan.JENIS_TUNJANGAN == 'U.Makan')
        .filter(MfTunjangan.TGL_MULAI <= tgl_akhir.date())
        .order_by(MfTunjangan.TGL_MULAI.desc())
        .first()
    )
    nominal_um = um_row.NOMINAL if um_row else 0
    
    # Ambil data absensi (join via NIP)
    absensi_rows = (
        db.session.query(Absensi, Pegawai)
        .join(Pegawai, Absensi.NIP == Pegawai.NIP)
        .join(MfKalender, Absensi.TGL_KERJA == MfKalender.TGL_KERJA)
        .filter(Absensi.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(MfKalender.IS_LIBUR == 'N')
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .all()
    )
    
    # Ambil data pegawai
    pegawai_list = (
        Pegawai.query
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(
            db.or_(
                db.and_(Pegawai.TGL_MASUK <= tgl_akhir, Pegawai.IS_KELUAR == 0),
                db.and_(Pegawai.IS_KELUAR == 1, Pegawai.TGL_KELUAR >= tgl_awal)
            )
        )
        .order_by(Pegawai.NAMA)
        .all()
    )
    
    if not pegawai_list:
        return {'error': 'Pegawai tidak ditemukan'}, 400
    
    # Build dict absensi per NIP
    from collections import defaultdict
    absensi_dict = defaultdict(list)
    for a, p in absensi_rows:
        absensi_dict[p.NIP].append(a)
    
    # Nama unit
    unit_names = ', '.join([u.NAMA_UNIT_KERJA for u in MfUnitKerja.query.filter(MfUnitKerja.UNIT_KERJA_ID.in_(unit_ids)).all()])
    
    # Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Uang Makan"
    ws.sheet_properties.tabColor = "FF7B00"
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    
    col_paraf = 16
    
    # Logo
    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except:
        pass
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    green_fill = PatternFill(start_color='ADFF2F', end_color='ADFF2F', fill_type='solid')
    gray_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
    
    # === JUDUL ===
    ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=col_paraf-1)
    ws.cell(row=2, column=4, value='REKAP UANG MAKAN').font = Font(bold=True, size=14)
    ws.cell(row=2, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=3, start_column=4, end_row=3, end_column=col_paraf-1)
    ws.cell(row=3, column=4, value=f"PEGAWAI KANTOR PENCARIAN DAN PERTOLONGAN {unit_names}")
    ws.cell(row=3, column=4).font = Font(bold=True)
    ws.cell(row=3, column=4).alignment = Alignment(horizontal='center')
    
    # Info bulan & hari kerja
    ws.cell(row=5, column=14, value='Bulan').font = Font(bold=True)
    ws.cell(row=5, column=15, value=f": {tgl_awal:%B %Y}")
    ws.cell(row=6, column=14, value='Hari Kerja').font = Font(bold=True)
    ws.cell(row=6, column=15, value=f": {default_tgl_kerja}")
    
    # === HEADER (row 7-9) ===
    # Row 7
    ws.cell(row=7, column=2, value='No')
    ws.cell(row=7, column=3, value='Nama')
    ws.cell(row=7, column=4, value='Pangkat')
    ws.cell(row=7, column=5, value='NIP')
    ws.cell(row=7, column=6, value='Jenis Absensi')
    ws.merge_cells(start_row=7, start_column=6, end_row=7, end_column=10)
    ws.cell(row=7, column=11, value='JUMLAH HARI')
    ws.merge_cells(start_row=7, start_column=11, end_row=7, end_column=12)
    ws.cell(row=7, column=13, value='JUMLAH UANG (Rp)')
    ws.cell(row=7, column=14, value='TANDA TANGAN')
    ws.merge_cells(start_row=7, start_column=14, end_row=7, end_column=15)
    
    # Row 8
    ws.cell(row=8, column=6, value='DL')
    ws.cell(row=8, column=7, value='CT')
    ws.cell(row=8, column=8, value='i')
    ws.cell(row=8, column=9, value='S')
    ws.cell(row=8, column=10, value='TA')
    
    # Merge
    ws.merge_cells('B7:B9')
    ws.merge_cells('C7:C9')
    ws.merge_cells('D7:D9')
    ws.merge_cells('E7:E9')
    ws.merge_cells('K7:L8')
    ws.merge_cells('M7:M9')
    ws.merge_cells('N7:O8')
    ws.merge_cells('K9:L9')
    ws.merge_cells('N9:O9')
    
    # Styling header (pakai try-except untuk skip merged cells)
    for r in range(7, 10):
        for c in range(2, 16):
            try:
                cell = ws.cell(row=r, column=c)
                cell.border = border
                cell.fill = green_fill
                cell.font = Font(bold=True, size=9)
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            except AttributeError:
                pass  # Skip merged cells
    
    # Lebar kolom
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20
    for c in ['F','G','H','I','J','K','L']:
        ws.column_dimensions[c].width = 5
    ws.column_dimensions['M'].width = 15
    ws.column_dimensions['N'].width = 17
    ws.column_dimensions['O'].width = 17
    
    # === ISI DATA ===
    row = 10
    no = 1
    total_um = 0
    
    for peg in pegawai_list:
        abs_list = absensi_dict.get(peg.NIP, [])
        
        # Hitung per kategori
        dl_count = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'DINASLUAR' and a.STATUS_UM == 1)
        
        cuti_ct = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'CUTI' and a.TINGKAT_TLM == 'CT')
        cuti_cb1 = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'CUTI' and a.TINGKAT_TLM == 'CB-1')
        cuti_cb2 = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'CUTI' and a.TINGKAT_TLM == 'CB-2')
        cuti_cb3 = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'CUTI' and a.TINGKAT_TLM == 'CB-3')
        cuti_capm2 = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'CUTI' and a.TINGKAT_TLM == 'CAP-M2')
        cuti_cap = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'CUTI' and a.TINGKAT_TLM == 'CAP')
        total_cuti = cuti_ct + cuti_cb1 + cuti_cb2 + cuti_cb3 + cuti_capm2 + cuti_cap
        
        sakit_all = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'SAKIT')
        alpa_ijin = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'ALPA' and a.PENDUKUNG_IN == 'Y')
        alpa_tanpa = sum(1 for a in abs_list if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'ALPA' and a.PENDUKUNG_IN != 'Y')
        
        # Hitung hari kerja per pegawai (kalau masuk setelah tgl_awal)
        tgl_masuk = peg.TGL_MASUK
        if tgl_masuk and tgl_masuk.date() > tgl_awal.date():
            xn_tgl_kerja = len([k for k in kalender_rows if k.TGL_KERJA and k.TGL_KERJA > tgl_masuk])
        else:
            xn_tgl_kerja = default_tgl_kerja
        
        ta = alpa_tanpa + (xn_tgl_kerja - len(abs_list))
        if ta < 0:
            ta = 0
        
        jumlah_hari = xn_tgl_kerja - (total_cuti + sakit_all + dl_count + ta + alpa_ijin)
        if jumlah_hari < 0:
            jumlah_hari = 0
        
        um = jumlah_hari * nominal_um
        total_um += um
        
        # Tulis data
        for c in range(2, 16):
            ws.cell(row=row, column=c).border = border
        
        ws.cell(row=row, column=2, value=no).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=peg.NAMA)
        ws.cell(row=row, column=4, value=f"{peg.GOL_ID} - {peg.PANGKAT or ''}")
        ws.cell(row=row, column=5, value=peg.NIP)
        if dl_count > 0:
            ws.cell(row=row, column=6, value=dl_count).alignment = Alignment(horizontal='center')
        if total_cuti > 0:
            ws.cell(row=row, column=7, value=total_cuti).alignment = Alignment(horizontal='center')
        if alpa_ijin > 0:
            ws.cell(row=row, column=8, value=alpa_ijin).alignment = Alignment(horizontal='center')
        if sakit_all > 0:
            ws.cell(row=row, column=9, value=sakit_all).alignment = Alignment(horizontal='center')
        if ta > 0:
            ws.cell(row=row, column=10, value=ta).alignment = Alignment(horizontal='center')
        
        ws.cell(row=row, column=11, value=jumlah_hari).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=12, value='hari').alignment = Alignment(horizontal='center')
        
        if um > 0:
            ws.cell(row=row, column=13, value=um)
            ws.cell(row=row, column=13).number_format = '#,##0'
        
        # Tanda tangan (merge 2 baris untuk ganjil)
        if no % 2 == 1:
            ws.merge_cells(start_row=row, start_column=14, end_row=row+1, end_column=14)
            ws.merge_cells(start_row=row, start_column=15, end_row=row+1, end_column=15)
            ws.cell(row=row, column=14, value=no).alignment = Alignment(vertical='top')
        
        no += 1
        row += 1
    
    # === BARIS TOTAL ===
    if no % 2 == 0:
        row += 1
    
    for c in range(2, 16):
        ws.cell(row=row, column=c).border = border
        ws.cell(row=row, column=c).fill = gray_fill
    
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)
    ws.cell(row=row, column=2, value='TOTAL').font = Font(bold=True)
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=12, value='Rp').font = Font(bold=True)
    ws.cell(row=row, column=13, value=total_um)
    ws.cell(row=row, column=13).number_format = '#,##0'
    
    # === TANDA TANGAN ===
    row += 2
    ws.cell(row=row, column=13, value=f"Surabaya, {tgl_akhir:%B %Y}")
    ws.merge_cells(start_row=row, start_column=13, end_row=row, end_column=15)
    
    row += 1
    ws.merge_cells(start_row=row, start_column=6, end_row=row, end_column=9)
    ws.cell(row=row, column=6, value='Mengetahui,')
    ws.cell(row=row, column=13, value='Staf Kepegawaian')
    ws.merge_cells(start_row=row, start_column=13, end_row=row, end_column=15)
    
    row += 1
    ws.merge_cells(start_row=row, start_column=6, end_row=row, end_column=9)
    ws.cell(row=row, column=6, value='Kasubag Umum')
    
    row += 4
    ws.merge_cells(start_row=row, start_column=6, end_row=row, end_column=11)
    ws.cell(row=row, column=6, value=kasubag_umum).font = Font(underline='single')
    ws.merge_cells(start_row=row, start_column=13, end_row=row, end_column=15)
    ws.cell(row=row, column=13, value=staf_kepegawaian).font = Font(underline='single')
    
    row += 1
    ws.merge_cells(start_row=row, start_column=6, end_row=row, end_column=11)
    ws.cell(row=row, column=6, value='NIP. ................................')
    ws.merge_cells(start_row=row, start_column=13, end_row=row, end_column=15)
    ws.cell(row=row, column=13, value='NIP. ................................')
    
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf, as_attachment=True,
        download_name=f"Rekap_Uang_Makan_{tgl_awal:%Y%m}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def laporan_rekap_tunjangan_kinerja():
    """Render halaman Laporan Rincian Pembayaran Tunjangan."""
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Laporan Rincian Pembayaran Tunjangan.html',
        unit_kerja_list=unit_kerja_list
    )

def export_rekap_tunjangan_kinerja():
    """Export Rincian Pembayaran Tunjangan Kinerja."""
    unit_list = request.form.getlist('unit_kerja[]')
    tgl_awal_str = request.form.get('tgl_awal')
    tgl_akhir_str = request.form.get('tgl_akhir')
    
    if not unit_list or not tgl_awal_str or not tgl_akhir_str:
        return {'error': 'Unit kosong atau format tanggal salah'}, 400
    
    try:
        unit_ids = [int(u) for u in unit_list]
    except ValueError:
        return {'error': 'Unit Kerja ID harus berupa angka'}, 400
    
    tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
    tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d')
    
    # Cek tgl server
    tgl_server = datetime.now()
    if tgl_server.date() < tgl_awal.date():
        return {'error': 'Tgl server lebih kecil dari tanggal awal periode'}, 400
    if tgl_server.date() < tgl_akhir.date():
        tgl_akhir = tgl_server
    
    # Ambil kalender
    kalender_rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .all()
    )
    
    # Ambil data absensi (join via NIP)
    absensi_rows = (
        db.session.query(Absensi, Pegawai)
        .join(Pegawai, Absensi.NIP == Pegawai.NIP)
        .join(MfKalender, Absensi.TGL_KERJA == MfKalender.TGL_KERJA)
        .filter(Absensi.TGL_KERJA.between(tgl_awal, tgl_akhir))
        .filter(MfKalender.IS_LIBUR == 'N')
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .all()
    )
    
    # Ambil data pegawai
    pegawai_list = (
        Pegawai.query
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .filter(Pegawai.TGL_MASUK <= tgl_akhir)
        .filter(
            db.or_(
                Pegawai.IS_KELUAR == 0,
                db.and_(Pegawai.IS_KELUAR == 1, Pegawai.TGL_KELUAR >= tgl_awal)
            )
        )
        .order_by(Pegawai.NAMA)
        .all()
    )
    
    if not pegawai_list:
        return {'error': 'Pegawai tidak ditemukan'}, 400
    
    # Ambil MFPot untuk persentase potongan
    potongan_list = (
        MfPot.query
        .filter(MfPot.TGL_MULAI <= tgl_akhir)
        .all()
    )
    
    # Ambil tunjangan per class
    class_tunjangan = {}
    for c in MfClass.query.filter(MfClass.TGL_MULAI <= tgl_akhir.date()).order_by(MfClass.TGL_MULAI.desc()).all():
        if c.CLASS_ID not in class_tunjangan:
            class_tunjangan[c.CLASS_ID] = c.TUNJANGAN
    
    # DinasLuar > 4 bulan
    dl_rows = (
        DinasLuar.query
        .join(Pegawai, DinasLuar.NIP == Pegawai.NIP)
        .filter(DinasLuar.TRANSAKSI == 'DinasLuar')
        .filter(DinasLuar.STATUS_UM == 1)
        .filter(DinasLuar.TGL_AKHIR_DINAS_LUAR >= DinasLuar.TGL_AWAL_DINAS_LUAR)  # > 4 bulan
        .filter(DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_akhir)
        .filter(DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_awal)
        .filter(Pegawai.UNIT_KERJA_ID.in_(unit_ids))
        .all()
    )
    
    # Build dict absensi
    absensi_dict = defaultdict(list)
    for a, p in absensi_rows:
        tgl_key = a.TGL_KERJA.strftime('%Y-%m-%d') if a.TGL_KERJA else None
        absensi_dict[p.NIP].append(a)
    
    # Build dict DL
    dl_dict = defaultdict(list)
    for dl in dl_rows:
        dl_dict[dl.NIP].append(dl)
    
    pot_dict = {}
    for p in potongan_list:
        pot_dict[p.KATEGORI] = p.PERSEN_POT or 0
    
    pot_ta = pot_dict.get('TA', 0)  # 5%
    pot_dl = pot_dict.get('DINASLUAR', 0)  # 1%
    
    # Hitung per pegawai
    hasil = []
    for peg in pegawai_list:
        abs_list = absensi_dict.get(peg.NIP, [])
        tunjangan = class_tunjangan.get(peg.CLASS_ID, 0) or 0
        
        # ✅ Buat dict lookup per tanggal untuk akses cepat
        abs_lookup = {}
        for a in abs_list:
            tgl_key = a.TGL_KERJA.strftime('%Y-%m-%d') if a.TGL_KERJA else None
            abs_lookup[tgl_key] = a
        
        persen_pot = 0
        tgl_masuk = peg.TGL_MASUK
        tgl_hitung = tgl_masuk if tgl_masuk and tgl_masuk > tgl_awal else tgl_awal
        
        d = tgl_hitung
        while d.date() <= tgl_akhir.date():
            # Cek libur dari kalender_rows
            is_libur = False
            tgl_str = d.strftime('%Y-%m-%d')
            
            kl = [k for k in kalender_rows if k.TGL_KERJA and k.TGL_KERJA.strftime('%Y-%m-%d') == tgl_str]
            if kl:
                is_libur = kl[0].IS_LIBUR == 'Y'
            elif d.weekday() >= 5:
                is_libur = True
            
            if not is_libur:
                # ✅ Cari record absensi via lookup dict
                a = abs_lookup.get(tgl_str)
                
                if a:
                    transaksi = (a.TRANSAKSI_IN or '').strip().lower()
                    
                    if transaksi in ('alpa', 'sakit', 'ijin'):
                        persen_pot += a.PERSEN_POT_TLM or 0
                    elif transaksi == 'dinasluar':
                        pass
                    else:
                        persen_pot += (a.PERSEN_POT_TLM or 0) + (a.PERSEN_POT_PSW or 0)
                else:
                    persen_pot += pot_ta
                
                # Cek DL > 4 bulan
                dl_peg = dl_dict.get(peg.NIP, [])
                for dl in dl_peg:
                    if dl.TGL_AWAL_DINAS_LUAR:
                        limit_dl = dl.TGL_AWAL_DINAS_LUAR + timedelta(days=120)
                        tgl_akhir_dl = dl.TGL_AKHIR_DINAS_LUAR.date() if dl.TGL_AKHIR_DINAS_LUAR else d.date()
                        if limit_dl.date() <= d.date() <= tgl_akhir_dl:
                            persen_pot += pot_dl
                            break
            
            d += timedelta(days=1)
        
        # ✅ Hitung nilai potongan (seperti VB.NET: tunjangan * persen_pot / 100)
        nilai_pot = tunjangan * (persen_pot / 100) if persen_pot > 0 else 0
        jumlah_dibayarkan = tunjangan - nilai_pot
        
        hasil.append({
            'nama': peg.NAMA,
            'nip': peg.NIP,
            'jabatan': f"TMT: {peg.TMT_JABATAN.strftime('%d/%m/%Y') if peg.TMT_JABATAN else '-'}",
            'class_id': peg.CLASS_ID,
            'tunjangan': tunjangan,
            'persen_pot': persen_pot,
            'nilai_pot': nilai_pot,
            'jumlah_pot': nilai_pot,
            'dibayarkan': jumlah_dibayarkan,
        })
    
    if not hasil:
        return {'error': 'Record tidak ada'}, 400
    
    # Nama unit
    unit_names = ', '.join([u.NAMA_UNIT_KERJA for u in MfUnitKerja.query.filter(MfUnitKerja.UNIT_KERJA_ID.in_(unit_ids)).all()])
    
    # Build Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Tunjangan"
    ws.sheet_properties.tabColor = "FF7B00"
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    
    try:
        img = XLImage('static/img/LogoSAR.png')
        img.width, img.height = 50, 50
        ws.add_image(img, 'A1')
    except:
        pass
    
    thin = Side(style='thin')
    border = Border(top=thin, left=thin, right=thin, bottom=thin)
    col_paraf = 12
    
    # Judul
    ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=col_paraf)
    ws.cell(row=2, column=4, value='Rincian Pembayaran Tunjangan').font = Font(bold=True, size=12)
    ws.cell(row=2, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=3, start_column=4, end_row=3, end_column=col_paraf)
    ws.cell(row=3, column=4, value=f"Periode {tgl_awal:%d.%m.%Y} s.d {tgl_akhir:%d.%m.%Y}")
    ws.cell(row=3, column=4).alignment = Alignment(horizontal='center')
    
    ws.merge_cells(start_row=4, start_column=4, end_row=4, end_column=col_paraf)
    ws.cell(row=4, column=4, value=f"Unit : {unit_names}").font = Font(bold=True)
    ws.cell(row=4, column=4).alignment = Alignment(horizontal='center')
    
    # Header
    headers = {2: 'No', 3: 'Nama', 4: 'NIP', 5: 'Status\nKepeg', 6: 'Jabatan\nTMT', 
               7: 'Kelas\nJabatan', 8: 'Tunjangan\nKerja', 9: 'Persen\nPot.', 
               10: 'Nilai\nPot.', 11: 'Jumlah\nPot.', 12: 'Jumlah\ndibayarkan'}
    
    for col, val in headers.items():
        c = ws.cell(row=5, column=col, value=val)
        c.border = border; c.font = Font(bold=True)
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Lebar kolom
    ws.column_dimensions['B'].width = 5
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 8
    ws.column_dimensions['F'].width = 30
    ws.column_dimensions['G'].width = 8
    ws.column_dimensions['H'].width = 15
    ws.column_dimensions['I'].width = 8
    ws.column_dimensions['J'].width = 12
    ws.column_dimensions['K'].width = 12
    ws.column_dimensions['L'].width = 15
    
    # Isi data
    grand_total = 0
    for i, row_data in enumerate(hasil, 1):
        for c in range(2, 13):
            ws.cell(row=5+i, column=c).border = border
        
        ws.cell(row=5+i, column=2, value=i).alignment = Alignment(horizontal='center')
        ws.cell(row=5+i, column=3, value=row_data['nama'])
        ws.cell(row=5+i, column=4, value=row_data['nip'])
        ws.cell(row=5+i, column=5, value='PNS')
        ws.cell(row=5+i, column=6, value=row_data['jabatan'])
        ws.cell(row=5+i, column=7, value=row_data['class_id'] if row_data['class_id'] else '').alignment = Alignment(horizontal='center')
        
        if row_data['tunjangan'] > 0:
            ws.cell(row=5+i, column=8, value=row_data['tunjangan']).number_format = '#,##0.00'
        if row_data['persen_pot'] > 0:
            ws.cell(row=5+i, column=9, value=row_data['persen_pot']).number_format = '0.00'
        if row_data['nilai_pot'] > 0:
            ws.cell(row=5+i, column=10, value=row_data['nilai_pot']).number_format = '#,##0.00'
        if row_data['jumlah_pot'] > 0:
            ws.cell(row=5+i, column=11, value=row_data['jumlah_pot']).number_format = '#,##0.00'
        if row_data['dibayarkan'] > 0:
            ws.cell(row=5+i, column=12, value=row_data['dibayarkan']).number_format = '#,##0.00'
        
        grand_total += row_data['dibayarkan']
    
    # Baris total
    last_row = 5 + len(hasil) + 1
    for c in range(2, 13):
        ws.cell(row=last_row, column=c).border = border
    
    ws.merge_cells(start_row=last_row, start_column=2, end_row=last_row, end_column=11)
    ws.cell(row=last_row, column=2, value='Total').font = Font(bold=True)
    ws.cell(row=last_row, column=12, value=grand_total).number_format = '#,##0.00'
    
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
        download_name=f"Rincian_Pembayaran_Tunjangan_{tgl_awal:%Y%m%d}_{tgl_akhir:%Y%m%d}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')