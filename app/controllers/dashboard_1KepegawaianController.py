#  controllers/dashboard_1KepegawaianController.py
from operator import and_
import uuid

from flask import render_template, request, jsonify
from datetime import datetime
from datetime import timedelta

from sqlalchemy import or_
from app import db
from app.models.pegMutasiUnitModel import PegMutasiUnit
from app.models.pegawaiModel import Pegawai
from app.models.potModel import MfPot
from app.models.sprinHeaderModel import SprinHeader
from app.models.unitKerjaModel import MfUnitKerja
from app.models.jabatanModel import MfJabatan
from app.models.golonganModel import MfGolongan
from app.models.eselonModel import MfEselon
from app.models.classModel import MfClass
from app.models.dinasLuarModel import DinasLuar
from app.models.absensiModel import Absensi
from app.models.kalenderModel import MfKalender
from app.models.mediaInformasiModel import MediaInformasi
from app.models.emailSendModel import MfEmailSend
from app.utils.unitKerjaHelper import get_active_unit_rows
from app.utils.pegawaiHelper import (
    get_operational_pegawai_query,
    search_operational_pegawai,
    is_operational_pegawai,
)
from app.utils.pegawaiSortHelper import sort_pegawai_rows


def kepegawaian_cari_data_pegawai():
    """Render halaman Kepegawaian Cari Data Pegawai."""
    return render_template('pages/dashboard_1/Kepegawaian Cari Data Pegawai.html')

def api_pegawai_cari():
    """
    API: Cari data pegawai dengan filter
    Mirip dengan BtnRefresh_Click di VB.NET
    """
    try:
        # Get parameter filter
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        status_pegawai = request.args.get('status_pegawai', 'aktif')  # aktif/keluar
        status_jenis = request.args.get('status_jenis', 'pns')  # pns/non_pns
        
        # Base query
        query = (
            db.session.query(
                Pegawai,
                MfUnitKerja,
                MfGolongan,
                MfJabatan
            )
            .outerjoin(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
            .outerjoin(MfGolongan, Pegawai.GOL_ID == MfGolongan.GOL_ID)
            .outerjoin(MfJabatan, Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID)
        )
        
        # ========================================================
        # FILTER UNIT KERJA AKTIF
        #
        # Hanya pegawai yang berada pada Unit Kerja
        # dengan MF_UNIT_KERJA.IS_USE = 'Y'.
        #
        # Pegawai tidak dihapus dari database ketika unit
        # dinonaktifkan. Mereka hanya tidak ditampilkan
        # pada operasional HRIS.
        # ========================================================

        query = query.filter(
            MfUnitKerja.IS_USE == 'Y'
        )

        # Filter status pegawai (aktif/keluar)
        if status_pegawai == 'aktif':
            query = query.filter(Pegawai.IS_KELUAR == 'N')
        else:
            query = query.filter(Pegawai.IS_KELUAR == 'Y')
        
        # Filter status jenis (PNS/NON PNS)
        if status_jenis == 'pns':
            query = query.filter(Pegawai.STATUS_PEG == 1)
        else:
            query = query.filter(Pegawai.STATUS_PEG == 2)
        
        # Field mapping untuk filter
        field_mapping = {
            'NIP': Pegawai.NIP,
            'Nama Peg': Pegawai.NAMA,
            'Gol': MfGolongan.NAMA_GOL,
            'Jabatan': MfJabatan.NAMA_JABATAN,
            'Unit Kerja': MfUnitKerja.NAMA_UNIT_KERJA,
            'Jenis Kelamin': Pegawai.JENIS_KEL,
        }
        
        # Filter 1
        if filter_field1 and filter_value1:
            field = field_mapping.get(filter_field1)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value1}%'))
        
        # Filter 2
        if filter_field2 and filter_value2:
            field = field_mapping.get(filter_field2)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value2}%'))
        
        # ========================================================
        # STANDARD SORTING PEGAWAI HRIS REBORN
        #
        # Jangan membuat ORDER BY lokal di controller.
        # Seluruh modul menggunakan pegawaiSortHelper.py
        # sebagai Single Source of Truth.
        # ========================================================

        results = query.all()

        # Simpan hasil JOIN berdasarkan NIP agar hasil JOIN
        # tetap mengikuti urutan pegawai hasil standard sorting.
        result_map = {
            peg.NIP: (peg, unit, gol, jab)
            for peg, unit, gol, jab in results
        }

        sorted_pegawai = sort_pegawai_rows([
            peg
            for peg, unit, gol, jab in results
        ])

        results = [
            result_map[peg.NIP]
            for peg in sorted_pegawai
            if peg.NIP in result_map
        ][:500]
        
        # Format data
        data = []
        for i, (peg, unit, gol, jab) in enumerate(results, 1):
            # Keterangan
            keterangan = ''
            if peg.IS_KELUAR == 'Y':
                tgl = peg.TGL_KELUAR.strftime('%Y.%m.%d') if peg.TGL_KELUAR else ''
                keterangan = f"Tanggal keluar {tgl} {peg.ALASAN_KELUAR or ''}"
            
            data.append({
                'no': i,
                'nip': peg.NIP,
                'nama': peg.NAMA or '',
                'golongan': (
                    gol.NAMA_GOL
                    if gol and gol.NAMA_GOL
                    else '-'
                ),
                'pangkat': (
                    gol.PANGKAT_GOL
                    if gol and gol.PANGKAT_GOL
                    else '-'
                ),
                'unit_kerja': unit.NAMA_UNIT_KERJA if unit else '-',
                # ====================================================
                # SUMBER JABATAN HRIS REBORN
                #
                # Jangan menggunakan Pegawai.JABATAN karena merupakan
                # teks legacy. Sumber utama adalah MF_JABATAN.
                # ====================================================

                'jabatan': (
                    jab.NAMA_JABATAN
                    if jab and jab.NAMA_JABATAN
                    else '-'
                ),

                'jabatan_status': (
                    'VALID'
                    if jab and peg.JABATAN_ID not in (None, 0)
                    else (
                        'BELUM DIISI'
                        if peg.JABATAN_ID in (None, 0)
                        else 'MASTER TIDAK DITEMUKAN'
                    )
                ),

                'status_peg': (
                    'PNS'
                    if peg.STATUS_PEG == 1
                    else 'NON PNS'
                ),

            })
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'data': []})


def api_pegawai_get_filter_fields():
    """API: Get list field untuk filter dropdown"""
    try:
        fields = [
            {'field_id': 'NIP', 'field_name': 'NIP'},
            {'field_id': 'Nama Peg', 'field_name': 'Nama Peg'},
            {'field_id': 'Gol', 'field_name': 'Gol'},
            {'field_id': 'Jabatan', 'field_name': 'Jabatan'},
            {'field_id': 'Unit Kerja', 'field_name': 'Unit Kerja'},
            {'field_id': 'Jenis Kelamin', 'field_name': 'Jenis Kelamin'},
        ]
        
        return jsonify({
            'success': True,
            'data': fields
        })
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})


def kepegawaian_cari_dinas_luar_umum(type_sprin='DL'):
    """Render halaman pencarian Dinas Luar berdasarkan jenis SPRIN."""

    config = {
        'DL': {
            'title': 'Dinas Luar Umum',
            'search_title': 'Cari Dinas Luar Umum',
            'main_url': 'main.view_kepegawaian_dinas_luar_umum'
        },
        'OPR': {
            'title': 'Dinas Luar OPS',
            'search_title': 'Cari Dinas Luar OPS',
            'main_url': 'main.view_kepegawaian_dinas_luar_operasi'
        },
        'POT': {
            'title': 'Dinas Luar SD',
            'search_title': 'Cari Dinas Luar SD',
            'main_url': 'main.view_kepegawaian_dinas_luar_pelatihan'
        }
    }

    selected = config.get(type_sprin, config['DL'])

    return render_template(
        'pages/dashboard_1/Kepegawaian Cari Dinas Luar Umum.html',
        type_sprin=type_sprin,
        page_title=selected['title'],
        search_title=selected['search_title'],
        main_url=selected['main_url']
    )

def api_dinas_luar_cari():
    """
    API pencarian Dinas Luar berdasarkan jenis SPRIN dan periode.
    DL  = Umum
    OPR = Operasi
    POT = Pelatihan/SD
    """
    try:
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')

        periode = request.args.get('periode', '')
        periode_type = request.args.get('periode_type', 'bulan')
        type_sprin = request.args.get('type_sprin', 'DL').upper()

        if type_sprin not in ('DL', 'OPR', 'POT'):
            type_sprin = 'DL'

        query = SprinHeader.query.filter(
            SprinHeader.TYPE_SPRIN_ID == type_sprin
        )

        # Filter periode
        if periode:
            if periode_type == 'bulan':
                # Format: YYYY-MM
                try:
                    tahun, bulan = periode.split('-')
                    tahun = int(tahun)
                    bulan = int(bulan)

                    from sqlalchemy import extract

                    query = query.filter(
                        extract('year', SprinHeader.TGL_AWAL_SPRIN) == tahun,
                        extract('month', SprinHeader.TGL_AWAL_SPRIN) == bulan
                    )
                except (ValueError, TypeError):
                    pass

            elif periode_type == 'tahun':
                try:
                    tahun = int(periode)

                    from sqlalchemy import extract

                    query = query.filter(
                        extract('year', SprinHeader.TGL_AWAL_SPRIN) == tahun
                    )
                except (ValueError, TypeError):
                    pass

        # Filter field
        field_mapping = {
            'KeteranganDinasLuar': SprinHeader.PERIHAL_SPRIN,
            'PenempatanDinasLuar': SprinHeader.PENEMPATAN,
            'NoSurat': SprinHeader.NO_SPRIN,
        }

        if filter_field1 and filter_value1:
            field = field_mapping.get(filter_field1)
            if field is not None:
                query = query.filter(
                    field.ilike(f'%{filter_value1}%')
                )

        if filter_field2 and filter_value2:
            field = field_mapping.get(filter_field2)
            if field is not None:
                query = query.filter(
                    field.ilike(f'%{filter_value2}%')
                )

        query = query.order_by(
            SprinHeader.TGL_AWAL_SPRIN.desc()
        )

        results = query.limit(500).all()

        jenis_map = {
            'DL': 'Umum',
            'OPR': 'Operasi',
            'POT': 'Pelatihan'
        }

        data = []

        for i, sprin in enumerate(results, 1):
            update_by_name = ''

            if sprin.UPDATE_BY:
                peg = Pegawai.query.filter(Pegawai.NIP == sprin.UPDATE_BY).first()
                update_by_name = peg.NAMA if peg else sprin.UPDATE_BY

            update_date_str = (
                sprin.UPDATE_DATE.strftime('%d-%b-%Y')
                if sprin.UPDATE_DATE else ''
            )

            tgl_awal = (
                sprin.TGL_AWAL_SPRIN.strftime('%d-%b-%Y')
                if sprin.TGL_AWAL_SPRIN else '-'
            )

            tgl_akhir = sprin.TGL_AKHIR_SPRIN or '-'

            data.append({
                'no': i,
                'no_surat': sprin.NO_SPRIN or '-',
                'tgl_sprin': f"{tgl_awal} - {tgl_akhir}",
                'keterangan': sprin.PERIHAL_SPRIN or '-',
                'penempatan': sprin.PENEMPATAN or '-',
                'update_by': (
                    f"{update_by_name} - {update_date_str}"
                    if update_by_name else '-'
                ),
                'guid_sprin': sprin.GUID_SPRIN,
                'jenis': jenis_map.get(type_sprin, 'Umum'),
            })

        return jsonify({
            'success': True,
            'type_sprin': type_sprin,
            'data': data,
            'total': len(data)
        })

    except Exception as e:
        import traceback
        print("ERROR in api_dinas_luar_cari:")
        traceback.print_exc()

        return jsonify({
            'error': str(e),
            'data': [],
            'success': False
        })

def api_dinas_luar_get_filter_fields():
    """API: Get list field untuk filter dropdown"""
    try:
        fields = [
            {'field_id': 'KeteranganDinasLuar', 'field_name': 'Keterangan'},
            {'field_id': 'PenempatanDinasLuar', 'field_name': 'Penempatan'},
            {'field_id': 'NoSurat', 'field_name': 'No. Surat'},
            {'field_id': 'NamaFile', 'field_name': 'Nama File (Y/N)'},
        ]
        return jsonify({'success': True, 'data': fields})
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})


def kepegawaian_data_pegawai():
    """Render halaman Kepegawaian Data Pegawai."""
    # Hanya Unit Kerja aktif (IS_USE = 'Y')
    unit_kerja_list = get_active_unit_rows()

    jabatan_list = MfJabatan.query.filter(
        MfJabatan.NAMA_JABATAN.isnot(None)
    ).order_by(MfJabatan.URUT_JABATAN.asc()).all()
    golongan_list = MfGolongan.query.order_by(MfGolongan.URUT_GOL.asc()).all()
    eselon_list = MfEselon.query.order_by(MfEselon.URUT_ESELON.asc()).all()
    class_list = MfClass.query.order_by(MfClass.CLASS_ID.asc()).all()
    
    return render_template(
        'pages/dashboard_1/Kepegawaian Data Pegawai.html',
        unit_kerja_list=unit_kerja_list,
        jabatan_list=jabatan_list,
        golongan_list=golongan_list,
        eselon_list=eselon_list,
        class_list=class_list
    )


def _safe_int(value, default=None):
    """Helper: konversi ke int dengan aman"""
    try:
        if value is None or value == '':
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_date(value):
    """Helper: konversi string ke date dengan aman"""
    try:
        if value:
            return datetime.strptime(value, '%Y-%m-%d')
        return None
    except (ValueError, TypeError):
        return None


def api_pegawai_get():
    """API: Get data pegawai by NIP"""
    try:
        nip = request.args.get('nip', '').strip()
        
        if not nip:
            return jsonify({'error': 'NIP tidak boleh kosong'})
        
        pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
        
        if not pegawai:
            return jsonify({'error': 'Pegawai tidak ditemukan'})
        
        return jsonify({
            'success': True,
            'data': pegawai.to_dict()
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_pegawai_save():
    """API: Simpan/Update data pegawai"""
    try:
        data = request.get_json()
        
        # Debug: lihat data yang masuk
        print("📥 Data diterima:", data)
        
        nip = data.get('nip', '').strip() if data.get('nip') else ''
        finger_id = data.get('finger_id', '').strip() if data.get('finger_id') else ''

        # Legacy HRIS:
        # Jika pegawai tidak memiliki NIP, Finger ID digunakan sebagai NIP.
        if not nip:
            if not finger_id:
                return jsonify({
                    'error': 'NIP atau Finger ID wajib diisi'
                })
            nip = finger_id
        
        # Validasi wajib
        nama = data.get('nama', '').strip() if data.get('nama') else ''
        tgl_masuk = data.get('tgl_masuk', '')
        
        if not nama:
            return jsonify({'error': 'Nama tidak boleh kosong'})
        if not tgl_masuk:
            return jsonify({'error': 'Tanggal Masuk tidak boleh kosong'})
        
        # Cek existing
        pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
        is_update = pegawai is not None
        
        # Data umum
        unit_kerja_id = _safe_int(data.get('unit_kerja_id'), 1)
        jabatan_id = _safe_int(data.get('jabatan_id'), None)
        gol_id = data.get('gol_id', '') or ''
        eselon = data.get('eselon', '') or ''
        class_id = _safe_int(data.get('class_id'), None)
        alamat = data.get('alamat', '') or ''
        jenis_kel = data.get('jenis_kel', '') or ''
        tgl_lahir = _safe_date(data.get('tgl_lahir'))
        kelurahan = data.get('kelurahan', '') or ''
        kecamatan = data.get('kecamatan', '') or ''
        kota = data.get('kota', '') or ''
        no_telp = data.get('no_telp', '') or ''
        email = data.get('email', '') or ''
        tmt_pangkat = _safe_date(data.get('tmt_pangkat'))
        tmt_cpns = _safe_date(data.get('tmt_cpns'))
        tmt_pns = _safe_date(data.get('tmt_pns'))
        tmt_class = _safe_date(data.get('tmt_class'))
        tmt_jabatan = _safe_date(data.get('tmt_jabatan'))
        gol_recruit = data.get('gol_recruit', '') or ''
        status_peg = _safe_int(data.get('status_peg'), 2)
        is_keluar_val = str(
            data.get('is_keluar', 'N') or 'N'
        ).strip().upper()

        if is_keluar_val not in ('Y', 'N'):
            is_keluar_val = 'N'

        is_keluar = is_keluar_val
        tgl_keluar = _safe_date(data.get('tgl_keluar'))
        alasan_keluar = data.get('alasan_keluar', '') or ''
        
        if is_update:
            # Update
            pegawai.NAMA = nama
            pegawai.FINGER_ID = finger_id or pegawai.FINGER_ID
            pegawai.UNIT_KERJA_ID = unit_kerja_id
            pegawai.JABATAN_ID = jabatan_id
            pegawai.GOL_ID = gol_id
            pegawai.ESELON = eselon
            pegawai.CLASS_ID = class_id
            pegawai.ALAMAT = alamat
            pegawai.JENIS_KEL = jenis_kel
            pegawai.TGL_LAHIR = tgl_lahir
            pegawai.KELURAHAN = kelurahan
            pegawai.KECAMATAN = kecamatan
            pegawai.KOTA = kota
            pegawai.NO_TELP = no_telp
            pegawai.MAIL = email
            pegawai.TGL_MASUK = _safe_date(tgl_masuk)
            pegawai.TMT_PANGKAT = tmt_pangkat
            pegawai.TMT_CPNS = tmt_cpns
            pegawai.TMT_PNS = tmt_pns
            pegawai.TMT_CLASS = tmt_class
            pegawai.TMT_JABATAN = tmt_jabatan
            pegawai.GOL_RECRUIT = gol_recruit
            pegawai.STATUS_PEG = status_peg
            pegawai.IS_KELUAR = is_keluar
            pegawai.TGL_KELUAR = tgl_keluar
            pegawai.ALASAN_KELUAR = alasan_keluar
            pegawai.UPDATE_IN_BY = 'admin'
            pegawai.UPDATE_DATE = datetime.now()
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Data pegawai berhasil diupdate'})
        else:
            # Insert
            new_pegawai = Pegawai(
                NIP=nip,
                NAMA=nama,
                FINGER_ID=finger_id or nip,
                UNIT_KERJA_ID=unit_kerja_id,
                JABATAN_ID=jabatan_id,
                GOL_ID=gol_id,
                ESELON=eselon,
                CLASS_ID=class_id,
                NO_TELP=no_telp,
                MAIL=email,
                PASS='surabaya-02',
                ALAMAT=alamat,
                JENIS_KEL=jenis_kel,
                TGL_LAHIR=tgl_lahir,
                KELURAHAN=kelurahan,
                KECAMATAN=kecamatan,
                KOTA=kota,
                TGL_MASUK=_safe_date(tgl_masuk),
                TMTPANGKAT=tmt_pangkat,
                TMTCPNS=tmt_cpns,
                TMTPNS=tmt_pns,
                TMT_CLASS=tmt_class,
                TMT_JABATAN=tmt_jabatan,
                GOL_RECRUIT=gol_recruit,
                STATUS_PEG=status_peg,
                IS_KELUAR=is_keluar,
                TGL_KELUAR=tgl_keluar,
                ALASAN_KELUAR=alasan_keluar,
                UPDATE_BY='admin',
                UPDATE_DATE=datetime.now()
            )
            db.session.add(new_pegawai)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Data pegawai berhasil disimpan'})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_pegawai_delete():
    """API: Delete pegawai"""
    try:
        data = request.get_json()
        nip = data.get('nip', '').strip() if data.get('nip') else ''
        
        if not nip:
            return jsonify({'error': 'NIP tidak boleh kosong'})
        
        Pegawai.query.filter(Pegawai.NIP == nip).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data pegawai berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


def kepegawaian_dinas_luar_operasi():
    """
    Render halaman Kepegawaian Dinas Luar Operasi.
    """
    return render_template('pages/dashboard_1/Kepegawaian Dinas Luar Operasi.html')

def api_dinas_luar_operasi_save():
    """
    API: Simpan Dinas Luar Operasi
    Logic: Header dulu, baru peserta (seperti Dinas Luar Umum)
    """
    try:
        data = request.get_json()
        print("📥 Data Dinas Luar Operasi:", data)
        
        no_surat = data.get('no_surat', '').strip()
        tgl_awal_surat = data.get('tgl_awal_surat', '')
        tgl_akhir_surat = data.get('tgl_akhir_surat', '')
        keterangan = data.get('keterangan', '')
        penempatan = data.get('penempatan', '')
        jenis_operasi = data.get('jenis_operasi', True)
        status_um = data.get('status_um', '1')
        peserta_list = data.get('peserta', [])
        nama_file = data.get('nama_file', '-')
        is_update = data.get('is_update', False)
        guid_sprin_existing = data.get('guid_sprin', '')
        save_header_only = data.get('save_header_only', False)
        
        if not no_surat:
            return jsonify({'success': False, 'error': 'No. Surat tidak boleh kosong'})
        if not tgl_awal_surat or not tgl_akhir_surat:
            return jsonify({'success': False, 'error': 'Tanggal Surat tidak boleh kosong'})
        
        # STEP 1: Simpan/Cari SPRIN_HEADER dulu
        if guid_sprin_existing:
            existing_sprin = SprinHeader.query.get(guid_sprin_existing)
            if existing_sprin:
                guid_sprin = guid_sprin_existing
                # Update header
                existing_sprin.NO_SPRIN = no_surat
                existing_sprin.TGL_AWAL_SPRIN = datetime.strptime(tgl_awal_surat, '%Y-%m-%d')
                existing_sprin.TGL_SPRIN = datetime.strptime(tgl_awal_surat, '%Y-%m-%d')
                existing_sprin.TGL_AKHIR_SPRIN = tgl_akhir_surat
                existing_sprin.PERIHAL_SPRIN = keterangan
                existing_sprin.PENEMPATAN = penempatan
                existing_sprin.UPDATE_BY = 'admin'
                existing_sprin.UPDATE_DATE = datetime.now()
            else:
                guid_sprin = f"DLO_{datetime.now().strftime('%Y-%m')}_{str(uuid.uuid4())}"
        else:
            # Cek existing by no_surat dengan TYPE_SPRIN_ID='OPR'
            existing_sprin = SprinHeader.query.filter(
                SprinHeader.NO_SPRIN == no_surat,
                SprinHeader.TYPE_SPRIN_ID == 'OPR'
            ).first()
            
            if existing_sprin:
                guid_sprin = existing_sprin.GUID_SPRIN
                # Update header
                existing_sprin.TGL_AWAL_SPRIN = datetime.strptime(tgl_awal_surat, '%Y-%m-%d')
                existing_sprin.TGL_SPRIN = datetime.strptime(tgl_awal_surat, '%Y-%m-%d')
                existing_sprin.TGL_AKHIR_SPRIN = tgl_akhir_surat
                existing_sprin.PERIHAL_SPRIN = keterangan
                existing_sprin.PENEMPATAN = penempatan
                existing_sprin.UPDATE_BY = 'admin'
                existing_sprin.UPDATE_DATE = datetime.now()
            else:
                guid_sprin = f"DLO_{datetime.now().strftime('%Y-%m')}_{str(uuid.uuid4())}"
                new_sprin = SprinHeader(
                    GUID_SPRIN=guid_sprin,
                    TYPE_SPRIN_ID='OPR',
                    NO_SPRIN=no_surat,
                    TGL_SPRIN=datetime.strptime(tgl_awal_surat, '%Y-%m-%d'),
                    TGL_AWAL_SPRIN=datetime.strptime(tgl_awal_surat, '%Y-%m-%d'),
                    TGL_AKHIR_SPRIN=tgl_akhir_surat,
                    PERIHAL_SPRIN=keterangan,
                    PENEMPATAN=penempatan,
                    STATUS_UM=int(status_um),
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(new_sprin)
        
        db.session.flush()
        
        # Jika hanya simpan header, commit dan return
        if save_header_only:
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Header berhasil disimpan', 
                'guid_sprin': guid_sprin
            })
        
        # STEP 2: Simpan peserta ke DINAS_LUAR
        if not peserta_list:
            return jsonify({'success': False, 'error': 'Peserta tidak boleh kosong'})
        
        # Delete existing peserta jika update (sebelum insert baru)
        if is_update and guid_sprin_existing:
            old_peserta = DinasLuar.query.filter(
                DinasLuar.GUID_SPRIN == guid_sprin_existing,
                DinasLuar.JENIS == 'OP'
            ).all()
            for old in old_peserta:
                db.session.delete(old)
            db.session.flush()
        
        saved_count = 0
        tipe = '1' if jenis_operasi else '0'
        
        # ✅ LOOP PESERTA - HANYA PAKAI NIP
        for peserta in peserta_list:
            nip = peserta.get('nip', '')  # ✅ NIP saja
            tgl_awal = peserta.get('tgl_awal', '')
            tgl_akhir = peserta.get('tgl_akhir', '')
            status_um_peserta = peserta.get('status_um', status_um)
            
            if not nip or not tgl_awal or not tgl_akhir:
                continue
            
            # Generate TransaksiID (format: DLO_NIP_TglAwal_TglAkhir)
            transaksi_id = f"DLO_{nip}_{tgl_awal}_{tgl_akhir}"
            
            # Cek existing
            existing_dl = DinasLuar.query.filter(
                DinasLuar.DINAS_TRANSAKSI_ID == transaksi_id
            ).first()
            
            tgl_awal_date = datetime.strptime(tgl_awal, '%Y-%m-%d')
            tgl_akhir_date = datetime.strptime(tgl_akhir, '%Y-%m-%d')
            
            if existing_dl:
                # Update
                existing_dl.TGL_AWAL_DINAS_LUAR = tgl_awal_date
                existing_dl.TGL_AKHIR_DINAS_LUAR = tgl_akhir_date
                existing_dl.KETERANGAN_DINAS_LUAR = keterangan
                existing_dl.PENEMPATAN_DINAS_LUAR = penempatan
                existing_dl.STATUS_UM = int(status_um_peserta)
                existing_dl.NAMA_FILE = nama_file
                existing_dl.TIPE = tipe
                existing_dl.TGL_AWAL_SURAT = datetime.strptime(tgl_awal_surat, '%Y-%m-%d')
                existing_dl.TGL_AKHIR_SURAT = datetime.strptime(tgl_akhir_surat, '%Y-%m-%d') if tgl_akhir_surat else None
                existing_dl.UPDATE_BY = 'admin'
                existing_dl.UPDATE_DATE = datetime.now()
            else:
                # ✅ Insert baru - NIP adalah NIP asli
                new_dl = DinasLuar(
                    DINAS_TRANSAKSI_ID=transaksi_id,
                    GUID_SPRIN=guid_sprin,
                    NIP=nip,  # ✅ NIP asli pegawai
                    TGL_AWAL_DINAS_LUAR=tgl_awal_date,
                    TGL_AKHIR_DINAS_LUAR=tgl_akhir_date,
                    KETERANGAN_DINAS_LUAR=keterangan,
                    PENEMPATAN_DINAS_LUAR=penempatan,
                    TRANSAKSI='DinasLuar',
                    PENDUKUNG='Y',
                    NO_SURAT=no_surat,
                    JENIS='OP',
                    NAMA_FILE=nama_file,
                    TGL_AWAL_SURAT=datetime.strptime(tgl_awal_surat, '%Y-%m-%d'),
                    TGL_AKHIR_SURAT=datetime.strptime(tgl_akhir_surat, '%Y-%m-%d') if tgl_akhir_surat else None,
                    TIPE=tipe,
                    STATUS_UM=int(status_um_peserta),
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(new_dl)
            
            saved_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{saved_count} peserta berhasil disimpan',
            'guid_sprin': guid_sprin
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print("❌ ERROR in api_dinas_luar_operasi_save:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

def api_dinas_luar_operasi_save_peserta():
    """
    API: Simpan Peserta Dinas Luar Operasi (setelah header ada)
    Khusus Operasi: JENIS='OP', TIPE='1' atau '0'
    """
    try:
        data = request.get_json()
        print("📥 Data Peserta Operasi:", data)
        
        guid_sprin = data.get('guid_sprin', '')
        peserta_list = data.get('peserta', [])
        jenis_operasi = data.get('jenis_operasi', True)
        nama_file = data.get('nama_file', '-')
        
        if not guid_sprin:
            return jsonify({'success': False, 'error': 'GUID SPRIN tidak boleh kosong'})
        if not peserta_list:
            return jsonify({'success': False, 'error': 'Peserta tidak boleh kosong'})
        
        # Ambil data header
        header = SprinHeader.query.get(guid_sprin)
        if not header:
            return jsonify({'success': False, 'error': 'Header tidak ditemukan'})
        
        tipe = '1' if jenis_operasi else '0'
        
        saved_count = 0
        for peserta in peserta_list:
            nip = peserta.get('nip', '')  # NIP pegawai
            tgl_awal = peserta.get('tgl_awal', '')
            tgl_akhir = peserta.get('tgl_akhir', '')
            status_um = peserta.get('status_um', '0')
            
            if not nip or not tgl_awal or not tgl_akhir:
                continue
            
            # Generate TransaksiID (format: DLO_NIP_TglAwal_TglAkhir)
            transaksi_id = f"DLO_{nip}_{tgl_awal}_{tgl_akhir}"
            
            existing = DinasLuar.query.filter(
                DinasLuar.DINAS_TRANSAKSI_ID == transaksi_id
            ).first()
            
            tgl_awal_date = datetime.strptime(tgl_awal, '%Y-%m-%d')
            tgl_akhir_date = datetime.strptime(tgl_akhir, '%Y-%m-%d')
            
            if existing:
                existing.TGL_AWAL_DINAS_LUAR = tgl_awal_date
                existing.TGL_AKHIR_DINAS_LUAR = tgl_akhir_date
                existing.KETERANGAN_DINAS_LUAR = header.PERIHAL_SPRIN or ''
                existing.PENEMPATAN_DINAS_LUAR = header.PENEMPATAN or ''
                existing.STATUS_UM = int(status_um)
                existing.NAMA_FILE = nama_file
                existing.TIPE = tipe
                existing.TGL_AWAL_SURAT = header.TGL_AWAL_SPRIN
                existing.TGL_AKHIR_SURAT = header.TGL_SPRIN
                existing.UPDATE_BY = 'admin'
                existing.UPDATE_DATE = datetime.now()
            else:
                new_dl = DinasLuar(
                    DINAS_TRANSAKSI_ID=transaksi_id,
                    GUID_SPRIN=guid_sprin,
                    NIP=nip,  # NIP asli pegawai
                    TGL_AWAL_DINAS_LUAR=tgl_awal_date,
                    TGL_AKHIR_DINAS_LUAR=tgl_akhir_date,
                    KETERANGAN_DINAS_LUAR=header.PERIHAL_SPRIN or '',
                    PENEMPATAN_DINAS_LUAR=header.PENEMPATAN or '',
                    TRANSAKSI='DinasLuar',
                    PENDUKUNG='Y',
                    NO_SURAT=header.NO_SPRIN or '',
                    JENIS='OP',  # ✅ Operasi
                    NAMA_FILE=nama_file,
                    TGL_AWAL_SURAT=header.TGL_AWAL_SPRIN,
                    TGL_AKHIR_SURAT=header.TGL_SPRIN,
                    TIPE=tipe,  # ✅ 1=Operasi, 0=Non Operasi
                    STATUS_UM=int(status_um),
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(new_dl)
            
            saved_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{saved_count} peserta berhasil disimpan'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print("❌ ERROR in api_dinas_luar_operasi_save_peserta:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

def api_dinas_luar_operasi_get():
    """
    API: Get data Dinas Luar Operasi by No Surat
    Join DinasLuar.NIP ke Pegawai.NIP (pakai NIP, bukan FingerID)
    """
    try:
        no_surat = request.args.get('no_surat', '')
        if not no_surat:
            return jsonify({'success': False, 'error': 'No Surat tidak boleh kosong'})
        
        # ✅ Join by NIP
        dinas_list = db.session.query(
            DinasLuar, Pegawai
        ).outerjoin(
            Pegawai, DinasLuar.NIP == Pegawai.NIP
        ).filter(
            DinasLuar.NO_SURAT == no_surat,
            DinasLuar.TRANSAKSI == 'DinasLuar',
            DinasLuar.JENIS == 'OP'
        ).order_by(Pegawai.NAMA).all()
        
        if not dinas_list:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        first = dinas_list[0][0]
        header = {
            'guid_sprin': first.GUID_SPRIN,
            'no_surat': first.NO_SURAT,
            'tgl_awal_surat': first.TGL_AWAL_SURAT.strftime('%Y-%m-%d') if first.TGL_AWAL_SURAT else '',
            'tgl_akhir_surat': first.TGL_AKHIR_SURAT.strftime('%Y-%m-%d') if first.TGL_AKHIR_SURAT else '',
            'keterangan': first.KETERANGAN_DINAS_LUAR or '',
            'penempatan': first.PENEMPATAN_DINAS_LUAR or '',
            'status_um': str(first.STATUS_UM) if first.STATUS_UM is not None else '1',
            'tipe': first.TIPE or '1',
            'nama_file': first.NAMA_FILE or '-'
        }
        
        peserta = []
        for dl, peg in dinas_list:
            status_um_name = 'Terpotong' if str(dl.STATUS_UM) == '1' else (
                'Tdk Terpotong Penempatan' if str(dl.STATUS_UM) == '2' else 'Tdk Terpotong'
            )
            peserta.append({
                'transaksi_id': dl.DINAS_TRANSAKSI_ID,
                'nip': dl.NIP,  # NIP asli
                'nama': peg.NAMA if peg else '-',
                'tgl_awal': dl.TGL_AWAL_DINAS_LUAR.strftime('%Y-%m-%d') if dl.TGL_AWAL_DINAS_LUAR else '',
                'tgl_akhir': dl.TGL_AKHIR_DINAS_LUAR.strftime('%Y-%m-%d') if dl.TGL_AKHIR_DINAS_LUAR else '',
                'status_um': str(dl.STATUS_UM) if dl.STATUS_UM is not None else '1',
                'status_um_name': status_um_name
            })
        
        return jsonify({
            'success': True,
            'data': {
                'header': header,
                'peserta': peserta
            }
        })
        
    except Exception as e:
        import traceback
        print("❌ ERROR in api_dinas_luar_operasi_get:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_dinas_luar_operasi_delete():
    """
    API: Delete Dinas Luar Operasi
    """
    try:
        data = request.get_json()
        guid_sprin = data.get('guid_sprin', '')
        transaksi_id = data.get('transaksi_id', '')
        
        if not guid_sprin and not transaksi_id:
            return jsonify({'success': False, 'error': 'Parameter tidak lengkap'})
        
        # Cari closing date
        closing_date = None
        closing_info = MediaInformasi.query.filter(
            MediaInformasi.TRX == 'closingabsensi'
        ).order_by(MediaInformasi.PUBLISH_DATE_START.desc()).first()
        
        if closing_info:
            closing_date = closing_info.PUBLISH_DATE_START
        
        deleted_count = 0
        
        if transaksi_id:
            # Delete single peserta
            dinas = DinasLuar.query.filter(
                DinasLuar.DINAS_TRANSAKSI_ID == transaksi_id
            ).first()
            
            if dinas:
                tgl_awal = dinas.TGL_AWAL_DINAS_LUAR
                tgl_akhir = dinas.TGL_AKHIR_DINAS_LUAR
                
                if closing_date and tgl_akhir and tgl_akhir > closing_date:
                    # Delete absensi
                    Absensi.query.filter(
                        Absensi.TRANSAKSI_ID_FROM == transaksi_id,
                        Absensi.TGL_KERJA >= tgl_awal,
                        Absensi.TGL_KERJA <= tgl_akhir
                    ).delete()
                
                db.session.delete(dinas)
                deleted_count = 1
        else:
            # Delete semua dengan GUID_SPRIN
            dinas_list = DinasLuar.query.filter(
                DinasLuar.GUID_SPRIN == guid_sprin,
                DinasLuar.JENIS == 'OP'
            ).all()
            
            for dinas in dinas_list:
                tgl_awal = dinas.TGL_AWAL_DINAS_LUAR
                tgl_akhir = dinas.TGL_AKHIR_DINAS_LUAR
                
                if closing_date and tgl_akhir and tgl_akhir > closing_date:
                    Absensi.query.filter(
                        Absensi.TRANSAKSI_ID_FROM == dinas.DINAS_TRANSAKSI_ID,
                        Absensi.TGL_KERJA >= tgl_awal,
                        Absensi.TGL_KERJA <= tgl_akhir
                    ).delete()
                
                db.session.delete(dinas)
                deleted_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} data berhasil dihapus'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print("❌ ERROR in api_dinas_luar_operasi_delete:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def kepegawaian_dinas_luar_pelatihan():
    """
    Render halaman Kepegawaian Dinas Luar Pelatihan.
    """
    return render_template('pages/dashboard_1/Kepegawaian Dinas Luar Pelatihan.html')

def api_dinas_luar_pelatihan_save_peserta():
    """
    API: Simpan Peserta Dinas Luar Pelatihan (Potensi)
    SAMA PERSIS seperti Umum, hanya JENIS='PL', TYPE_SPRIN_ID='POT'
    """
    try:
        data = request.get_json()
        print("📥 Data Peserta Pelatihan:", data)
        
        guid_sprin = data.get('guid_sprin', '')
        peserta_list = data.get('peserta', [])
        nama_file = data.get('nama_file', '-')
        
        if not guid_sprin: 
            return jsonify({'success': False, 'error': 'GUID SPRIN tidak boleh kosong'})
        if not peserta_list: 
            return jsonify({'success': False, 'error': 'Peserta tidak boleh kosong'})
        
        header = SprinHeader.query.get(guid_sprin)
        if not header: 
            return jsonify({'success': False, 'error': 'Header tidak ditemukan'})
        
        saved_count = 0
        for peserta in peserta_list:
            nip = peserta.get('nip', '')
            tgl_awal = peserta.get('tgl_awal', '')
            tgl_akhir = peserta.get('tgl_akhir', '')
            status_um = peserta.get('status_um', '0')
            
            if not nip or not tgl_awal or not tgl_akhir:
                continue
            
            transaksi_id = f"DLP_{nip}_{tgl_awal}_{tgl_akhir}"
            
            existing = DinasLuar.query.filter(
                DinasLuar.DINAS_TRANSAKSI_ID == transaksi_id
            ).first()
            
            tgl_awal_date = datetime.strptime(tgl_awal, '%Y-%m-%d')
            tgl_akhir_date = datetime.strptime(tgl_akhir, '%Y-%m-%d')
            
            if existing:
                existing.TGL_AWAL_DINAS_LUAR = tgl_awal_date
                existing.TGL_AKHIR_DINAS_LUAR = tgl_akhir_date
                existing.KETERANGAN_DINAS_LUAR = header.PERIHAL_SPRIN or ''
                existing.PENEMPATAN_DINAS_LUAR = header.PENEMPATAN or ''
                existing.STATUS_UM = int(status_um)
                existing.NAMA_FILE = nama_file
                existing.UPDATE_BY = 'admin'
                existing.UPDATE_DATE = datetime.now()
            else:
                new_dl = DinasLuar(
                    DINAS_TRANSAKSI_ID=transaksi_id,
                    GUID_SPRIN=guid_sprin,
                    NIP=nip,
                    TGL_AWAL_DINAS_LUAR=tgl_awal_date,
                    TGL_AKHIR_DINAS_LUAR=tgl_akhir_date,
                    KETERANGAN_DINAS_LUAR=header.PERIHAL_SPRIN or '',
                    PENEMPATAN_DINAS_LUAR=header.PENEMPATAN or '',
                    TRANSAKSI='DinasLuar',
                    PENDUKUNG='Y',
                    NO_SURAT=header.NO_SPRIN or '',
                    JENIS='PL',  # ✅ Pelatihan/Potensi
                    NAMA_FILE=nama_file,
                    TGL_AWAL_SURAT=header.TGL_AWAL_SPRIN,
                    TGL_AKHIR_SURAT=header.TGL_SPRIN,
                    TIPE='0',
                    STATUS_UM=int(status_um),
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(new_dl)
            saved_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'{saved_count} peserta berhasil disimpan'})
    except Exception as e:
        db.session.rollback()
        import traceback
        print("❌ ERROR in api_dinas_luar_pelatihan_save_peserta:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_dinas_luar_pelatihan_get():
    """API: Get data Dinas Luar Pelatihan by No Surat"""
    try:
        no_surat = request.args.get('no_surat', '')
        if not no_surat:
            return jsonify({'success': False, 'error': 'No Surat tidak boleh kosong'})
        
        dinas_list = db.session.query(
            DinasLuar, Pegawai
        ).outerjoin(
            Pegawai, DinasLuar.NIP == Pegawai.NIP
        ).filter(
            DinasLuar.NO_SURAT == no_surat,
            DinasLuar.TRANSAKSI == 'DinasLuar',
            DinasLuar.JENIS == 'PL'
        ).order_by(Pegawai.NAMA).all()
        
        if not dinas_list:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        first = dinas_list[0][0]
        header = {
            'guid_sprin': first.GUID_SPRIN,
            'no_surat': first.NO_SURAT,
            'tgl_awal_surat': first.TGL_AWAL_SURAT.strftime('%Y-%m-%d') if first.TGL_AWAL_SURAT else '',
            'tgl_akhir_surat': first.TGL_AKHIR_SURAT.strftime('%Y-%m-%d') if first.TGL_AKHIR_SURAT else '',
            'keterangan': first.KETERANGAN_DINAS_LUAR or '',
            'penempatan': first.PENEMPATAN_DINAS_LUAR or '',
            'status_um': str(first.STATUS_UM) if first.STATUS_UM is not None else '0',
            'nama_file': first.NAMA_FILE or '-'
        }
        
        peserta = []
        for dl, peg in dinas_list:
            status_um_name = 'Terpotong' if str(dl.STATUS_UM) == '1' else (
                'Tdk Terpotong Penempatan' if str(dl.STATUS_UM) == '2' else 'Tdk Terpotong'
            )
            peserta.append({
                'transaksi_id': dl.DINAS_TRANSAKSI_ID,
                'nip': dl.NIP,
                'nama': peg.NAMA if peg else '-',
                'tgl_awal': dl.TGL_AWAL_DINAS_LUAR.strftime('%Y-%m-%d') if dl.TGL_AWAL_DINAS_LUAR else '',
                'tgl_akhir': dl.TGL_AKHIR_DINAS_LUAR.strftime('%Y-%m-%d') if dl.TGL_AKHIR_DINAS_LUAR else '',
                'status_um': str(dl.STATUS_UM) if dl.STATUS_UM is not None else '0',
                'status_um_name': status_um_name
            })
        
        return jsonify({'success': True, 'data': {'header': header, 'peserta': peserta}})
    except Exception as e:
        import traceback
        print("❌ ERROR in api_dinas_luar_pelatihan_get:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_dinas_luar_pelatihan_delete():
    """API: Delete Dinas Luar Pelatihan"""
    try:
        data = request.get_json()
        guid_sprin = data.get('guid_sprin', '')
        if not guid_sprin:
            return jsonify({'success': False, 'error': 'GUID SPRIN tidak boleh kosong'})
        
        deleted = DinasLuar.query.filter(
            DinasLuar.GUID_SPRIN == guid_sprin,
            DinasLuar.JENIS == 'PL'
        ).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': f'{deleted} data berhasil dihapus'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


def kepegawaian_dinas_luar_umum():
    return render_template('pages/dashboard_1/Kepegawaian Dinas Luar Umum.html')


def api_dinas_luar_search_pegawai():
    """
    API: Pencarian pegawai untuk autocomplete.

    Standar HRIS Reborn:

        - Minimal 1 karakter
        - Hanya Pegawai Operasional
        - IS_KELUAR = N
        - Unit Kerja IS_USE = Y
        - Maksimal 15 kandidat
        - Pencarian sebagian nama
    """

    try:
        keyword = request.args.get('keyword', '').strip()

        if not keyword:
            return jsonify({
                'data': []
            })

        # ========================================================
        # AUTOCOMPLETE PEGAWAI TERPUSAT
        #
        # Business Rule:
        #
        #   app/utils/pegawaiHelper.py
        #
        # Jangan melakukan query Pegawai langsung di endpoint.
        # ========================================================

        pegawai_list = search_operational_pegawai(
            keyword,
            limit=15
        )

        return jsonify({
            'data': [
                {
                    'nip': pegawai.NIP,
                    'nama': pegawai.NAMA or ''
                }
                for pegawai in pegawai_list
            ]
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'data': []
        })


def api_sprin_header_save():
    """API: Simpan Header SPRIN saja"""
    try:
        data = request.get_json()
        
        no_surat = data.get('no_surat', '').strip()
        tgl_awal = data.get('tgl_awal_surat', '')
        tgl_akhir = data.get('tgl_akhir_surat', '')
        keterangan = data.get('keterangan', '')
        penempatan = data.get('penempatan', '')
        type_sprin_id = data.get('type_sprin_id', 'DL')  # ✅ Default 'DL', bisa 'OPR'
        
        if not no_surat: 
            return jsonify({'error': 'No. Surat tidak boleh kosong'})
        
        # Cek existing
        existing = SprinHeader.query.filter(
            SprinHeader.NO_SPRIN == no_surat,
            SprinHeader.TYPE_SPRIN_ID == type_sprin_id  # ✅ Filter by type juga
        ).first()
        
        if existing:
            return jsonify({
                'success': True, 
                'guid_sprin': existing.GUID_SPRIN, 
                'message': 'Header sudah ada'
            })
        
        # Generate GUID sesuai type
        prefix = 'DLU_' if type_sprin_id == 'DL' else 'DLO_'
        guid_sprin = f"{prefix}{datetime.now().strftime('%Y-%m')}_{str(uuid.uuid4())}"
        
        new_sprin = SprinHeader(
            GUID_SPRIN=guid_sprin,
            TYPE_SPRIN_ID=type_sprin_id,  # ✅ Bisa 'DL' atau 'OPR'
            NO_SPRIN=no_surat,
            TGL_SPRIN=datetime.strptime(tgl_awal, '%Y-%m-%d') if tgl_awal else None,
            TGL_AWAL_SPRIN=datetime.strptime(tgl_awal, '%Y-%m-%d') if tgl_awal else None,
            TGL_AKHIR_SPRIN=tgl_akhir,
            PERIHAL_SPRIN=keterangan,
            PENEMPATAN=penempatan,
            UPDATE_BY='admin',
            UPDATE_DATE=datetime.now()
        )
        db.session.add(new_sprin)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'guid_sprin': guid_sprin, 
            'message': 'Header berhasil disimpan'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})

def api_dinas_luar_save_peserta():
    """API: Simpan Peserta ke DINAS_LUAR (setelah header ada)"""
    try:
        data = request.get_json()
        guid_sprin = data.get('guid_sprin', '')
        peserta_list = data.get('peserta', [])
        
        if not guid_sprin: return jsonify({'error': 'GUID SPRIN tidak boleh kosong'})
        if not peserta_list: return jsonify({'error': 'Peserta tidak boleh kosong'})
        
        # Ambil data header
        header = SprinHeader.query.get(guid_sprin)
        if not header: return jsonify({'error': 'Header tidak ditemukan'})
        
        saved_count = 0
        for peserta in peserta_list:
            nip = peserta.get('nip', '')
            tgl_awal = peserta.get('tgl_awal', '')
            tgl_akhir = peserta.get('tgl_akhir', '')
            status_um = peserta.get('status_um', '0')
            
            if not nip or not tgl_awal or not tgl_akhir: continue
            
            transaksi_id = f"DLU_{nip}_{tgl_awal}_{tgl_akhir}"
            existing = DinasLuar.query.filter(DinasLuar.DINAS_TRANSAKSI_ID == transaksi_id).first()
            
            if existing:
                existing.TGL_AWAL_DINAS_LUAR = datetime.strptime(tgl_awal, '%Y-%m-%d')
                existing.TGL_AKHIR_DINAS_LUAR = datetime.strptime(tgl_akhir, '%Y-%m-%d')
                existing.STATUS_UM = int(status_um)
                existing.UPDATE_BY = 'admin'
                existing.UPDATE_DATE = datetime.now()
            else:
                new_dl = DinasLuar(
                    DINAS_TRANSAKSI_ID=transaksi_id, GUID_SPRIN=guid_sprin, NIP=nip,
                    TGL_AWAL_DINAS_LUAR=datetime.strptime(tgl_awal, '%Y-%m-%d'),
                    TGL_AKHIR_DINAS_LUAR=datetime.strptime(tgl_akhir, '%Y-%m-%d'),
                    KETERANGAN_DINAS_LUAR=header.PERIHAL_SPRIN or '',
                    PENEMPATAN_DINAS_LUAR=header.PENEMPATAN or '',
                    TRANSAKSI='DinasLuar', PENDUKUNG='Y',
                    NO_SURAT=header.NO_SPRIN or '', JENIS='DL', NAMA_FILE='-',
                    TGL_AWAL_SURAT=header.TGL_AWAL_SPRIN,
                    TGL_AKHIR_SURAT=header.TGL_SPRIN,
                    TIPE=0, STATUS_UM=int(status_um),
                    UPDATE_BY='admin', UPDATE_DATE=datetime.now()
                )
                db.session.add(new_dl)
            saved_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'{saved_count} peserta berhasil disimpan'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})

def api_dinas_luar_save():
    """API: Simpan Dinas Luar Umum"""
    try:
        data = request.get_json()
        
        no_surat = data.get('no_surat', '').strip()
        tgl_awal_surat = data.get('tgl_awal_surat', '')
        tgl_akhir_surat = data.get('tgl_akhir_surat', '')
        keterangan = data.get('keterangan', '')
        penempatan = data.get('penempatan', '')
        status_um = data.get('status_um', '0')
        peserta_list = data.get('peserta', [])
        guid_sprin = data.get('guid_sprin', '')
        is_update = data.get('is_update', False)
        save_header_only = data.get('save_header_only', False)  # ✅ Flag baru
        
        if not no_surat: return jsonify({'error': 'No. Surat tidak boleh kosong'})
        if not tgl_awal_surat or not tgl_akhir_surat: return jsonify({'error': 'Tanggal Surat tidak boleh kosong'})
        
        # STEP 1: Simpan/Cari SPRIN_HEADER dulu
        existing_sprin = SprinHeader.query.filter(SprinHeader.NO_SPRIN == no_surat).first()
        
        if existing_sprin:
            guid_sprin = existing_sprin.GUID_SPRIN
        else:
            guid_sprin = f"DLU_{datetime.now().strftime('%Y-%m')}_{str(uuid.uuid4())}"
            new_sprin = SprinHeader(
                GUID_SPRIN=guid_sprin, TYPE_SPRIN_ID='DL', NO_SPRIN=no_surat,
                TGL_SPRIN=datetime.strptime(tgl_awal_surat, '%Y-%m-%d'),
                TGL_AWAL_SPRIN=datetime.strptime(tgl_awal_surat, '%Y-%m-%d'),
                TGL_AKHIR_SPRIN=tgl_akhir_surat, PERIHAL_SPRIN=keterangan,
                PENEMPATAN=penempatan, STATUS_UM=int(status_um),
                UPDATE_BY='admin', UPDATE_DATE=datetime.now()
            )
            db.session.add(new_sprin)
            db.session.flush()
        
        # ✅ Jika hanya simpan header, commit dan return
        if save_header_only:
            db.session.commit()
            return jsonify({'success': True, 'message': 'Header berhasil disimpan', 'guid_sprin': guid_sprin})
        
        # STEP 2: Simpan peserta ke DINAS_LUAR
        if not peserta_list: return jsonify({'error': 'Peserta tidak boleh kosong'})
        
        saved_count = 0
        for peserta in peserta_list:
            nip = peserta.get('nip', '')
            tgl_awal_dl = peserta.get('tgl_awal', '')
            tgl_akhir_dl = peserta.get('tgl_akhir', '')
            status_um_peserta = peserta.get('status_um', status_um)
            
            if not nip or not tgl_awal_dl or not tgl_akhir_dl: continue
            
            transaksi_id = f"DLU_{nip}_{tgl_awal_dl}_{tgl_akhir_dl}"
            existing = DinasLuar.query.filter(DinasLuar.DINAS_TRANSAKSI_ID == transaksi_id).first()
            
            if existing:
                existing.TGL_AWAL_DINAS_LUAR = datetime.strptime(tgl_awal_dl, '%Y-%m-%d')
                existing.TGL_AKHIR_DINAS_LUAR = datetime.strptime(tgl_akhir_dl, '%Y-%m-%d')
                existing.KETERANGAN_DINAS_LUAR = keterangan
                existing.PENEMPATAN_DINAS_LUAR = penempatan
                existing.STATUS_UM = int(status_um_peserta)
                existing.UPDATE_BY = 'admin'
                existing.UPDATE_DATE = datetime.now()
            else:
                new_dl = DinasLuar(
                    DINAS_TRANSAKSI_ID=transaksi_id, GUID_SPRIN=guid_sprin, NIP=nip,
                    TGL_AWAL_DINAS_LUAR=datetime.strptime(tgl_awal_dl, '%Y-%m-%d'),
                    TGL_AKHIR_DINAS_LUAR=datetime.strptime(tgl_akhir_dl, '%Y-%m-%d'),
                    KETERANGAN_DINAS_LUAR=keterangan, PENEMPATAN_DINAS_LUAR=penempatan,
                    TRANSAKSI='DinasLuar', PENDUKUNG='Y', NO_SURAT=no_surat,
                    JENIS='DL', NAMA_FILE='-',
                    TGL_AWAL_SURAT=datetime.strptime(tgl_awal_surat, '%Y-%m-%d'),
                    TGL_AKHIR_SURAT=datetime.strptime(tgl_akhir_surat, '%Y-%m-%d'),
                    TIPE=0, STATUS_UM=int(status_um_peserta),
                    UPDATE_BY='admin', UPDATE_DATE=datetime.now()
                )
                db.session.add(new_dl)
            saved_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'{saved_count} peserta berhasil disimpan', 'guid_sprin': guid_sprin})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_dinas_luar_get():
    """API: Get data Dinas Luar by No Surat"""
    try:
        no_surat = request.args.get('no_surat', '')
        if not no_surat: return jsonify({'error': 'No Surat tidak boleh kosong'})
        
        dinas_list = DinasLuar.query.filter(
            DinasLuar.NO_SURAT == no_surat,
            DinasLuar.TRANSAKSI == 'DinasLuar',
            DinasLuar.JENIS == 'DL'
        ).all()
        
        if not dinas_list: return jsonify({'error': 'Data tidak ditemukan'})
        
        first = dinas_list[0]
        header = {
            'guid_sprin': first.GUID_SPRIN, 'no_surat': first.NO_SURAT,
            'tgl_awal_surat': first.TGL_AWAL_SURAT.strftime('%Y-%m-%d') if first.TGL_AWAL_SURAT else '',
            'tgl_akhir_surat': first.TGL_AKHIR_SURAT.strftime('%Y-%m-%d') if first.TGL_AKHIR_SURAT else '',
            'keterangan': first.KETERANGAN_DINAS_LUAR or '', 'penempatan': first.PENEMPATAN_DINAS_LUAR or '',
            'status_um': str(first.STATUS_UM) if first.STATUS_UM else '0',
        }
        
        peserta = []
        for dl in dinas_list:
            peg = Pegawai.query.filter(Pegawai.NIP == dl.NIP).first()
            peserta.append({
                'transaksi_id': dl.DINAS_TRANSAKSI_ID, 'nip': dl.NIP,
                'nama': peg.NAMA if peg else '-',
                'tgl_awal': dl.TGL_AWAL_DINAS_LUAR.strftime('%Y-%m-%d') if dl.TGL_AWAL_DINAS_LUAR else '',
                'tgl_akhir': dl.TGL_AKHIR_DINAS_LUAR.strftime('%Y-%m-%d') if dl.TGL_AKHIR_DINAS_LUAR else '',
                'status_um': str(dl.STATUS_UM) if dl.STATUS_UM else '0',
            })
        
        return jsonify({'success': True, 'data': {'header': header, 'peserta': peserta}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_dinas_luar_delete():
    """API: Delete Dinas Luar"""
    try:
        data = request.get_json()
        guid_sprin = data.get('guid_sprin', '')
        transaksi_id = data.get('transaksi_id', '')
        
        if transaksi_id:
            DinasLuar.query.filter(DinasLuar.DINAS_TRANSAKSI_ID == transaksi_id).delete()
        elif guid_sprin:
            DinasLuar.query.filter(DinasLuar.GUID_SPRIN == guid_sprin).delete()
        else:
            return jsonify({'error': 'Parameter tidak lengkap'})
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Data berhasil dihapus'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


def kepegawaian_mutasi_penempatan_pegawai():
    """
    Render halaman Kepegawaian Mutasi Penempatan Pegawai.
    """
    return render_template('pages/dashboard_1/Kepegawaian Mutasi Penempatan Pegawai.html')

def api_mutasi_save():
    """
    API: Simpan Data Mutasi Penempatan Pegawai
    """
    try:
        data = request.get_json()
        print("📥 Data Mutasi:", data)
        
        no_sk = data.get('no_sk', '').strip()
        tgl_mutasi = data.get('tgl_mutasi', '')
        unit_kerja_id = data.get('unit_kerja_id', '')
        keterangan = data.get('keterangan', '')
        peserta_list = data.get('peserta', [])
        is_edit = data.get('is_edit', False)
        
        if not no_sk:
            return jsonify({'success': False, 'error': 'No. SK tidak boleh kosong'})
        if not tgl_mutasi:
            return jsonify({'success': False, 'error': 'Tanggal Mutasi tidak boleh kosong'})
        if not unit_kerja_id:
            return jsonify({'success': False, 'error': 'Unit Kerja tujuan tidak boleh kosong'})
        if not peserta_list:
            return jsonify({'success': False, 'error': 'Peserta tidak boleh kosong'})
        
        # Cek duplikasi No SK (hanya untuk insert baru)
        if not is_edit:
            existing = PegMutasiUnit.query.filter(
                PegMutasiUnit.NO_SK == no_sk
            ).first()
            if existing:
                return jsonify({
                    'success': False, 
                    'error': 'No SK sudah ter-record di database'
                })
        
        # Hapus data existing by No SK
        PegMutasiUnit.query.filter(
            PegMutasiUnit.NO_SK == no_sk
        ).delete()
        db.session.flush()
        
        tgl_mutasi_date = datetime.strptime(tgl_mutasi, '%Y-%m-%d')
        
        # ✅ Cari TRAKSAKSI_ID terakhir dan tambahkan 1
        last_trx = db.session.query(
            db.func.max(PegMutasiUnit.TRAKSAKSI_ID)
        ).scalar() or 0
        
        saved_count = 0
        for peserta in peserta_list:
            nip = peserta.get('nip', '')
            if not nip:
                continue
            
            last_trx += 1
            
            new_mutasi = PegMutasiUnit(
                TRAKSAKSI_ID=last_trx,  # ✅ Set manual karena composite key
                NIP=nip,
                TGL_MUTASI=tgl_mutasi_date,
                UNIT_KERJA=str(unit_kerja_id),
                NO_SK=no_sk,
                KETERANGAN=keterangan,
                UPDATE_BY='admin',
                UPDATE_DATE=datetime.now()
            )
            db.session.add(new_mutasi)
            saved_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{saved_count} pegawai berhasil dimutasi',
            'no_sk': no_sk
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print("❌ ERROR in api_mutasi_save:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

def api_mutasi_get():
    """API: Get data Mutasi by No SK"""
    try:
        no_sk = request.args.get('no_sk', '')
        if not no_sk:
            return jsonify({'success': False, 'error': 'No SK tidak boleh kosong'})
        
        mutasi_list = db.session.query(
            PegMutasiUnit, Pegawai
        ).join(
            Pegawai, PegMutasiUnit.NIP == Pegawai.NIP
        ).filter(
            PegMutasiUnit.NO_SK == no_sk
        ).order_by(Pegawai.NAMA).all()
        
        if not mutasi_list:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        first = mutasi_list[0]
        
        header = {
            'no_sk': first[0].NO_SK,
            'tgl_mutasi': first[0].TGL_MUTASI.strftime('%Y-%m-%d') if first[0].TGL_MUTASI else '',
            'unit_kerja_id': first[0].UNIT_KERJA or '',
            'keterangan': first[0].KETERANGAN or '',
        }
        
        peserta = []
        for mutasi, peg in mutasi_list:
            peserta.append({
                'nip': mutasi.NIP,
                'nama': peg.NAMA if peg else '-',
            })
        
        return jsonify({
            'success': True,
            'data': {
                'header': header,
                'peserta': peserta
            }
        })
        
    except Exception as e:
        import traceback
        print("❌ ERROR in api_mutasi_get:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_mutasi_delete():
    """API: Delete data Mutasi by No SK"""
    try:
        data = request.get_json()
        no_sk = data.get('no_sk', '')
        
        if not no_sk:
            return jsonify({'success': False, 'error': 'No SK tidak boleh kosong'})
        
        deleted = PegMutasiUnit.query.filter(
            PegMutasiUnit.NO_SK == no_sk
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{deleted} data mutasi berhasil dihapus'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


def api_mutasi_cari():
    """API: Cari data Mutasi"""
    try:
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        query = db.session.query(
            PegMutasiUnit, Pegawai
        ).join(
            Pegawai, PegMutasiUnit.NIP == Pegawai.NIP
        )
        
        if filter_field1 and filter_value1:
            if filter_field1 == 'NIP':
                query = query.filter(Pegawai.NIP.ilike(f'%{filter_value1}%'))
            elif filter_field1 == 'Nama':
                query = query.filter(Pegawai.NAMA.ilike(f'%{filter_value1}%'))
            elif filter_field1 == 'NoSK':
                query = query.filter(PegMutasiUnit.NO_SK.ilike(f'%{filter_value1}%'))
        
        if filter_field2 and filter_value2:
            if filter_field2 == 'NIP':
                query = query.filter(Pegawai.NIP.ilike(f'%{filter_value2}%'))
            elif filter_field2 == 'Nama':
                query = query.filter(Pegawai.NAMA.ilike(f'%{filter_value2}%'))
            elif filter_field2 == 'NoSK':
                query = query.filter(PegMutasiUnit.NO_SK.ilike(f'%{filter_value2}%'))
        
        results = query.order_by(
            PegMutasiUnit.NO_SK,
            Pegawai.NAMA
        ).limit(500).all()
        
        data = []
        for i, (mutasi, peg) in enumerate(results, 1):
            data.append({
                'no': i,
                'no_sk': mutasi.NO_SK,
                'nip': mutasi.NIP,
                'nama': peg.NAMA if peg else '-',
                'tgl_sk': mutasi.TGL_MUTASI.strftime('%d-%b-%Y') if mutasi.TGL_MUTASI else '-',
                'unit_kerja': mutasi.UNIT_KERJA or '-',
                'keterangan': mutasi.KETERANGAN or '-',
                'update_by': mutasi.UPDATE_BY or 'admin',
                'update_date': mutasi.UPDATE_DATE.strftime('%d-%b-%Y') if mutasi.UPDATE_DATE else '-'
            })
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })
        
    except Exception as e:
        import traceback
        print("❌ ERROR in api_mutasi_cari:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'data': []})


def api_mutasi_get_filter_fields():
    """API: Get list field untuk filter dropdown Mutasi"""
    try:
        fields = [
            {'field_id': 'NIP', 'field_name': 'NIP'},
            {'field_id': 'Nama', 'field_name': 'Nama Pegawai'},
            {'field_id': 'NoSK', 'field_name': 'No. SK'},
        ]
        return jsonify({'success': True, 'data': fields})
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})


def kepegawaian_pegawai_cuti():
    """
    Render halaman Kepegawaian Pegawai Cuti.
    """
    return render_template('pages/dashboard_1/Kepegawaian Pegawai Cuti.html')

def api_cuti_save():
    """
    API: Simpan Data Cuti Pegawai
    Mirip dengan LBSave_Click di VB.NET
    """
    try:
        data = request.get_json()
        print("📥 Data Cuti:", data)
        
        nip = data.get('nip', '').strip()
        tgl_awal = data.get('tgl_awal', '')
        tgl_akhir = data.get('tgl_akhir', '')
        keterangan = data.get('keterangan', '')
        jenis_cuti = data.get('jenis_cuti', '')
        transaksi_id_existing = data.get('transaksi_id', '')
        
        if not nip:
            return jsonify({'success': False, 'error': 'Pegawai tidak boleh kosong'})
        if not tgl_awal or not tgl_akhir:
            return jsonify({'success': False, 'error': 'Tanggal tidak boleh kosong'})
        if not jenis_cuti:
            return jsonify({'success': False, 'error': 'Jenis Cuti tidak boleh kosong'})
        
        # ====================================================
        # HRIS REBORN:
        # Absensi tidak menyimpan NIP.
        # Relasi Pegawai -> Absensi menggunakan FingerID.
        # ====================================================
        pegawai = Pegawai.query.filter(
            Pegawai.NIP == nip
        ).first()

        if not pegawai:
            return jsonify({
                'success': False,
                'error': f'Pegawai dengan NIP {nip} tidak ditemukan'
            })

        # ====================================================
        # HRIS REBORN BUSINESS RULE — SINGLE SOURCE OF TRUTH
        #
        # Pegawai aktif untuk kebutuhan operasional HRIS
        # harus melewati satu pintu:
        #
        #     is_operational_pegawai()
        #
        # Rule:
        #
        #     Pegawai.IS_KELUAR = 'N'
        #     AND
        #     MfUnitKerja.IS_USE = 'Y'
        #
        # Jangan membuat definisi status aktif sendiri
        # di modul Cuti.
        # ====================================================
        if not is_operational_pegawai(pegawai):
            return jsonify({
                'success': False,
                'error': (
                    f'Pegawai dengan NIP {nip} tidak termasuk '
                    f'Pegawai Operasional HRIS'
                )
            })

        if pegawai.FINGER_ID is None:
            return jsonify({
                'success': False,
                'error': f'Pegawai dengan NIP {nip} belum memiliki FingerID'
            })

        finger_id = pegawai.FINGER_ID

        # Generate atau gunakan TransaksiID existing
        if transaksi_id_existing:
            transaksi_id = transaksi_id_existing
        else:
            transaksi_id = f"CUTI_{nip}_{tgl_awal}_{tgl_akhir}"
        
        # Delete existing data dulu
        DinasLuar.query.filter(
            DinasLuar.TRANSAKSI_ID == transaksi_id
        ).delete()
        
        Absensi.query.filter(
            Absensi.TRAKSAKSI_ID_FROM == transaksi_id
        ).delete()
        db.session.flush()
        
        # ====================================================
        # CUTI TIDAK MEMBUTUHKAN SPRIN_HEADER
        #
        # Data Cuti HRIS Reborn disimpan langsung pada:
        #
        #     DINAS_LUAR
        #     ABSENSI
        #
        # Data Cuti existing menggunakan GUIDSprin kosong ('').
        # Jangan membuat dummy SPRIN_HEADER.
        # ====================================================
        # Cek kalender
        tgl_awal_date = datetime.strptime(tgl_awal, '%Y-%m-%d')
        tgl_akhir_date = datetime.strptime(tgl_akhir, '%Y-%m-%d')
        
        kalender_count = MfKalender.query.filter(
            MfKalender.TGL_KERJA >= tgl_awal_date,
            MfKalender.TGL_KERJA <= tgl_akhir_date
        ).count()
        
        expected_days = (tgl_akhir_date - tgl_awal_date).days + 1
        if kalender_count < expected_days:
            return jsonify({
                'success': False, 
                'error': 'Master Kalender ada yang belum tercreate sesuai range tanggal'
            })
        
        # ✅ Simpan ke DINAS_LUAR dengan GUID_SPRIN dummy
        new_dl = DinasLuar(
            TRANSAKSI_ID=transaksi_id,
            GUID_SPRIN='',
            FINGER_ID=finger_id,
            TGL_AWAL_DINAS_LUAR=tgl_awal_date,
            TGL_AKHIR_DINAS_LUAR=tgl_akhir_date,
            KETERANGAN_DINAS_LUAR=keterangan,
            PENEMPATAN_DINAS_LUAR=jenis_cuti,
            TRANSAKSI='Cuti',
            PENDUKUNG='Y',
            NO_SURAT='-',
            JENIS='CUTI',
            NAMA_FILE='-',
            TGL_AWAL_SURAT=tgl_awal_date,
            TGL_AKHIR_SURAT=tgl_akhir_date,
            TIPE='0',
            STATUS_UM=0,
            UPDATE_BY='admin',
            UPDATE_DATE=datetime.now()
        )
        db.session.add(new_dl)
        
        # Ambil data potongan
        potongan = MfPot.query.filter(
            MfPot.KATEGORI == 'CUTI',
            MfPot.TINGKAT == jenis_cuti,
            MfPot.TGL_MULAI <= tgl_akhir_date
        ).order_by(MfPot.TGL_MULAI.desc()).first()
        
        persen_pot = potongan.PERSEN_POT if potongan else 0
        
        # Loop insert absensi per hari
        current_date = tgl_awal_date
        while current_date <= tgl_akhir_date:
            kalender = MfKalender.query.filter(
                MfKalender.TGL_KERJA == current_date
            ).first()
            
            is_libur = False
            if kalender:
                is_libur = kalender.IS_LIBUR == 'Y'
            else:
                if current_date.weekday() >= 5:
                    is_libur = True
            
            if not is_libur:
                Absensi.query.filter(
                    Absensi.FINGER_ID == finger_id,
                    Absensi.TGL_KERJA == current_date
                ).delete()
                
                new_absensi = Absensi(
                    FINGER_ID=finger_id,
                    TGL_KERJA=current_date,
                    TGL_JAM_IN=current_date,
                    TGL_JAM_OUT=current_date,
                    KET_IN=keterangan[:100] if keterangan else 'Cuti',
                    KET_OUT=keterangan[:100] if keterangan else 'Cuti',
                    TRANSAKSI_IN='Cuti',
                    TRANSAKSI_OUT='Cuti',
                    UPDATE_IN_BY='admin',
                    UPDATE_OUT_BY='admin',
                    TINGKAT_TLM=jenis_cuti,
                    TOTAL_TLM=0,
                    TOTAL_PSW=0,
                    TINGKAT_PSW=jenis_cuti,
                    IS_INVALID='Y',
                    IS_OUTVALID='Y',
                    AWAL_TLM=0,
                    PERSEN_POT_TLM=persen_pot,
                    PERSEN_POT_PSW=0,
                    TGL_JAM_BAKU_IN=current_date,
                    TGL_JAM_BAKU_OUT=current_date,
                    TRAKSAKSI_ID_FROM=transaksi_id,
                    PENDUKUNG_IN='Y',
                    PENDUKUNG_OUT='Y',
                    STATUS_UM=0
                )
                db.session.add(new_absensi)
            
            current_date += timedelta(days=1)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Data Cuti berhasil disimpan',
            'transaksi_id': transaksi_id
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print("❌ ERROR in api_cuti_save:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_cuti_get():
    """API: Get data Cuti by TransaksiID"""
    try:
        transaksi_id = request.args.get('transaksi_id', '')
        if not transaksi_id:
            return jsonify({'success': False, 'error': 'Transaksi ID tidak boleh kosong'})
        
        dinas = DinasLuar.query.filter(
            DinasLuar.TRANSAKSI_ID == transaksi_id,
            DinasLuar.TRANSAKSI == 'Cuti'
        ).first()
        
        if not dinas:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        # Ambil data pegawai melalui FingerID.
        # DinasLuar tidak menyimpan NIP pada model HRIS Reborn.
        pegawai = Pegawai.query.filter(
            Pegawai.FINGER_ID == dinas.FINGER_ID
        ).first()
        
        if not pegawai:
            return jsonify({
                'success': False,
                'error': 'Data pegawai tidak ditemukan'
            })

        # ====================================================
        # HRIS REBORN BUSINESS RULE — SINGLE SOURCE OF TRUTH
        #
        # Pegawai aktif untuk kebutuhan operasional HRIS
        # harus melewati satu pintu:
        #
        #     is_operational_pegawai()
        #
        # Rule:
        #
        #     Pegawai.IS_KELUAR = 'N'
        #     AND
        #     MfUnitKerja.IS_USE = 'Y'
        #
        # Jangan membuat definisi status aktif sendiri
        # di modul Cuti.
        # ====================================================
        if not is_operational_pegawai(pegawai):
            return jsonify({
                'success': False,
                'error': 'Pegawai tidak termasuk Pegawai Operasional HRIS'
            })

        # Ambil nama potongan
        potongan = MfPot.query.filter(
            MfPot.TINGKAT == dinas.PENEMPATAN_DINAS_LUAR,
            MfPot.KATEGORI == 'CUTI'
        ).first()
        
        result = {
            'transaksi_id': dinas.TRANSAKSI_ID,
            'nip': pegawai.NIP,
            'nama': pegawai.NAMA if pegawai else '-',
            'tgl_awal': dinas.TGL_AWAL_DINAS_LUAR.strftime('%Y-%m-%d') if dinas.TGL_AWAL_DINAS_LUAR else '',
            'tgl_akhir': dinas.TGL_AKHIR_DINAS_LUAR.strftime('%Y-%m-%d') if dinas.TGL_AKHIR_DINAS_LUAR else '',
            'keterangan': dinas.KETERANGAN_DINAS_LUAR or '',
            'jenis_cuti': dinas.PENEMPATAN_DINAS_LUAR or '',
            'jenis_cuti_nama': potongan.NAMA_POT if potongan else dinas.PENEMPATAN_DINAS_LUAR,
            'update_by': dinas.UPDATE_BY or '',
            'update_date': dinas.UPDATE_DATE.strftime('%d-%b-%Y %H:%M') if dinas.UPDATE_DATE else ''
        }
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        import traceback
        print("❌ ERROR in api_cuti_get:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_cuti_delete():
    """API: Delete data Cuti"""
    try:
        data = request.get_json()
        transaksi_id = data.get('transaksi_id', '')
        
        if not transaksi_id:
            return jsonify({'success': False, 'error': 'Transaksi ID tidak boleh kosong'})
        
        # Delete dari ABSENSI dulu (pakai nama kolom yang benar)
        Absensi.query.filter(
            Absensi.TRAKSAKSI_ID_FROM == transaksi_id  # ✅ TRAKSAKSI
        ).delete()
        
        # Delete dari DINAS_LUAR
        DinasLuar.query.filter(
            DinasLuar.TRANSAKSI_ID == transaksi_id,
            DinasLuar.TRANSAKSI == 'Cuti'
        ).delete()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data Cuti berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_cuti_cari():
    """API: Cari data Cuti"""
    try:
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        # ====================================================
        # BASE QUERY
        # HRIS REBORN BUSINESS RULE:
        # Hanya pegawai dari Unit Kerja yang masih aktif
        # yang boleh muncul dalam daftar Cuti.
        #
        # Data historis Unit Kerja nonaktif tetap berada
        # di database, tetapi tidak ditampilkan sebagai
        # data aktif HRIS Reborn.
        # ====================================================
        # ====================================================
        # SINGLE SOURCE OF TRUTH — PEGAWAI OPERASIONAL
        #
        # Populasi pegawai TIDAK boleh didefinisikan ulang
        # di controller.
        #
        # Gunakan:
        #
        #     get_operational_pegawai_query()
        #
        # Business Rule terpusat di:
        #
        #     app/utils/pegawaiHelper.py
        #
        # Rule:
        #
        #     Pegawai.IS_KELUAR = 'N'
        #     AND
        #     MfUnitKerja.IS_USE = 'Y'
        #
        # Setelah populasi pegawai diperoleh dari helper,
        # query dilanjutkan ke transaksi DINAS_LUAR.
        # ====================================================
        query = (
            get_operational_pegawai_query()
            .with_entities(
                DinasLuar,
                Pegawai,
                MfPot
            )
            .join(
                DinasLuar,
                DinasLuar.FINGER_ID == Pegawai.FINGER_ID
            )
            .outerjoin(
                MfPot,
                db.and_(
                    DinasLuar.PENEMPATAN_DINAS_LUAR == MfPot.TINGKAT,
                    MfPot.KATEGORI == 'CUTI'
                )
            )
            .filter(
                DinasLuar.TRANSAKSI == 'Cuti'
            )
        )
        
        # Filter
        field_mapping = {
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'KeteranganCuti': DinasLuar.KETERANGAN_DINAS_LUAR,
            'JenisCuti': MfPot.NAMA_POT,
        }
        
        if filter_field1 and filter_value1:
            field = field_mapping.get(filter_field1)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value1}%'))
        
        if filter_field2 and filter_value2:
            field = field_mapping.get(filter_field2)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value2}%'))
        
        results = query.order_by(DinasLuar.UPDATE_DATE.desc()).limit(500).all()
        
        data = []
        for i, (dl, peg, pot) in enumerate(results, 1):
            data.append({
                'no': i,
                'transaksi_id': dl.TRANSAKSI_ID,
                'nip': peg.NIP,
                'nama': peg.NAMA if peg else '-',
                'tgl_awal': dl.TGL_AWAL_DINAS_LUAR.strftime('%d-%b-%Y') if dl.TGL_AWAL_DINAS_LUAR else '-',
                'tgl_akhir': dl.TGL_AKHIR_DINAS_LUAR.strftime('%d-%b-%Y') if dl.TGL_AKHIR_DINAS_LUAR else '-',
                'keterangan': dl.KETERANGAN_DINAS_LUAR or '-',
                'jenis_cuti': pot.NAMA_POT if pot else dl.PENEMPATAN_DINAS_LUAR,
                'update_by': f"{dl.UPDATE_BY} - {dl.UPDATE_DATE.strftime('%d-%b-%Y')}" if dl.UPDATE_DATE else '-'
            })
        
        return jsonify({'success': True, 'data': data, 'total': len(data)})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'data': []})



def kepegawaian_cari_pegawai_cuti():
    """
    Render halaman pencarian Pegawai Cuti.
    """
    return render_template(
        'pages/dashboard_1/Kepegawaian Cari Pegawai Cuti.html'
    )


def api_cuti_get_jenis():
    """API: Get list Jenis Cuti dari MfPot"""
    try:
        potongan_list = MfPot.query.filter(
            MfPot.KATEGORI == 'CUTI'
        ).order_by(MfPot.TINGKAT).all()
        
        data = [{'tingkat': p.TINGKAT, 'nama': p.NAMA_POT, 'persen': p.PERSEN_POT} for p in potongan_list]
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []})


def api_cuti_get_filter_fields():
    """API: Get list field untuk filter dropdown Cuti"""
    try:
        fields = [
            {'field_id': 'NIP', 'field_name': 'NIP'},
            {'field_id': 'Nama', 'field_name': 'Nama Pegawai'},
            {'field_id': 'KeteranganCuti', 'field_name': 'Keterangan'},
            {'field_id': 'JenisCuti', 'field_name': 'Jenis Cuti'},
        ]
        return jsonify({'success': True, 'data': fields})
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})


def kepegawaian_pegawai_sakit():
    """
    Render halaman Kepegawaian Pegawai Sakit.
    """
    return render_template('pages/dashboard_1/Kepegawaian Pegawai Sakit.html')


def kepegawaian_pegawai_tidak_hadir():
    """
    Render halaman Kepegawaian Pegawai Tidak Hadir.
    """
    return render_template('pages/dashboard_1/Kepegawaian Pegawai Tidak Hadir.html')


def kepegawaian_update_pendukung():
    """
    Render halaman Kepegawaian Update Pendukung.
    """
    return render_template('pages/dashboard_1/Kepegawaian Update Pendukung.html')

def api_update_pendukung_search():
    """
    API: Cari data untuk Update Pendukung
    Mirip dengan BtnRefresh_Click di VB.NET
    """
    try:
        periode = request.args.get('periode', '')  # Format: YYYY-MM
        filter_field = request.args.get('filter_field', '')
        filter_value = request.args.get('filter_value', '')
        tingkatan = request.args.get('tingkatan', '')
        
        if not periode or len(periode) < 7:
            return jsonify({'success': False, 'error': 'Periode tidak boleh kosong'})
        
        tahun = int(periode[:4])
        bulan = int(periode[5:7])
        
        # Query 1: Absensi dengan TLM (keterlambatan) - BUKAN DinasLuar/Cuti/Sakit/Alpa
        q1 = db.session.query(
            Absensi.TRANSAKSI_IN.label('Transac'),
            Absensi.TGL_KERJA.label('TglKerja'),
            Absensi.PENDUKUNG_IN.label('pendukung'),
            Absensi.TINGKAT_TLM.label('tingkat'),
            Pegawai.NIP.label('FingerID'),
            Pegawai.NAMA.label('Nama'),
            Absensi.KET_IN.label('ket'),
            db.literal('IN').label('Transaksi'),
            MfGolongan.URUT_GOL.label('Urutan'),
            Absensi.TRAKSAKSI_ID_FROM.label('TransaksiIDFrom')
        ).join(
            Pegawai, Absensi.NIP == Pegawai.NIP
        ).outerjoin(
            MfGolongan, Pegawai.GOL_ID == MfGolongan.GOL_ID
        ).filter(
            db.extract('year', Absensi.TGL_KERJA) == tahun,
            db.extract('month', Absensi.TGL_KERJA) == bulan,
            ~Absensi.TRANSAKSI_IN.in_(['DinasLuar', 'Cuti', 'sakit', 'Alpa']),
            Absensi.TINGKAT_TLM != '',
            Absensi.TINGKAT_TLM.isnot(None)
        )
        
        # Query 2: Absensi Alpa/Sakit
        q2 = db.session.query(
            Absensi.TRANSAKSI_IN.label('Transac'),
            Absensi.TGL_KERJA.label('TglKerja'),
            Absensi.PENDUKUNG_IN.label('pendukung'),
            db.case(
                (Absensi.TRANSAKSI_IN == 'Alpa', 'Ijin'),
                else_=Absensi.TRANSAKSI_IN
            ).label('tingkat'),
            Pegawai.NIP.label('FingerID'),
            Pegawai.NAMA.label('Nama'),
            Absensi.KET_IN.label('ket'),
            db.literal('IN').label('Transaksi'),
            MfGolongan.URUT_GOL.label('Urutan'),
            Absensi.TRAKSAKSI_ID_FROM.label('TransaksiIDFrom')
        ).join(
            Pegawai, Absensi.NIP == Pegawai.NIP
        ).outerjoin(
            MfGolongan, Pegawai.GOL_ID == MfGolongan.GOL_ID
        ).filter(
            db.extract('year', Absensi.TGL_KERJA) == tahun,
            db.extract('month', Absensi.TGL_KERJA) == bulan,
            Absensi.TRANSAKSI_IN.in_(['Alpa', 'sakit']),
            Absensi.TINGKAT_TLM != '',
            Absensi.TINGKAT_TLM.isnot(None)
        )
        
        # Query 3: Absensi dengan PSW (pulang sebelum waktunya)
        q3 = db.session.query(
            Absensi.TRANSAKSI_OUT.label('Transac'),
            Absensi.TGL_KERJA.label('TglKerja'),
            Absensi.PENDUKUNG_OUT.label('pendukung'),
            Absensi.TINGKAT_PSW.label('tingkat'),
            Pegawai.NIP.label('FingerID'),
            Pegawai.NAMA.label('Nama'),
            Absensi.KET_OUT.label('ket'),
            db.literal('OUT').label('Transaksi'),
            MfGolongan.URUT_GOL.label('Urutan'),
            Absensi.TRAKSAKSI_ID_FROM.label('TransaksiIDFrom')
        ).join(
            Pegawai, Absensi.NIP == Pegawai.NIP
        ).outerjoin(
            MfGolongan, Pegawai.GOL_ID == MfGolongan.GOL_ID
        ).filter(
            db.extract('year', Absensi.TGL_KERJA) == tahun,
            db.extract('month', Absensi.TGL_KERJA) == bulan,
            ~Absensi.TRANSAKSI_IN.in_(['DinasLuar', 'Cuti', 'sakit', 'Alpa']),
            Absensi.TINGKAT_PSW != '',
            Absensi.TINGKAT_PSW.isnot(None)
        )
        
        # Filter tambahan
        if filter_field and filter_value:
            if filter_field == 'NIP':
                q1 = q1.filter(Pegawai.NIP.ilike(f'%{filter_value}%'))
                q2 = q2.filter(Pegawai.NIP.ilike(f'%{filter_value}%'))
                q3 = q3.filter(Pegawai.NIP.ilike(f'%{filter_value}%'))
            elif filter_field == 'Nama':
                q1 = q1.filter(Pegawai.NAMA.ilike(f'%{filter_value}%'))
                q2 = q2.filter(Pegawai.NAMA.ilike(f'%{filter_value}%'))
                q3 = q3.filter(Pegawai.NAMA.ilike(f'%{filter_value}%'))
        
        if tingkatan:
            q1 = q1.filter(Absensi.TINGKAT_TLM == tingkatan)
            q3 = q3.filter(Absensi.TINGKAT_PSW == tingkatan)
        
        # Union all queries - lalu convert ke list biasa (hindari subquery)
        results_q1 = q1.all()
        results_q2 = q2.all()
        results_q3 = q3.all()
        
        # Gabungkan semua hasil
        all_results = list(results_q1) + list(results_q2) + list(results_q3)
        
        # Format dan urutkan
        formatted = []
        for row in all_results:
            formatted.append({
                'tgl_kerja': row.TglKerja,
                'pendukung': row.pendukung,
                'tingkat': row.tingkat,
                'nip': row.FingerID,
                'nama': row.Nama,
                'keterangan': row.ket,
                'transaksi': row.Transaksi,
                'transac': row.Transac,
                'transaksi_id_from': row.TransaksiIDFrom,
                'urutan': row.Urutan or 999,
            })
        
        # Urutkan: by TglKerja, Urutan, Nama
        formatted.sort(key=lambda x: (x['tgl_kerja'] or '', x['urutan'], x['nama'] or ''))
        
        # Format final
        data = []
        for i, item in enumerate(formatted, 1):
            data.append({
                'no': i,
                'tgl_kerja': item['tgl_kerja'].strftime('%d-%b-%Y') if item['tgl_kerja'] else '-',
                'pendukung': item['pendukung'] == 'Y' if item['pendukung'] else False,
                'tingkat': item['tingkat'] or '',
                'nip': item['nip'] or '',
                'nama': item['nama'] or '',
                'keterangan': item['keterangan'] or '',
                'transaksi': item['transaksi'] or '',
                'transac': item['transac'] or '',
                'transaksi_id_from': item['transaksi_id_from'] or '',
            })
        
        # Batasi 1000 data
        data = data[:1000]
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })
        
    except Exception as e:
        import traceback
        print("❌ ERROR in api_update_pendukung_search:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'data': []})


def api_update_pendukung_save():
    """
    API: Simpan Update Pendukung
    Mirip dengan BtnSave_Click di VB.NET
    """
    try:
        data = request.get_json()
        print("📥 Data Update Pendukung:", len(data.get('items', [])), 'items')
        
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'error': 'Data tidak boleh kosong'})
        
        saved_count = 0
        
        for item in items:
            tgl_kerja = item.get('tgl_kerja', '')
            nip = item.get('nip', '')
            pendukung = 'Y' if item.get('pendukung', False) else 'N'
            keterangan = item.get('keterangan', '') or ''
            transaksi = item.get('transaksi', '')  # 'IN' atau 'OUT'
            transac = item.get('transac', '')  # DinasLuar, Cuti, sakit, Alpa, dll
            transaksi_id_from = item.get('transaksi_id_from', '')
            
            if not tgl_kerja or not nip:
                continue
            
            try:
                tgl_kerja_date = datetime.strptime(tgl_kerja, '%d-%b-%Y')
            except:
                continue
            
            # Cari absensi by NIP dan TGL_KERJA
            absensi = Absensi.query.filter(
                Absensi.NIP == nip,
                db.func.date(Absensi.TGL_KERJA) == tgl_kerja_date.date()
            ).first()
            
            if not absensi:
                continue
            
            # Jika transaksi adalah DinasLuar/Cuti/Sakit/Alpa
            if transac.upper() in ['DINASLUAR', 'CUTI', 'SAKIT', 'ALPA']:
                # Update Absensi (IN dan OUT)
                absensi.PENDUKUNG_IN = pendukung
                absensi.KET_IN = keterangan[:850] if keterangan else None
                absensi.UPDATE_IN_BY = 'admin'
                absensi.UPDATE_IN_DATE = datetime.now()
                absensi.PENDUKUNG_OUT = pendukung
                absensi.KET_OUT = keterangan[:850] if keterangan else None
                absensi.UPDATE_OUT_BY = 'admin'
                absensi.UPDATE_OUT_DATE = datetime.now()
                
                # Update DinasLuar jika ada
                if transaksi_id_from:
                    dinas = DinasLuar.query.filter(
                        DinasLuar.NIP == nip,
                        DinasLuar.TRANSAKSI == transac,
                        DinasLuar.DINAS_TRANSAKSI_ID == transaksi_id_from
                    ).first()
                    
                    if dinas:
                        dinas.KETERANGAN_DINAS_LUAR = keterangan[:450] if keterangan else None
                        dinas.PENDUKUNG = pendukung
                        dinas.UPDATE_BY = 'admin'
                        dinas.UPDATE_DATE = datetime.now()
            else:
                # Update Absensi IN atau OUT saja
                if transaksi == 'IN':
                    absensi.PENDUKUNG_IN = pendukung
                    absensi.KET_IN = keterangan[:850] if keterangan else None
                    absensi.UPDATE_IN_BY = 'admin'
                    absensi.UPDATE_IN_DATE = datetime.now()
                elif transaksi == 'OUT':
                    absensi.PENDUKUNG_OUT = pendukung
                    absensi.KET_OUT = keterangan[:850] if keterangan else None
                    absensi.UPDATE_OUT_BY = 'admin'
                    absensi.UPDATE_OUT_DATE = datetime.now()
            
            saved_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{saved_count} data berhasil diupdate'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print("❌ ERROR in api_update_pendukung_save:")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_update_pendukung_get_tingkatan():
    """API: Get list Tingkatan dari MfPot"""
    try:
        tingkatan_list = db.session.query(MfPot.TINGKAT).distinct().order_by(MfPot.TINGKAT).all()
        data = [t[0] for t in tingkatan_list if t[0]]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []})


def api_update_pendukung_get_filter_fields():
    """API: Get list field untuk filter"""
    try:
        fields = [
            {'field_id': 'NIP', 'field_name': 'NIP'},
            {'field_id': 'Nama', 'field_name': 'Nama Pegawai'},
        ]
        return jsonify({'success': True, 'data': fields})
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})