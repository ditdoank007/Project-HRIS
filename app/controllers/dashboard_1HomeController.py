# controllers/dashboard_1HomeController.py
from collections import defaultdict

from flask import render_template, request
from datetime import date, datetime, timedelta
from app import db
from app.models.kalenderModel import MfKalender
from app.models.pegawaiModel import Pegawai
from app.models.golonganModel import MfGolongan
from app.models.absensiModel import Absensi
from app.models.potModel import MfPot
from app.models.unitKerjaModel import MfUnitKerja
from app.utils.jabatanHelper import pegawai_sort_key
from sqlalchemy import or_


def dashboard_pelanggaran():
    """
    Render halaman Dashboard Pelanggaran.
    Menampilkan tabel hukuman disiplin pegawai berdasarkan jumlah
    ketidakhadiran hari kerja.
    """
    # ✅ Baca parameter tahun dari query string
    tahun_str = request.args.get('tahun', str(date.today().year))
    try:
        tahun = int(tahun_str)
    except ValueError:
        tahun = date.today().year
    
    data_pelanggaran = _get_data_pelanggaran(tahun)
    return render_template(
        'pages/dashboard_1/Dashboard Pelanggaran.html',
        data_pelanggaran=data_pelanggaran,
        selected_year=tahun  # ✅ Kirim ke template
    )


def _get_data_pelanggaran(tahun=None):
    """
    SESUAI LOGIKA VB.NET FillPelanggaran()
    """
    try:
        if tahun is None:
            tahun = date.today().year
        
        # ✅ Gunakan tahun dari parameter
        xTglawal = date(tahun, 1, 1)
        
        # Jika tahun yang dipilih = tahun sekarang, akhir = kemarin
        # Jika tahun lampau, akhir = 31 Desember tahun itu
        today = date.today()
        if tahun == today.year:
            xTglAkhir = today - timedelta(days=1)
        else:
            xTglAkhir = date(tahun, 12, 31)
        
        # 1. Ambil kalender hari kerja
        kalender_rows = (
            MfKalender.query
            .filter(MfKalender.TGL_KERJA.between(
                datetime.combine(xTglawal, datetime.min.time()),
                datetime.combine(xTglAkhir, datetime.min.time())
            ))
            .filter(MfKalender.IS_LIBUR == 'N')
            .all()
        )
        default_tgl_kerja = len(kalender_rows)
        
        # 2. Ambil data absensi (✅ JOIN via NIP, bukan FINGER_ID)
        absensi_rows = (
            db.session.query(Absensi, Pegawai)
            .join(Pegawai, Absensi.FINGER_ID == Pegawai.FINGER_ID)
            .join(MfKalender, Absensi.TGL_KERJA == MfKalender.TGL_KERJA)
            .filter(Absensi.TGL_KERJA.between(
                datetime.combine(xTglawal, datetime.min.time()),
                datetime.combine(xTglAkhir, datetime.min.time())
            ))
            .filter(MfKalender.IS_LIBUR == 'N')
            .filter(Pegawai.IS_VIP == 'N')
            .filter(Pegawai.STATUS_PEG == '1')
            .all()
        )
        
        # 3. Unit Kerja aktif HRIS Reborn
        #
        # Hanya pegawai dari Unit Kerja dengan IS_AKTIF = 'Y'
        # yang masuk perhitungan Dashboard Pelanggaran.
        active_unit_ids = (
            MfUnitKerja.query
            .filter(MfUnitKerja.IS_AKTIF == 'Y')
            .with_entities(MfUnitKerja.UNIT_KERJA_ID)
            .all()
        )

        active_unit_ids = {
            str(row[0]).strip()
            for row in active_unit_ids
            if row[0] is not None
        }

        # 3. Ambil pegawai distinct
        pegawai_list = (
            Pegawai.query
            .filter(Pegawai.IS_VIP == 'N')
            .filter(Pegawai.STATUS_PEG == '1')
            .filter(Pegawai.GOL_ID != '-')
            .filter(
                Pegawai.UNIT_KERJA_ID.in_(active_unit_ids)
            )
            .filter(
                db.or_(
                    db.and_(Pegawai.TGL_MASUK <= xTglAkhir, Pegawai.IS_KELUAR == 'N'),
                    db.and_(Pegawai.IS_KELUAR == 'Y', Pegawai.TGL_KELUAR >= xTglAkhir, Pegawai.TGL_MASUK <= xTglAkhir)
                )
            )
            .all()
        )
        
        # 4. Ambil data MFPot untuk hukuman
        potongan_list = (
            MfPot.query
            .filter(MfPot.KATEGORI == 'HUKUMAN')
            .filter(MfPot.TGL_MULAI <= xTglAkhir)
            .all()
        )
        
        # Build dict absensi berdasarkan FingerID.
        # ABSENSI legacy tidak memiliki NIP.
        # Relasi ABSENSI -> PEGAWAI menggunakan FingerID.
        absensi_dict = defaultdict(list)
        for a, p in absensi_rows:
            if a.FINGER_ID:
                absensi_dict[str(a.FINGER_ID).strip()].append(a)
        
        # 5. Hitung per pegawai
        dtresult = []
        for peg in pegawai_list:
            nip = (peg.NIP or '').strip()
            finger_id = str(peg.FINGER_ID or '').strip()
            abs_list = absensi_dict.get(finger_id, [])
            
            # TLM tanpa keterangan
            tot_tlma = sum(a.AWAL_TLM or 0 for a in abs_list 
                          if a.TINGKAT_TLM in ('TLM-1','TLM-2','TLM-3','TLM-4') 
                          and a.PENDUKUNG_IN == 'N' 
                          and a.TRANSAKSI_IN in ('LogFP','Manual','-','IN NonFP'))
            
            # PSW tanpa keterangan
            tot_pswa = sum(a.TOTAL_PSW or 0 for a in abs_list 
                          if a.TINGKAT_PSW in ('PSW-1','PSW-2','PSW-3','PSW-4') 
                          and a.PENDUKUNG_OUT == 'N' 
                          and a.TRANSAKSI_OUT in ('LogFP','Manual','-','OUT NonFP'))
            
            # Sakit tanpa keterangan
            sakit_a = sum(1 for a in abs_list 
                         if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'SAKIT' 
                         and a.PENDUKUNG_IN == 'N')
            
            # Alpa tanpa keterangan
            alpa_a = sum(1 for a in abs_list 
                        if a.TRANSAKSI_IN and a.TRANSAKSI_IN.strip().upper() == 'ALPA' 
                        and a.PENDUKUNG_IN == 'N')
            
            # Hitung hari kerja
            tgl_masuk = peg.TGL_MASUK
            if tgl_masuk and tgl_masuk > datetime.combine(xTglawal, datetime.min.time()):
                xn_tgl_kerja = len([k for k in kalender_rows if k.TGL_KERJA > tgl_masuk])
            else:
                xn_tgl_kerja = default_tgl_kerja
            
            tdk_masuk = alpa_a + (xn_tgl_kerja - len(abs_list))
            if tdk_masuk < 0:
                tdk_masuk = 0
            
            # Grand total menit (seperti VB.NET)
            if tot_pswa > 0:
                tot_pswa = 0
            grand_tot = (tot_pswa * -1) + tot_tlma + (sakit_a * 60 * 8) + (tdk_masuk * 60 * 8)
            
            # Konversi ke hari (8 jam per hari)
            tot_hr = grand_tot // (60 * 8)
            
            # Hanya tampilkan jika > 4 hari
            if tot_hr > 4:
                dtresult.append({
                    'pegawai': peg,
                    'nip': peg.NIP,
                    'nama': peg.NAMA,
                    'hari': int(tot_hr)
                })
        
        # =========================================================
        # STANDARD SORT DASHBOARD PELANGGARAN
        #
        # Prioritas:
        # 1. Jumlah hari pelanggaran DESC
        # 2. Senioritas pegawai
        #    - Eselon
        #    - Class Jabatan
        #    - Golongan
        #    - Tahun Penerimaan
        #    - Tahun Lahir
        #    - Tanggal Lahir
        #    - Nama
        #    - NIP
        # =========================================================

        dtresult.sort(
            key=lambda x: (
                -x['hari'],
                pegawai_sort_key(x['pegawai'])
            )
        )
        
        # 6. Cocokkan dengan MFPot untuk dapat hukuman
        data = []
        no = 1
        for row in dtresult:
            hari = row['hari']
            
            hukuman = None
            for pot in potongan_list:
                if pot.RANGE_AWAL is not None and pot.RANGE_AKHIR is not None:
                    if pot.RANGE_AWAL <= hari <= pot.RANGE_AKHIR:
                        hukuman = pot
                        break
            
            if hukuman:
                tingkat = (hukuman.TINGKAT or '').strip().upper()
                if 'HDB' in tingkat:
                    kategori = 'Hukuman Disiplin Berat'
                    row_class = 'alert-error'
                elif 'HDS' in tingkat:
                    kategori = 'Hukuman Disiplin Sedang'
                    row_class = 'bg-orange-active'
                else:
                    kategori = 'Hukuman Disiplin Ringan'
                    row_class = 'bg-yellow-gradient'
                
                if hukuman.PERSEN_POT == 100:
                    durasi_pot = hukuman.SATUAN_DURASI or ''
                else:
                    durasi_pot = f"{int(hukuman.DURASI_POT or 0)} {hukuman.SATUAN_DURASI or ''}"
                
                data.append({
                    'no': no,
                    'nama': row['nama'],
                    'hari': hari,
                    'kategori': kategori,
                    'jenis': hukuman.TINDAKAN or hukuman.NAMA_POT or '-',
                    'potongan': int(hukuman.PERSEN_POT or 0),
                    'lama_pot': durasi_pot.strip(),
                    'row_class': row_class
                })
                no += 1
        
        return data
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


def _parse_tanggal(value):
    """
    Konversi nilai TGL_LAHIR / TMT_PANGKAT menjadi objek `date` Python,
    apapun tipe aslinya dari database (datetime, date, atau string).
    Mengembalikan None jika tidak bisa di-parse (data kosong/rusak),
    supaya baris tsb bisa di-skip alih-alih membuat request error 500.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        formats = (
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y.%m.%d',
        )
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    return None


def dashboard_pensiun():
    """
    Render halaman Dashboard Pensiun.
    Menampilkan daftar pegawai aktif yang mendekati usia pensiun,
    beserta tanggal lahir dan umur saat ini.
    """
    # Baca parameter tahun dari URL
    tahun_str = request.args.get('tahun', str(date.today().year))
    try:
        tahun = int(tahun_str)
    except ValueError:
        tahun = date.today().year
    
    # Kirim parameter tahun ke fungsi
    data_pensiun = _get_data_pensiun(tahun=tahun)
    
    return render_template(
        'pages/dashboard_1/Dashboard Pensiun.html',
        data_pensiun=data_pensiun,
        selected_year=tahun  # Kirim ke template untuk dropdown
    )


def _get_data_pensiun(tahun=None, batas_usia_minimal=57):
    """
    Ambil pegawai aktif yang punya TGL_LAHIR dan usianya sudah
    >= batas_usia_minimal (default 57 tahun sesuai VB.NET), 
    diurutkan dari yang paling tua.
    """
    try:
        results = Pegawai.query.filter(
            Pegawai.TGL_LAHIR.isnot(None),
            Pegawai.NIP.isnot(None),
            (Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR == 'N'),
            Pegawai.STATUS_PEG == '1',
            Pegawai.GOL_ID != '-'
        ).all()

        if tahun is None:
            tahun = date.today().year
        
        today = date.today()
        
        if tahun == today.year:
            xTglJalan = date(today.year, today.month, 1) - timedelta(days=1)  # Akhir bulan lalu
        else:
            xTglJalan = date(tahun, 12, 31)

        data = []

        for pegawai in results:
            # VB.NET pakai TglLahirNIP (diekstrak dari NIP)
            # Format NIP: YYYYMMDDxxxxxxx
            tgl_lahir = None
            if pegawai.NIP and len(pegawai.NIP) >= 8:
                try:
                    tgl_lahir_str = f"{pegawai.NIP[:4]}-{pegawai.NIP[4:6]}-{pegawai.NIP[6:8]}"
                    tgl_lahir = datetime.strptime(tgl_lahir_str, '%Y-%m-%d').date()
                except:
                    pass
            
            # Fallback ke TGL_LAHIR jika NIP tidak bisa diparse
            if tgl_lahir is None:
                tgl_lahir = _parse_tanggal(pegawai.TGL_LAHIR)
            
            if tgl_lahir is None:
                continue
            
            umur_str = _hitung_rentang(tgl_lahir, xTglJalan)
            
            # Parse tahun dari umur
            parts = umur_str.replace('t', '').replace('b', '').replace('h', '').split(',')
            thn_umur = int(parts[0].strip()) if len(parts) > 0 else 0
            
            if thn_umur >= batas_usia_minimal:
                data.append({
                    'no': 0,
                    'nip': pegawai.NIP,
                    'nama': pegawai.NAMA,
                    'tgl_lahir': tgl_lahir,
                    'tgl_lahir_str': tgl_lahir.strftime('%Y.%m.%d'),
                    'umur': thn_umur
                })

        data.sort(key=lambda x: x['umur'], reverse=True)
        
        for i, row in enumerate(data, 1):
            row['no'] = i

        return data
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


def _hitung_umur(tgl_lahir, sampai_tanggal):
    """Hitung umur (tahun penuh) dari tgl_lahir sampai sampai_tanggal."""
    if not tgl_lahir:
        return 0

    umur = sampai_tanggal.year - tgl_lahir.year
    if (sampai_tanggal.month, sampai_tanggal.day) < (tgl_lahir.month, tgl_lahir.day):
        umur -= 1

    return umur


def dashboard_pangkat():
    tahun_str = request.args.get('tahun', str(date.today().year))
    try:
        tahun = int(tahun_str)
    except ValueError:
        tahun = date.today().year
    
    data_pangkat = _get_data_pangkat(tahun=tahun)
    return render_template(
        'pages/dashboard_1/Dashboard Pangkat.html',
        data_pangkat=data_pangkat,
        selected_year=tahun
    )


def _get_data_pangkat(tahun=None):
    """
    Join PEGAWAI -> MF_GOL (via GOL_ID) untuk mendapatkan nama golongan,
    lalu hitung rentang waktu sejak TMT_PANGKAT sampai hari ini.
    Hanya pegawai aktif (IS_KELUAR != 1) yang punya TMT_PANGKAT yang ditampilkan,
    diurutkan dari yang paling lama menduduki golongan saat ini.
    
    Filter:
    - Berdasarkan VB.NET: hanya pegawai dengan TypeJabatan = 'FU' (Fungsional)
    - TMT Pangkat >= 3 tahun 6 bulan
    """
    try:
        results = Pegawai.query.join(
            MfGolongan, Pegawai.GOL_ID == MfGolongan.GOL_ID
        ).filter(
            Pegawai.TMT_PANGKAT.isnot(None),
            Pegawai.TMT_PANGKAT != '1900-01-01',  # Exclude default date
            (Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR == 'N'),
            Pegawai.STATUS_PEG == '1',
            Pegawai.GOL_ID != '-'
        ).order_by(Pegawai.TMT_PANGKAT.asc()).all()

        if tahun is None:
            tahun = date.today().year
        
        # Tanggal akhir untuk perhitungan (seperti VB.NET: xTglJalanKGB)
        xTglJalanKGB = date(tahun, 1, 1)  # Awal bulan berjalan di VB.NET
        
        data = []
        today = date.today()

        for pegawai in results:
            golongan = MfGolongan.query.get(pegawai.GOL_ID)
            
            tmt = _parse_tanggal(pegawai.TMT_PANGKAT)
            if tmt is None:
                continue
            
            # Hitung rentang dari TMT Pangkat sampai xTglJalanKGB
            rentang = _hitung_rentang(tmt, xTglJalanKGB)
            
            # Parse tahun dan bulan dari rentang untuk filter (seperti VB.NET)
            # Format: "Xt, Yb, Zh"
            parts = rentang.replace('t', '').replace('b', '').replace('h', '').split(',')
            thn_pangkat = int(parts[0].strip()) if len(parts) > 0 else 0
            bln_pangkat = int(parts[1].strip()) if len(parts) > 1 else 0
            
            # Filter: hanya tampilkan jika >= 3 tahun 6 bulan (seperti VB.NET)
            if thn_pangkat >= 3 and bln_pangkat >= 6:
                data.append({
                    'no': 0,  # Akan diisi nanti
                    'nip': pegawai.NIP,
                    'nama': pegawai.NAMA,
                    'tmt_pangkat': tmt.strftime('%Y.%m.%d') if tmt else '-',
                    'gol': golongan.NAMA_GOL if golongan else pegawai.GOL_ID or '-',
                    'rentang': rentang
                })

        # Sort by rentang (paling lama di atas)
        data.sort(key=lambda x: x['tmt_pangkat'])
        
        for i, row in enumerate(data, 1):
            row['no'] = i

        return data
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


def _hitung_rentang(tmt_pangkat, sampai_tanggal):
    """
    Hitung selisih waktu dari tmt_pangkat sampai sampai_tanggal
    dalam format "Xt, Yb, Zh" (tahun, bulan, hari).
    """
    if not tmt_pangkat:
        return '-'

    tahun = sampai_tanggal.year - tmt_pangkat.year
    bulan = sampai_tanggal.month - tmt_pangkat.month
    hari = sampai_tanggal.day - tmt_pangkat.day

    if hari < 0:
        bulan -= 1
        bulan_sebelumnya = sampai_tanggal.month - 1 or 12
        tahun_bulan_sebelumnya = sampai_tanggal.year if sampai_tanggal.month > 1 else sampai_tanggal.year - 1
        hari_di_bulan_sebelumnya = _hari_dalam_bulan(tahun_bulan_sebelumnya, bulan_sebelumnya)
        hari += hari_di_bulan_sebelumnya

    if bulan < 0:
        tahun -= 1
        bulan += 12

    return f"{tahun}t, {bulan}b, {hari}h"


def _hari_dalam_bulan(tahun, bulan):
    """Jumlah hari dalam bulan tertentu (menangani tahun kabisat)."""
    if bulan == 12:
        next_month = date(tahun + 1, 1, 1)
    else:
        next_month = date(tahun, bulan + 1, 1)
    return (next_month - date(tahun, bulan, 1)).days


def dashboard_kgb():
    tahun_str = request.args.get('tahun', str(date.today().year))
    try:
        tahun = int(tahun_str)
    except ValueError:
        tahun = date.today().year
    
    data_kgb = _get_data_kgb(tahun=tahun)
    return render_template(
        'pages/dashboard_1/Dashboard KGB.html',
        data_kgb=data_kgb,
        selected_year=tahun
    )


def _get_data_kgb(tahun=None, siklus_tahun=2):
    """
    Ambil pegawai aktif yang punya TMT_CPNS/TMT_PNS, lalu hitung tanggal KGB
    berikutnya (kelipatan siklus_tahun tahun sejak TMT_CPNS yang > hari ini),
    dan tampilkan sisa waktu (Rentang) menuju tanggal tsb.
    
    Filter:
    - Hanya tampilkan jika sisa waktu <= 3 bulan (seperti VB.NET)
    """
    try:
        results = Pegawai.query.filter(
            Pegawai.TMT_CPNS.isnot(None),
            (Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR == 'N'),
            Pegawai.STATUS_PEG == '1',
            Pegawai.GOL_ID != '-',
            Pegawai.GOL_RECRUIT.isnot(None),
            Pegawai.GOL_RECRUIT != '-'
        ).all()

        if tahun is None:
            tahun = date.today().year
        
        today = date.today()
        
        # Tanggal untuk perhitungan KGB (seperti VB.NET: xTglJalanKGB)
        xTglJalanKGB = date(tahun, today.month, 1) if tahun == today.year else date(tahun, 1, 1)
        
        data = []

        for pegawai in results:
            tmt_cpns = _parse_tanggal(pegawai.TMT_CPNS)
            tmt_pns = _parse_tanggal(pegawai.TMT_PNS)
            
            if tmt_cpns is None:
                continue
            
            # Hitung KGB berikutnya dari TMT CPNS (seperti VB.NET)
            tgl_kgb_berikutnya = _hitung_tanggal_kgb_berikutnya(tmt_cpns, xTglJalanKGB, siklus_tahun)
            
            # Hitung rentang dari xTglJalanKGB ke tgl_kgb_berikutnya
            rentang = _hitung_rentang(xTglJalanKGB, tgl_kgb_berikutnya)
            
            # Parse tahun dan bulan dari rentang
            parts = rentang.replace('t', '').replace('b', '').replace('h', '').split(',')
            thn_kgb = int(parts[0].strip()) if len(parts) > 0 else 0
            bln_kgb = int(parts[1].strip()) if len(parts) > 1 else 0
            
            # Filter: hanya tampilkan jika <= 0 tahun 3 bulan (seperti VB.NET)
            if thn_kgb == 0 and bln_kgb <= 3:
                data.append({
                    'no': 0,
                    'nip': pegawai.NIP,
                    'nama': pegawai.NAMA,
                    'tmt_cpns': tmt_cpns.strftime('%Y.%m.%d'),
                    'tmt_pns': tmt_pns.strftime('%Y.%m.%d') if tmt_pns else '-',
                    'gol_recruit': pegawai.GOL_RECRUIT or '-',
                    'tgl_kgb_berikutnya': tgl_kgb_berikutnya,
                    'rentang': rentang
                })

        data.sort(key=lambda x: x['tgl_kgb_berikutnya'])
        
        for i, row in enumerate(data, 1):
            row['no'] = i

        return data
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


def _hitung_tanggal_kgb_berikutnya(tmt_pns, sampai_tanggal, siklus_tahun=2):
    """
    Hitung tanggal KGB berikutnya: kelipatan siklus_tahun tahun sejak
    tmt_pns, yang jatuh setelah (atau sama dengan) sampai_tanggal.
    """
    tahun_berjalan = tmt_pns.year
    tanggal_kgb = tmt_pns

    while tanggal_kgb < sampai_tanggal:
        tahun_berjalan += siklus_tahun
        try:
            tanggal_kgb = tanggal_kgb.replace(year=tahun_berjalan)
        except ValueError:
            tanggal_kgb = tanggal_kgb.replace(year=tahun_berjalan, day=28)

    return tanggal_kgb


def dashboard_trt():
    """Render halaman Dashboard TRT."""
    return render_template('pages/dashboard_1/Dashboard TRT.html')