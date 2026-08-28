# controllers/dashboard_2MasterDataController.py
from flask import render_template, request, jsonify, g, current_app
from datetime import datetime
import uuid
from app import db
from app.models.pegawaiModel import Pegawai
from app.utils.pegawaiHelper import search_operational_pegawai
from app.models.unitKerjaModel import MfUnitKerja
from app.models.timSiagaModel import MfTimSiaga
from app.models.timSiagaAnggotaModel import MfTimSiagaAnggota
from app.models.logActivityModel import LogActivity
from app.models.otorisasiModel import Otorisasi
from app.models.shiftModel import MfShift
from app.models.emailSendModel import MfEmailSend
from app.models.jabatanSiagaModel import MfJabatanSiaga

def master_data_email_broadcast():
    """Render halaman Master Data Email Broadcast."""
    return render_template('pages/dashboard_2/Master_Data_Email_Broadcast.html')

def api_email_broadcast_get():
    """
    API: Get data konfigurasi email (seperti Btnfind_Click di VB.NET)
    """
    try:
        # Ambil record pertama
        email_config = MfEmailSend.query.first()
        
        if not email_config:
            return jsonify({
                'success': True,
                'data': {
                    'email_send': '',
                    'pass_send': '',
                    'smtp_send': '',
                    'port_send': '',
                    'update_info': '',
                }
            })
        
        # Cari nama pegawai yang update
        update_info = ''
        if email_config.UPDATE_BY:
            peg = Pegawai.query.filter(Pegawai.NIP == email_config.UPDATE_BY).first()
            nama_update = peg.NAMA if peg else email_config.UPDATE_BY
            tgl_update = email_config.UPDATE_DATE.strftime('%d/%m/%Y %H:%M:%S') if email_config.UPDATE_DATE else ''
            update_info = f'{nama_update} - {tgl_update}'
        
        return jsonify({
            'success': True,
            'data': {
                'email_send': email_config.EMAIL_SEND or '',
                'pass_send': email_config.PASS_SEND or '',
                'smtp_send': email_config.SMTP_SEND or '',
                'port_send': email_config.PORT_SENT or '',
                'update_info': update_info,
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_email_broadcast_save():
    """
    API: Simpan/Update konfigurasi email (seperti BtnSave_Click di VB.NET)
    """
    try:
        data = request.get_json()
        email_send = data.get('email_send', '').strip()
        pass_send = data.get('pass_send', '').strip()
        smtp_send = data.get('smtp_send', '').strip()
        port_send = data.get('port_send', '').strip()
        
        # Validasi (seperti VB.NET: Email atau Password Kosong)
        if not email_send or not pass_send:
            return jsonify({'error': 'Email atau Password tidak boleh kosong'})
        
        # Cari existing config
        email_config = MfEmailSend.query.first()
        
        if email_config:
            # Update existing (seperti VB.NET: Update MFEmailSend)
            email_config.EMAIL_SEND = email_send
            email_config.PASS_SEND = pass_send
            email_config.SMTP_SEND = smtp_send
            email_config.PORT_SENT = port_send
            email_config.UPDATE_BY = 'admin'
            email_config.UPDATE_DATE = datetime.now()
        else:
            # Insert baru
            new_config = MfEmailSend(
                EMAIL_SEND=email_send,
                PASS_SEND=pass_send,
                SMTP_SEND=smtp_send,
                PORT_SENT=port_send,
                UPDATE_BY='admin',
                UPDATE_DATE=datetime.now()
            )
            db.session.add(new_config)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Update Setting Email Broadcast Sukses'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

def master_data_kgr():
    """Render halaman Master Data KGR."""
    unit_kerja_list = (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_AKTIF == 'Y')
        .order_by(MfUnitKerja.NAMA_UNIT_KERJA.asc())
        .all()
    )
    return render_template(
        'pages/dashboard_2/Master_Data_KGR.html',
        unit_kerja_list=unit_kerja_list
    )

def api_kgr_search_pegawai():
    """
    API pencarian pegawai untuk form KGR.

    Standar HRIS Reborn:

        - Minimal 1 karakter
        - Hanya Pegawai Operasional
        - IS_KELUAR = N
        - Unit Kerja IS_USE = Y
        - Maksimal 15 kandidat
        - Pencarian sebagian nama
    """

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
    #   search_operational_pegawai()
    #
    # memastikan seluruh pencarian pegawai menggunakan
    # populasi operasional HRIS Reborn.
    # ========================================================

    pegawai_list = search_operational_pegawai(
        keyword
    )

    return jsonify({
        'data': [
            {
                'nip': p.NIP,
                'nama': p.NAMA
            }
            for p in pegawai_list
        ]
    })


def api_kgr_get_shift():
    """API: Get list shift untuk dropdown"""
    try:
        shift_list = MfShift.query.filter(
            MfShift.IS_AKTIF == 'Y'
        ).order_by(MfShift.NAMA_SHIFT.asc()).all()
        
        return jsonify({
            'success': True,
            'data': [
                {
                    'shift_id': s.SHIFT_ID,
                    'nama_shift': s.NAMA_SHIFT
                }
                for s in shift_list
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})

def api_kgr_save():
    """
    API: Simpan/Update KGR
    Mirip dengan BtnSave_Click di VB.NET (tanpa UserAccount & HakAksesForm)
    """
    try:
        data = request.get_json()
        guid_tim = data.get('guid_tim', '')
        periode = data.get('periode', '')
        shift = data.get('shift', '')
        no_urut = data.get('no_urut', '0')
        unit_kerja_id = data.get('unit_kerja_id', '')
        fungsional = data.get('fungsional', '')
        nip = data.get('nip', '')
        check_lintas_tim = data.get('check_lintas_tim', False)
        is_new = data.get('is_new', True)
        
        # Validasi
        if not periode:
            return jsonify({'error': 'Periode tidak boleh kosong'})
        if not no_urut or no_urut == '0':
            return jsonify({'error': 'No Urut tidak boleh kosong'})
        if not unit_kerja_id:
            return jsonify({'error': 'Unit Kerja tidak boleh kosong'})
        if not nip:
            return jsonify({'error': 'Pegawai tidak boleh kosong'})
        
        tahun = periode[:4]
        bulan = periode[5:7]
        
        # Cek apakah pegawai sudah ada di tim lain (jika bukan lintas tim)
        if not check_lintas_tim:
            existing = MfTimSiagaAnggota.query.filter(
                MfTimSiagaAnggota.NIP == nip,
                MfTimSiagaAnggota.IS_AKTIF == 'Y',
                MfTimSiagaAnggota.BULAN_PERIODE == bulan,
                MfTimSiagaAnggota.TAHUN_PERIODE == tahun,
                MfTimSiagaAnggota.SHIFT == shift,
                MfTimSiagaAnggota.GUID_TIM != (guid_tim if not is_new else '')
            ).first()
            
            if existing:
                peg = Pegawai.query.filter(Pegawai.NIP == nip).first()
                return jsonify({
                    'error': f'Pegawai {peg.NAMA if peg else nip} sudah terdaftar di tim lain'
                })
        
        try:
            if is_new:
                # Cari atau buat header di MF_TIM_SIAGA
                existing_header = MfTimSiaga.query.filter(
                    MfTimSiaga.BULAN_PERIODE == bulan,
                    MfTimSiaga.TAHUN_PERIODE == tahun,
                    MfTimSiaga.SHIFT == shift,
                    MfTimSiaga.ID_UNIT_KERJA == str(unit_kerja_id),
                    MfTimSiaga.FUNGSIONAL_TIM == fungsional,
                    MfTimSiaga.NO_URUT_TIM == int(no_urut) if no_urut else 0
                ).first()
                
                if existing_header:
                    guid_tim = existing_header.GUID_TIM
                else:
                    guid_tim = str(uuid.uuid4())
                    tim_header = MfTimSiaga(
                        GUID_TIM=guid_tim,
                        NO_URUT_TIM=int(no_urut) if no_urut else 0,
                        NAMA_TIM=f'KGR-{fungsional}-{no_urut}',
                        ID_UNIT_KERJA=str(unit_kerja_id),
                        IS_AKTIF='Y',
                        BULAN_PERIODE=bulan,
                        TAHUN_PERIODE=tahun,
                        FUNGSIONAL_TIM=fungsional,
                        SHIFT=shift,
                        UPDATE_BY='admin',
                        UPDATE_DATE=datetime.now()
                    )
                    db.session.add(tim_header)
                    db.session.flush()
                
                # Insert anggota
                new_anggota = MfTimSiagaAnggota(
                    GUID_TIM=guid_tim,
                    NIP=nip,
                    FUNGSIONAL=fungsional,
                    IS_AKTIF='Y',
                    ID_UNIT_KERJA=str(unit_kerja_id),
                    NO_URUT=int(no_urut) if no_urut else 0,
                    BULAN_PERIODE=bulan,
                    TAHUN_PERIODE=tahun,
                    SHIFT=shift,
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(new_anggota)
                
            else:
                # Update
                anggota = MfTimSiagaAnggota.query.filter(
                    MfTimSiagaAnggota.GUID_TIM == guid_tim
                ).first()
                
                if not anggota:
                    return jsonify({'error': 'Data tidak ditemukan'})
                
                anggota.NIP = nip
                anggota.ID_UNIT_KERJA = str(unit_kerja_id)
                anggota.NO_URUT = int(no_urut) if no_urut else 0
                anggota.FUNGSIONAL = fungsional
                anggota.SHIFT = shift
                anggota.UPDATE_BY = 'admin'
                anggota.UPDATE_DATE = datetime.now()
            
            db.session.commit()
            
            peg = Pegawai.query.filter(Pegawai.NIP == nip).first()
            nama_pegawai = peg.NAMA if peg else nip
            
            return jsonify({
                'success': True,
                'message': f'Data KGR No Urut {no_urut}, Unit {unit_kerja_id} - {nama_pegawai} berhasil disimpan',
                'guid_tim': guid_tim
            })
            
        except Exception as e:
            db.session.rollback()
            raise e
            
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

def api_kgr_delete():
    """API: Delete KGR"""
    try:
        data = request.get_json()
        guid_tim = data.get('guid_tim', '')
        
        if not guid_tim:
            return jsonify({'error': 'GUID Tim tidak ditemukan'})
        
        # Cek apakah sudah ada di LogActivity (seperti VB.NET)
        log_exists = LogActivity.query.filter(
            LogActivity.GUIDTim == guid_tim,
            LogActivity.StatusID.in_(['0', '3']),
            LogActivity.Activity == 'Piket Siaga'
        ).first()
        
        if log_exists:
            return jsonify({
                'error': f'Data TIM {guid_tim} sudah diabsensi kehadiran, tidak bisa dihapus'
            })
        
        # Delete (sesuai VB.NET)
        MfTimSiagaAnggota.query.filter(
            MfTimSiagaAnggota.GUID_TIM == guid_tim
        ).delete()
        
        # Delete dari LogActivity
        LogActivity.query.filter(
            LogActivity.GUIDTim == guid_tim,
            LogActivity.Activity == 'Piket Siaga'
        ).delete()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})

def api_kgr_get():
    """API: Get data KGR by GUID (untuk edit)"""
    guid_tim = request.args.get('guid_tim', '')
    
    if not guid_tim:
        return jsonify({'error': 'GUID Tim tidak ditemukan'})
    
    anggota = MfTimSiagaAnggota.query.filter(
        MfTimSiagaAnggota.GUID_TIM == guid_tim
    ).first()
    
    if not anggota:
        return jsonify({'error': 'Data tidak ditemukan'})
    
    peg = Pegawai.query.filter(Pegawai.NIP == anggota.NIP).first()
    unit = MfUnitKerja.query.get(anggota.ID_UNIT_KERJA)
    
    return jsonify({
        'success': True,
        'data': {
            'guid_tim': anggota.GUID_TIM,
            'nip': anggota.NIP,
            'nama_pegawai': peg.NAMA if peg else '',
            'unit_kerja_id': anggota.ID_UNIT_KERJA,
            'nama_unit_kerja': unit.NAMA_UNIT_KERJA if unit else '',
            'no_urut': anggota.NO_URUT,
            'fungsional': anggota.FUNGSIONAL,
            'shift': anggota.SHIFT,
            'periode': f"{anggota.TAHUN_PERIODE}-{anggota.BULAN_PERIODE}",
        }
    })

def api_kgr_save_as():
    """
    API: Save As KGR (copy ke periode lain)
    """
    try:
        data = request.get_json()
        periode_sumber = data.get('periode_sumber', '')
        periode_tujuan = data.get('periode_tujuan', '')
        unit_kerja_id = data.get('unit_kerja_id', '')
        
        if not periode_sumber or not periode_tujuan:
            return jsonify({'error': 'Periode sumber dan tujuan harus diisi'})
        if not unit_kerja_id:
            return jsonify({'error': 'Unit Kerja tidak boleh kosong'})
        
        tahun_sumber = periode_sumber[:4]
        bulan_sumber = periode_sumber[5:7]
        tahun_tujuan = periode_tujuan[:4]
        bulan_tujuan = periode_tujuan[5:7]
        
        # Cek apakah periode tujuan sudah di-approve
        log_approved = db.session.query(LogActivity, Otorisasi).filter(
            LogActivity.GUIDLog == Otorisasi.GUIDOto,
            db.func.month(LogActivity.ActivityDate) == bulan_tujuan,
            db.func.year(LogActivity.ActivityDate) == tahun_tujuan,
            LogActivity.Activity == 'Piket Siaga',
            LogActivity.IDUnitKerja == str(unit_kerja_id),
            Otorisasi.LevelOto == '1',
            Otorisasi.Act >= '0'
        ).first()
        
        if log_approved:
            return jsonify({
                'error': f'Jadwal periode {tahun_tujuan}.{bulan_tujuan} unit {unit_kerja_id} sudah di-approve'
            })
        
        # Ambil data sumber
        anggota_sumber = MfTimSiagaAnggota.query.filter(
            MfTimSiagaAnggota.IS_AKTIF == 'Y',
            MfTimSiagaAnggota.BULAN_PERIODE == bulan_sumber,
            MfTimSiagaAnggota.TAHUN_PERIODE == tahun_sumber,
            MfTimSiagaAnggota.ID_UNIT_KERJA == str(unit_kerja_id),
            MfTimSiagaAnggota.FUNGSIONAL.in_(['KGR', 'PW'])
        ).all()
        
        if not anggota_sumber:
            return jsonify({'error': 'Data sumber tidak ditemukan'})
        
        try:
            for ag in anggota_sumber:
                # Cari atau buat header MF_TIM_SIAGA untuk periode tujuan
                existing_header = MfTimSiaga.query.filter(
                    MfTimSiaga.BULAN_PERIODE == bulan_tujuan,
                    MfTimSiaga.TAHUN_PERIODE == tahun_tujuan,
                    MfTimSiaga.SHIFT == ag.SHIFT,
                    MfTimSiaga.ID_UNIT_KERJA == str(unit_kerja_id),
                    MfTimSiaga.FUNGSIONAL_TIM == ag.FUNGSIONAL,
                    MfTimSiaga.NO_URUT_TIM == ag.NO_URUT
                ).first()
                
                if existing_header:
                    new_guid = existing_header.GUID_TIM
                else:
                    new_guid = str(uuid.uuid4())
                    tim_header = MfTimSiaga(
                        GUID_TIM=new_guid,
                        NO_URUT_TIM=ag.NO_URUT,
                        NAMA_TIM=f'KGR-{ag.FUNGSIONAL}-{ag.NO_URUT}',
                        ID_UNIT_KERJA=ag.ID_UNIT_KERJA,
                        IS_AKTIF='Y',
                        BULAN_PERIODE=bulan_tujuan,
                        TAHUN_PERIODE=tahun_tujuan,
                        FUNGSIONAL_TIM=ag.FUNGSIONAL,
                        SHIFT=ag.SHIFT,
                        UPDATE_BY='admin',
                        UPDATE_DATE=datetime.now()
                    )
                    db.session.add(tim_header)
                    db.session.flush()
                
                # Delete existing di periode tujuan untuk NIP yang sama
                MfTimSiagaAnggota.query.filter(
                    MfTimSiagaAnggota.ID_UNIT_KERJA == str(unit_kerja_id),
                    MfTimSiagaAnggota.BULAN_PERIODE == bulan_tujuan,
                    MfTimSiagaAnggota.TAHUN_PERIODE == tahun_tujuan,
                    MfTimSiagaAnggota.FUNGSIONAL.in_(['KGR', 'PW']),
                    MfTimSiagaAnggota.NIP == ag.NIP
                ).delete()
                
                # Insert baru
                new_ag = MfTimSiagaAnggota(
                    GUID_TIM=new_guid,
                    NIP=ag.NIP,
                    FUNGSIONAL=ag.FUNGSIONAL,
                    IS_AKTIF='Y',
                    ID_UNIT_KERJA=ag.ID_UNIT_KERJA,
                    NO_URUT=ag.NO_URUT,
                    BULAN_PERIODE=bulan_tujuan,
                    TAHUN_PERIODE=tahun_tujuan,
                    SHIFT=ag.SHIFT,
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(new_ag)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Data KGR berhasil disalin ke periode {tahun_tujuan}.{bulan_tujuan}'
            })
            
        except Exception as e:
            db.session.rollback()
            raise e
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

def api_kgr_cari():
    """
    API Cari KGR - mirip dengan lbRefesh_Click di VB.NET
    """
    try:
        periode = request.args.get('periode', '')
        unit_kerja_id = request.args.get('unit_kerja_id', '')
        shift = request.args.get('shift', '')
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        # ✅ PERBAIKAN: Hanya query 3 tabel (bukan 4)
        query = (
            db.session.query(
                MfTimSiagaAnggota,
                Pegawai,
                MfUnitKerja
            )
            .join(Pegawai, MfTimSiagaAnggota.NIP == Pegawai.NIP)
            .join(MfUnitKerja, MfTimSiagaAnggota.ID_UNIT_KERJA == MfUnitKerja.UNIT_KERJA_ID)
            .filter(MfTimSiagaAnggota.FUNGSIONAL.in_(['KGR', 'PW']))
        )
        
        # Filter periode
        if periode:
            tahun = periode[:4]
            bulan = periode[5:7]
            query = query.filter(
                MfTimSiagaAnggota.BULAN_PERIODE == bulan,
                MfTimSiagaAnggota.TAHUN_PERIODE == tahun
            )
        
        # Filter unit kerja (jika level > 1)
        if unit_kerja_id:
            query = query.filter(
                MfTimSiagaAnggota.ID_UNIT_KERJA == unit_kerja_id
            )
        
        # Filter shift
        if shift:
            query = query.filter(MfTimSiagaAnggota.SHIFT == shift)
        
        # Field mapping (seperti di VB.NET)
        field_mapping = {
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'UnitKerjaName': MfUnitKerja.NAMA_UNIT_KERJA,
            'Fungsional': MfTimSiagaAnggota.FUNGSIONAL,
        }
        
        if filter_field1 and filter_value1:
            field = field_mapping.get(filter_field1)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value1}%'))
        
        if filter_field2 and filter_value2:
            field = field_mapping.get(filter_field2)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value2}%'))
        
        # Order
        query = query.order_by(
            MfTimSiagaAnggota.SHIFT,
            MfTimSiagaAnggota.NO_URUT
        )
        
        results = query.all()
        
        # ✅ PERBAIKAN: Unpack 3 variabel (sesuai query)
        data = []
        for anggota, peg, unit in results:
            data.append({
                'guid_tim': anggota.GUID_TIM,
                'nip': anggota.NIP,
                'nama': peg.NAMA if peg else '',
                'no_urut': anggota.NO_URUT,
                'unit_kerja_id': anggota.ID_UNIT_KERJA,
                'unit_kerja_name': unit.NAMA_UNIT_KERJA if unit else '',
                'fungsional': anggota.FUNGSIONAL,
                'shift': anggota.SHIFT,
                'periode': f"{anggota.TAHUN_PERIODE}.{anggota.BULAN_PERIODE}",
                'is_aktif': anggota.IS_AKTIF,
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

def master_data_nominal_ut_piket():
    """Render halaman Master Data Nominal UT Piket."""
    return render_template('pages/dashboard_2/Master_Data_Nominal_UT_Piket.html')


# ============================================================
# MASTER JABATAN SIAGA
# ============================================================


def master_data_jabatan_siaga():
    """
    Render halaman Master Jabatan Siaga.

    Sumber data:
        MF_JABATAN_SIAGA

    Urutan:
        NoUrut ASC
    """

    jabatan_siaga_list = (
        MfJabatanSiaga.query
        .order_by(
            MfJabatanSiaga.NO_URUT.asc()
        )
        .all()
    )

    return render_template(
        'pages/dashboard_2/Master_Data_Jabatan_Siaga.html',
        jabatan_siaga_list=jabatan_siaga_list
    )

def api_jabatan_siaga_get():
    """
    Mengambil Master Jabatan Siaga.

    Default:
        hanya data aktif.

    all=1:
        tampilkan seluruh data termasuk nonaktif.
    """

    try:
        tampil_semua = (
            str(request.args.get('all', '')).strip()
            == '1'
        )

        query = MfJabatanSiaga.query

        if not tampil_semua:
            query = query.filter(
                MfJabatanSiaga.IS_AKTIF == 'Y'
            )

        rows = (
            query
            .order_by(
                MfJabatanSiaga.NO_URUT.asc()
            )
            .all()
        )

        return jsonify({
            'success': True,
            'data': [
                row.to_dict()
                for row in rows
            ],
            'total': len(rows)
        })

    except Exception as exc:

        current_app.logger.exception(
            'Gagal mengambil Master Jabatan Siaga'
        )

        return jsonify({
            'success': False,
            'error': str(exc),
            'data': []
        }), 500


def api_jabatan_siaga_save():
    """
    Tambah / Edit Master Jabatan Siaga.
    """

    try:
        data = request.get_json(
            silent=True
        ) or {}

        raw_id = (
            data.get('id')
            or data.get('id_jabatan_siaga')
            or ''
        )

        nama = str(
            data.get('nama_jabatan')
            or ''
        ).strip().upper()

        keterangan = str(
            data.get('keterangan')
            or ''
        ).strip()

        raw_no_urut = (
            data.get('no_urut')
            or ''
        )

        is_aktif = str(
            data.get('is_aktif')
            or 'Y'
        ).strip().upper()

        if not nama:
            return jsonify({
                'success': False,
                'error': 'Nama jabatan wajib diisi.'
            }), 400

        try:
            no_urut = int(raw_no_urut)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'error': 'No urut harus berupa angka.'
            }), 400

        if no_urut <= 0:
            return jsonify({
                'success': False,
                'error': (
                    'No urut harus lebih besar dari 0.'
                )
            }), 400

        if is_aktif not in ('Y', 'N'):
            return jsonify({
                'success': False,
                'error': 'Status aktif tidak valid.'
            }), 400

        try:
            id_jabatan = (
                int(raw_id)
                if raw_id
                else None
            )
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'error': 'ID jabatan tidak valid.'
            }), 400

        # ----------------------------------------------------
        # CEK DUPLIKAT NAMA
        # ----------------------------------------------------

        nama_query = (
            MfJabatanSiaga.query
            .filter(
                MfJabatanSiaga.NAMA_JABATAN == nama
            )
        )

        if id_jabatan:
            nama_query = nama_query.filter(
                MfJabatanSiaga.ID_JABATAN_SIAGA
                != id_jabatan
            )

        if nama_query.first():
            return jsonify({
                'success': False,
                'error': (
                    f'Jabatan "{nama}" sudah ada.'
                )
            }), 409

        update_by = 'HRIS'
        user = getattr(
            g,
            'user',
            None
        )

        if user:
            update_by = (
                getattr(user, 'NIP', None)
                or getattr(user, 'username', None)
                or 'HRIS'
            )

        now = datetime.now()

        # ====================================================
        # INSERT
        # ====================================================

        if not id_jabatan:

            existing = (
                MfJabatanSiaga.query
                .filter(
                    MfJabatanSiaga.NO_URUT
                    == no_urut
                )
                .first()
            )

            if existing:

                # Geser seluruh urutan >= posisi baru.
                #
                # Temporary range dipakai agar UNIQUE
                # NoUrut tidak bentrok.
                db.session.execute(
                    db.text("""
                        UPDATE MF_JABATAN_SIAGA
                        SET NoUrut = NoUrut + 100000
                        WHERE NoUrut >= :no
                    """),
                    {'no': no_urut}
                )

                db.session.execute(
                    db.text("""
                        UPDATE MF_JABATAN_SIAGA
                        SET NoUrut = NoUrut - 99999
                        WHERE NoUrut >= :temporary
                    """),
                    {
                        'temporary':
                            no_urut + 100000
                    }
                )

            row = MfJabatanSiaga(
                NO_URUT=no_urut,
                NAMA_JABATAN=nama,
                KETERANGAN=keterangan or None,
                IS_AKTIF=is_aktif,
                UPDATE_BY=update_by,
                UPDATE_DATE=now
            )

            db.session.add(row)

        # ====================================================
        # UPDATE
        # ====================================================

        else:

            row = (
                MfJabatanSiaga.query
                .filter(
                    MfJabatanSiaga.ID_JABATAN_SIAGA
                    == id_jabatan
                )
                .first()
            )

            if not row:
                return jsonify({
                    'success': False,
                    'error': (
                        'Jabatan tidak ditemukan.'
                    )
                }), 404

            old_no_urut = row.NO_URUT

            # ------------------------------------------------
            # NOMOR URUT BERUBAH
            # ------------------------------------------------

            if old_no_urut != no_urut:

                # Pindahkan row yang sedang diedit
                # ke nomor sementara.
                db.session.execute(
                    db.text("""
                        UPDATE MF_JABATAN_SIAGA
                        SET NoUrut = NoUrut + 100000
                        WHERE IDJabatanSiaga = :id
                    """),
                    {
                        'id': id_jabatan
                    }
                )

                if no_urut < old_no_urut:

                    # Contoh:
                    # 6 -> 4
                    #
                    # 4 -> 5
                    # 5 -> 6

                    db.session.execute(
                        db.text("""
                            UPDATE MF_JABATAN_SIAGA
                            SET NoUrut = NoUrut + 1
                            WHERE NoUrut >= :new_no
                              AND NoUrut < :old_no
                        """),
                        {
                            'new_no': no_urut,
                            'old_no': old_no_urut
                        }
                    )

                else:

                    # Contoh:
                    # 6 -> 7
                    #
                    # 7 -> 6

                    db.session.execute(
                        db.text("""
                            UPDATE MF_JABATAN_SIAGA
                            SET NoUrut = NoUrut - 1
                            WHERE NoUrut > :old_no
                              AND NoUrut <= :new_no
                        """),
                        {
                            'old_no': old_no_urut,
                            'new_no': no_urut
                        }
                    )

                db.session.execute(
                    db.text("""
                        UPDATE MF_JABATAN_SIAGA
                        SET NoUrut = :new_no
                        WHERE IDJabatanSiaga = :id
                    """),
                    {
                        'new_no': no_urut,
                        'id': id_jabatan
                    }
                )

                db.session.flush()

                row = (
                    MfJabatanSiaga.query
                    .filter(
                        MfJabatanSiaga.ID_JABATAN_SIAGA
                        == id_jabatan
                    )
                    .first()
                )

            row.NAMA_JABATAN = nama
            row.KETERANGAN = (
                keterangan or None
            )
            row.IS_AKTIF = is_aktif
            row.UPDATE_BY = update_by
            row.UPDATE_DATE = now

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                'Master Jabatan Siaga '
                'berhasil disimpan.'
            ),
            'data': row.to_dict()
        })

    except Exception as exc:

        db.session.rollback()

        current_app.logger.exception(
            'Gagal menyimpan Master Jabatan Siaga'
        )

        return jsonify({
            'success': False,
            'error': str(exc)
        }), 500


def api_jabatan_siaga_deactivate():
    """
    Deaktivasi jabatan.
    Record tidak dihapus secara fisik.
    """

    try:
        data = request.get_json(
            silent=True
        ) or {}

        raw_id = (
            data.get('id')
            or data.get('id_jabatan_siaga')
            or ''
        )

        try:
            id_jabatan = int(raw_id)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'error': 'ID jabatan tidak valid.'
            }), 400

        row = (
            MfJabatanSiaga.query
            .filter(
                MfJabatanSiaga.ID_JABATAN_SIAGA
                == id_jabatan
            )
            .first()
        )

        if not row:
            return jsonify({
                'success': False,
                'error': (
                    'Jabatan tidak ditemukan.'
                )
            }), 404

        row.IS_AKTIF = 'N'
        row.UPDATE_BY = 'HRIS'
        row.UPDATE_DATE = datetime.now()

        user = getattr(
            g,
            'user',
            None
        )

        if user:
            row.UPDATE_BY = (
                getattr(user, 'NIP', None)
                or getattr(user, 'username', None)
                or 'HRIS'
            )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Jabatan "{row.NAMA_JABATAN}" '
                'berhasil dinonaktifkan.'
            ),
            'data': row.to_dict()
        })

    except Exception as exc:

        db.session.rollback()

        current_app.logger.exception(
            'Gagal menonaktifkan Master Jabatan Siaga'
        )

        return jsonify({
            'success': False,
            'error': str(exc)
        }), 500

def master_data_tim_siaga():
    """Render halaman Master Data Tim Siaga."""
    unit_kerja_list = (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_AKTIF == 'Y')
        .order_by(MfUnitKerja.NAMA_UNIT_KERJA.asc())
        .all()
    )
    return render_template(
        'pages/dashboard_2/Master_Data_Tim_Siaga.html',
        unit_kerja_list=unit_kerja_list
    )

def api_search_pegawai_tim():
    """
    API pencarian pegawai untuk form Tim Siaga.

    Standar HRIS Reborn:

        - Minimal 1 karakter
        - Hanya Pegawai Operasional
        - IS_KELUAR = N
        - Unit Kerja IS_USE = Y
        - Maksimal 15 kandidat
        - Pencarian sebagian nama
    """

    keyword = request.args.get('keyword', '').strip()

    if not keyword:
        return jsonify({
            'data': []
        })

    # ========================================================
    # AUTOCOMPLETE PEGAWAI TERPUSAT
    #
    # Seluruh pencarian pegawai menggunakan Business Rule
    # yang sama melalui search_operational_pegawai().
    # ========================================================

    pegawai_list = search_operational_pegawai(
        keyword
    )

    return jsonify({
        'data': [
            {
                'nip': p.NIP,
                'nama': p.NAMA
            }
            for p in pegawai_list
        ]
    })


def api_tim_siaga_save():
    """API: Simpan/Update Tim Siaga"""
    try:
        data = request.get_json()
        guid_tim = data.get('guid_tim', '')
        nama_tim = data.get('nama_tim', '')
        no_urut = data.get('no_urut', '0')
        unit_kerja_id = data.get('unit_kerja_id', '')
        fungsional = data.get('fungsional', '')
        shift = data.get('shift', '1')
        periode = data.get('periode', '')
        anggota_list = data.get('anggota', [])
        is_new = data.get('is_new', True)
        
        if not nama_tim or not unit_kerja_id or not fungsional or not periode:
            return jsonify({'error': 'Data tidak lengkap'})
        
        if not anggota_list:
            return jsonify({'error': 'Anggota Tim kosong'})
        
        tahun = periode[:4]
        bulan = periode[5:7]
        
        if is_new:
            guid_tim = str(uuid.uuid4())
            
            # ✅ INSERT HEADER DULU
            tim = MfTimSiaga(
                GUID_TIM=guid_tim,
                NO_URUT_TIM=int(no_urut) if no_urut else 0,
                NAMA_TIM=nama_tim,
                ID_UNIT_KERJA=str(unit_kerja_id),
                IS_AKTIF='Y',
                BULAN_PERIODE=bulan,
                TAHUN_PERIODE=tahun,
                FUNGSIONAL_TIM=fungsional,
                SHIFT=shift,
                UPDATE_BY='admin',
                UPDATE_DATE=datetime.now()
            )
            db.session.add(tim)
            # ✅ FLUSH: pastikan header tersimpan dulu sebelum insert anggota
            db.session.flush()
            
            # ✅ BARU INSERT ANGGOTA
            for i, anggota in enumerate(anggota_list, 1):
                ag = MfTimSiagaAnggota(
                    GUID_TIM=guid_tim,
                    NIP=anggota.get('nip', ''),
                    FUNGSIONAL=fungsional,
                    IS_AKTIF='Y',
                    ID_UNIT_KERJA=str(unit_kerja_id),
                    NO_URUT=i,
                    BULAN_PERIODE=bulan,
                    TAHUN_PERIODE=tahun,
                    SHIFT=shift,
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(ag)
        else:
            # Update existing
            tim = MfTimSiaga.query.get(guid_tim)
            if not tim:
                return jsonify({'error': 'Data tidak ditemukan'})
            
            tim.NAMA_TIM = nama_tim
            tim.NO_URUT_TIM = int(no_urut) if no_urut else 0
            tim.ID_UNIT_KERJA = str(unit_kerja_id)
            tim.FUNGSIONAL_TIM = fungsional
            tim.SHIFT = shift
            tim.BULAN_PERIODE = bulan
            tim.TAHUN_PERIODE = tahun
            tim.UPDATE_BY = 'admin'
            tim.UPDATE_DATE = datetime.now()
            
            # ✅ FLUSH dulu
            db.session.flush()
            
            # Hapus anggota lama
            MfTimSiagaAnggota.query.filter(MfTimSiagaAnggota.GUID_TIM == guid_tim).delete()
            # ✅ FLUSH lagi
            db.session.flush()
            
            # Insert anggota baru
            for i, anggota in enumerate(anggota_list, 1):
                ag = MfTimSiagaAnggota(
                    GUID_TIM=guid_tim,
                    NIP=anggota.get('nip', ''),
                    FUNGSIONAL=fungsional,
                    IS_AKTIF='Y',
                    ID_UNIT_KERJA=str(unit_kerja_id),
                    NO_URUT=i,
                    BULAN_PERIODE=bulan,
                    TAHUN_PERIODE=tahun,
                    SHIFT=shift,
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(ag)
        
        # ✅ COMMIT di akhir
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Data berhasil disimpan',
            'guid_tim': guid_tim
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_tim_siaga_delete():
    """API: Delete Tim Siaga"""
    try:
        data = request.get_json()
        guid_tim = data.get('guid_tim', '')
        
        if not guid_tim:
            return jsonify({'error': 'GUID Tim tidak ditemukan'})
        
        MfTimSiagaAnggota.query.filter(MfTimSiagaAnggota.GUID_TIM == guid_tim).delete()
        MfTimSiaga.query.filter(MfTimSiaga.GUID_TIM == guid_tim).delete()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


def api_tim_siaga_get():
    """API: Get data Tim Siaga by GUID"""
    guid_tim = request.args.get('guid_tim', '')
    
    if not guid_tim:
        return jsonify({'error': 'GUID Tim tidak ditemukan'})
    
    tim = MfTimSiaga.query.get(guid_tim)
    if not tim:
        return jsonify({'error': 'Data tidak ditemukan'})
    
    anggota = (
        MfTimSiagaAnggota.query
        .filter(MfTimSiagaAnggota.GUID_TIM == guid_tim)
        .order_by(MfTimSiagaAnggota.NO_URUT)
        .all()
    )
    
    anggota_data = []
    for ag in anggota:
        peg = Pegawai.query.filter(Pegawai.NIP == ag.NIP).first()
        anggota_data.append({
            'nip': ag.NIP,
            'nama': peg.NAMA if peg else '-',
            'fungsional': ag.FUNGSIONAL,
        })
    
    return jsonify({
        'success': True,
        'data': {
            'guid_tim': tim.GUID_TIM,
            'nama_tim': tim.NAMA_TIM,
            'no_urut': tim.NO_URUT_TIM,
            'unit_kerja_id': tim.ID_UNIT_KERJA,
            'fungsional': tim.FUNGSIONAL_TIM,
            'shift': tim.SHIFT,
            'periode': f"{tim.TAHUN_PERIODE}-{tim.BULAN_PERIODE}",
            'anggota': anggota_data,
        }
    })


def api_tim_siaga_save_as():
    """API: Save As (copy tim ke periode lain)"""
    try:
        data = request.get_json()
        periode_sumber = data.get('periode_sumber', '')
        periode_tujuan = data.get('periode_tujuan', '')
        unit_kerja_id = data.get('unit_kerja_id', '')
        shift = data.get('shift', '1')
        
        if not periode_sumber or not periode_tujuan:
            return jsonify({'error': 'Periode sumber dan tujuan harus diisi'})
        
        tahun_sumber = periode_sumber[:4]
        bulan_sumber = periode_sumber[5:7]
        tahun_tujuan = periode_tujuan[:4]
        bulan_tujuan = periode_tujuan[5:7]
        
        # Get tim sumber
        tim_list = MfTimSiaga.query.filter(
            MfTimSiaga.BULAN_PERIODE == bulan_sumber,
            MfTimSiaga.TAHUN_PERIODE == tahun_sumber,
            MfTimSiaga.SHIFT == shift,
            MfTimSiaga.ID_UNIT_KERJA == str(unit_kerja_id)
        ).all()
        
        if not tim_list:
            return jsonify({'error': 'Data sumber tidak ditemukan'})
        
        # Delete existing di periode tujuan
        MfTimSiagaAnggota.query.filter(
            MfTimSiagaAnggota.BULAN_PERIODE == bulan_tujuan,
            MfTimSiagaAnggota.TAHUN_PERIODE == tahun_tujuan,
            MfTimSiagaAnggota.ID_UNIT_KERJA == str(unit_kerja_id),
            MfTimSiagaAnggota.SHIFT == shift
        ).delete()
        
        MfTimSiaga.query.filter(
            MfTimSiaga.BULAN_PERIODE == bulan_tujuan,
            MfTimSiaga.TAHUN_PERIODE == tahun_tujuan,
            MfTimSiaga.ID_UNIT_KERJA == str(unit_kerja_id),
            MfTimSiaga.SHIFT == shift
        ).delete()
        
        saved = 0
        for tim in tim_list:
            new_guid = str(uuid.uuid4())
            
            new_tim = MfTimSiaga(
                GUID_TIM=new_guid,
                NO_URUT_TIM=tim.NO_URUT_TIM,
                NAMA_TIM=tim.NAMA_TIM,
                ID_UNIT_KERJA=tim.ID_UNIT_KERJA,
                IS_AKTIF='Y',
                BULAN_PERIODE=bulan_tujuan,
                TAHUN_PERIODE=tahun_tujuan,
                FUNGSIONAL_TIM=tim.FUNGSIONAL_TIM,
                SHIFT=tim.SHIFT,
                UPDATE_BY='admin',
                UPDATE_DATE=datetime.now()
            )
            db.session.add(new_tim)
            
            # Copy anggota
            anggota_lama = MfTimSiagaAnggota.query.filter(
                MfTimSiagaAnggota.GUID_TIM == tim.GUID_TIM
            ).all()
            
            for ag in anggota_lama:
                new_ag = MfTimSiagaAnggota(
                    GUID_TIM=new_guid,
                    NIP=ag.NIP,
                    FUNGSIONAL=ag.FUNGSIONAL,
                    IS_AKTIF='Y',
                    ID_UNIT_KERJA=ag.ID_UNIT_KERJA,
                    NO_URUT=ag.NO_URUT,
                    BULAN_PERIODE=bulan_tujuan,
                    TAHUN_PERIODE=tahun_tujuan,
                    SHIFT=ag.SHIFT,
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(new_ag)
            
            saved += 1
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{saved} tim berhasil disalin'})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

def master_data_user_account():
    """Render halaman Master Data User Account."""
    return render_template('pages/dashboard_2/Master_Data_User_Account.html')

# View tampilan Cari
def cari_data_kgr():
    """Render halaman Cari Data KGR."""
    unit_kerja_list = (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_AKTIF == 'Y')
        .order_by(MfUnitKerja.NAMA_UNIT_KERJA.asc())
        .all()
    )
    return render_template(
        'pages/dashboard_2/Cari_Data_KGR.html',
        unit_kerja_list=unit_kerja_list
    )

def api_kgr_get_filter_fields():
    """API: Get list field untuk filter dropdown"""
    try:
        fields = [
            {'field_id': 'NIP', 'field_name': 'NIP'},
            {'field_id': 'Nama', 'field_name': 'Nama'},
            {'field_id': 'UnitKerjaName', 'field_name': 'Unit Kerja'},
            {'field_id': 'Fungsional', 'field_name': 'Fungsional'},
        ]
        
        return jsonify({
            'success': True,
            'data': fields
        })
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})


def cari_data_piket_siaga():
    """Render halaman Cari Data Piket Siaga."""
    unit_kerja_list = (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_AKTIF == 'Y')
        .order_by(MfUnitKerja.NAMA_UNIT_KERJA.asc())
        .all()
    )
    return render_template(
        'pages/dashboard_2/Cari_Data_Piket_Siaga.html',
        unit_kerja_list=unit_kerja_list
    )


def cari_data_piket_tim_siaga():
    """Render halaman Cari Data Piket Tim Siaga."""
    unit_kerja_list = (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_AKTIF == 'Y')
        .order_by(MfUnitKerja.NAMA_UNIT_KERJA.asc())
        .all()
    )
    return render_template(
        'pages/dashboard_2/Cari_Data_Piket_Tim_Siaga.html',
        unit_kerja_list=unit_kerja_list
    )

def api_cari_tim_siaga():
    """
    API Cari Tim Siaga - mencari data dari tabel MF_TIM_SIAGA & MF_TIM_SIAGA_ANGGOTA
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')
        periode = request.args.get('periode', '')
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        # Query dari MF_TIM_SIAGA join ke anggota & pegawai
        query = (
            db.session.query(MfTimSiaga, Pegawai, MfUnitKerja, MfTimSiagaAnggota)
            .join(MfTimSiagaAnggota, MfTimSiaga.GUID_TIM == MfTimSiagaAnggota.GUID_TIM)
            .join(Pegawai, MfTimSiagaAnggota.NIP == Pegawai.NIP)
            .join(MfUnitKerja, MfTimSiaga.ID_UNIT_KERJA == MfUnitKerja.UNIT_KERJA_ID)
        )
        
        # Filter periode (bulan+tahun)
        if periode:
            tahun = periode[:4]
            bulan = periode[5:7]
            query = query.filter(
                MfTimSiaga.BULAN_PERIODE == bulan,
                MfTimSiaga.TAHUN_PERIODE == tahun
            )
        
        # Field mapping untuk filter tambahan
        field_mapping = {
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'UnitKerjaName': MfUnitKerja.NAMA_UNIT_KERJA,
            'NamaTim': MfTimSiaga.NAMA_TIM,
            'Fungsional': MfTimSiaga.FUNGSIONAL_TIM,
            'Shift': MfTimSiaga.SHIFT,
        }
        
        if filter_field1 and filter_value1:
            field = field_mapping.get(filter_field1)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value1}%'))
        
        if filter_field2 and filter_value2:
            field = field_mapping.get(filter_field2)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value2}%'))
        
        # Order
        query = query.order_by(
            MfTimSiaga.TAHUN_PERIODE.desc(),
            MfTimSiaga.BULAN_PERIODE.desc(),
            MfTimSiaga.SHIFT,
            MfTimSiaga.NO_URUT_TIM,
            MfTimSiaga.NAMA_TIM,
            MfTimSiagaAnggota.NO_URUT
        )
        
        results = query.all()
        
        # Format data - gabungkan per GUID_TIM
        tim_dict = {}
        for tim, peg, unit, anggota in results:
            guid = tim.GUID_TIM
            if guid not in tim_dict:
                tim_dict[guid] = {
                    'guid_tim': guid,
                    'nama_tim': tim.NAMA_TIM or '',
                    'no_urut': tim.NO_URUT_TIM or 0,
                    'unit_kerja': unit.NAMA_UNIT_KERJA or '',
                    'unit_kerja_id': tim.ID_UNIT_KERJA or '',
                    'fungsional': tim.FUNGSIONAL_TIM or '',
                    'shift': tim.SHIFT or '',
                    'periode': f"{tim.TAHUN_PERIODE or ''}.{tim.BULAN_PERIODE or ''}",
                    'is_aktif': tim.IS_AKTIF or 'Y',
                    'update_by': tim.UPDATE_BY or '',
                    'update_date': tim.UPDATE_DATE.strftime('%d/%m/%Y %H:%M') if tim.UPDATE_DATE else '',
                    'anggota': []
                }
            tim_dict[guid]['anggota'].append({
                'nip': anggota.NIP,
                'nama': peg.NAMA or '',
                'fungsional': anggota.FUNGSIONAL or '',
            })
        
        data = list(tim_dict.values())
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'data': []})


def api_cari_tim_siaga_get():
    """API: Get detail Tim Siaga by GUID (untuk edit)"""
    guid_tim = request.args.get('guid_tim', '')
    
    if not guid_tim:
        return jsonify({'error': 'GUID Tim tidak ditemukan'})
    
    tim = MfTimSiaga.query.get(guid_tim)
    if not tim:
        return jsonify({'error': 'Data tidak ditemukan'})
    
    anggota = (
        MfTimSiagaAnggota.query
        .filter(MfTimSiagaAnggota.GUID_TIM == guid_tim)
        .order_by(MfTimSiagaAnggota.NO_URUT)
        .all()
    )
    
    anggota_data = []
    for ag in anggota:
        peg = Pegawai.query.filter(Pegawai.NIP == ag.NIP).first()
        anggota_data.append({
            'nip': ag.NIP,
            'nama': peg.NAMA if peg else '-',
            'fungsional': ag.FUNGSIONAL,
        })
    
    return jsonify({
        'success': True,
        'data': {
            'guid_tim': tim.GUID_TIM,
            'nama_tim': tim.NAMA_TIM,
            'no_urut': tim.NO_URUT_TIM,
            'unit_kerja_id': tim.ID_UNIT_KERJA,
            'fungsional': tim.FUNGSIONAL_TIM,
            'shift': tim.SHIFT,
            'periode': f"{tim.TAHUN_PERIODE}-{tim.BULAN_PERIODE}",
            'anggota': anggota_data,
        }
    })


def cari_data_tim_siaga():
    """Render halaman Cari Data Tim Siaga."""
    unit_kerja_list = (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_AKTIF == 'Y')
        .order_by(MfUnitKerja.NAMA_UNIT_KERJA.asc())
        .all()
    )
    return render_template(
        'pages/dashboard_2/Cari_Data_Tim_Siaga.html',
        unit_kerja_list=unit_kerja_list
    )


# ============================================================
# ACTIVATE MASTER JABATAN SIAGA
# ============================================================

def api_jabatan_siaga_activate():
    """
    Mengaktifkan kembali Master Jabatan Siaga.

    Record tidak dibuat ulang.
    Record existing hanya diubah:
        IS_AKTIF = 'Y'
    """

    try:

        data = request.get_json(
            silent=True
        ) or {}

        raw_id = (
            data.get('id')
            or data.get('id_jabatan_siaga')
            or ''
        )

        try:
            id_jabatan = int(raw_id)
        except (TypeError, ValueError):

            return jsonify({
                'success': False,
                'error': 'ID jabatan tidak valid.'
            }), 400


        row = (
            MfJabatanSiaga.query
            .filter(
                MfJabatanSiaga.ID_JABATAN_SIAGA
                == id_jabatan
            )
            .first()
        )


        if not row:

            return jsonify({
                'success': False,
                'error': 'Jabatan tidak ditemukan.'
            }), 404


        row.IS_AKTIF = 'Y'

        user = getattr(
            g,
            'user',
            None
        )

        row.UPDATE_BY = 'HRIS'

        if user:

            row.UPDATE_BY = (
                getattr(user, 'NIP', None)
                or getattr(user, 'username', None)
                or 'HRIS'
            )

        row.UPDATE_DATE = datetime.now()


        db.session.commit()


        return jsonify({
            'success': True,
            'message': (
                'Jabatan berhasil diaktifkan kembali.'
            ),
            'data': row.to_dict()
        })


    except Exception as exc:

        db.session.rollback()

        current_app.logger.exception(
            'Gagal mengaktifkan Master Jabatan Siaga'
        )

        return jsonify({
            'success': False,
            'error': str(exc)
        }), 500

