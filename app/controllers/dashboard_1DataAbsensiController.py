# controllers/dashboard_1DataAbsensiController.py
from flask import render_template, request, jsonify
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import func, text
from app import db
from app.models.absensiModel import Absensi
from app.models.lemburModel import Lembur
from app.models.pegawaiModel import Pegawai
from app.models.unitKerjaModel import MfUnitKerja
from app.models.kalenderModel import MfKalender
from app.models.potModel import MfPot
from app.models.classModel import MfClass
from app.models.dinasLuarModel import DinasLuar
from app.models.jabatanModel import MfJabatan
from app.models.timeRecorderModel import TimeRecorder
from app.models.jamKerjaModel import MfJamKerja
from app.models.loadFingerModel import MfLoadFinger
from app.models.dinasLuarModel import DinasLuar
from app.models.mediaInformasiModel import MediaInformasi
import random

_NORMALISASI_CACHE = {}

_DAT_IMPORT_CACHE = {}


def api_normalisasi_upload_dat():
    """
    IMPORT FILE .DAT - MULTI FILE.

    Alur:
    .DAT -> FINGER_HARVEST_RAW

    Format .DAT:
    FINGER_ID <TAB> WAKTU <TAB> STATUS <TAB> PUNCH <TAB> DEVICE_IP

    Data raw disimpan apa adanya.
    Filter administrator/operator mesin dilakukan pada tahap normalisasi.
    """

    try:
        from datetime import datetime

        files = request.files.getlist("files")

        if not files:
            return jsonify({
                "success": False,
                "error": "Tidak ada file .DAT yang dipilih."
            }), 400

        inserted = 0
        duplicate = 0
        invalid = 0
        admin_raw = 0
        total_lines = 0
        preview = []

        connection = db.engine.raw_connection()

        try:
            cursor = connection.cursor()

            for file in files:

                filename = (file.filename or "").strip()

                if not filename:
                    continue

                if not filename.lower().endswith(".dat"):
                    invalid += 1
                    continue

                content = file.read()

                # DAT dari aplikasi HRIS 2013 menggunakan CRLF.
                content_text = content.decode(
                    "utf-8",
                    errors="replace"
                )

                for line_number, raw_line in enumerate(
                    content_text.splitlines(),
                    start=1
                ):

                    line = raw_line.strip()

                    if not line:
                        continue

                    total_lines += 1

                    parts = line.split("\t")

                    if len(parts) < 5:
                        invalid += 1
                        continue

                    finger_id = parts[0].strip()
                    waktu_text = parts[1].strip()
                    status = parts[2].strip() or None
                    punch_text = parts[3].strip()
                    device_ip = parts[4].strip()

                    if not finger_id or not waktu_text or not device_ip:
                        invalid += 1
                        continue

                    try:
                        waktu = datetime.strptime(
                            waktu_text,
                            "%Y-%m-%d %H:%M"
                        )
                    except ValueError:
                        invalid += 1
                        continue

                    # Tolak tahun fingerprint yang tidak masuk akal.
                    # Data HRIS historis menggunakan tahun >= 2000
                    # dan tidak boleh melebihi tahun berjalan + 1.
                    if (
                        waktu.year < 2000
                        or waktu.year > datetime.now().year + 1
                    ):
                        invalid += 1
                        continue

                    try:
                        punch = int(punch_text)
                    except ValueError:
                        punch = None

                    try:
                        finger_id_int = int(finger_id)
                    except ValueError:
                        invalid += 1
                        continue

                    # Finger ID operator/admin tetap masuk RAW.
                    # Filtering dilakukan saat normalisasi.
                    if finger_id in {"1", "2", "4", "5"}:
                        admin_raw += 1

                    # Cegah file yang sama / record yang sama
                    # masuk berulang kali.
                    cursor.execute(
                        """
                        SELECT ID
                        FROM FINGER_HARVEST_RAW
                        WHERE DEVICE_IP = %s
                          AND USER_ID = %s
                          AND WAKTU = %s
                          AND COALESCE(PUNCH, -1) = COALESCE(%s, -1)
                        LIMIT 1
                        """,
                        (
                            device_ip,
                            finger_id,
                            waktu,
                            punch,
                        )
                    )

                    exists = cursor.fetchone()

                    if exists:
                        duplicate += 1
                        continue

                    harvest_date = waktu.date()

                    cursor.execute(
                        """
                        INSERT INTO FINGER_HARVEST_RAW
                        (
                            HARVEST_DATE,
                            DEVICE_IP,
                            DEVICE_SERIAL,
                            DEVICE_NAME,
                            FINGER_ID,
                            UID_DEVICE,
                            USER_ID,
                            WAKTU,
                            STATUS,
                            PUNCH
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            NULL,
                            NULL,
                            %s,
                            NULL,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        """,
                        (
                            harvest_date,
                            device_ip,
                            finger_id_int,
                            finger_id,
                            waktu,
                            status,
                            punch,
                        )
                    )

                    inserted += 1

                    # Preview maksimum 200 record.
                    if len(preview) < 200:
                        preview.append({
                            "finger_id": finger_id,
                            "waktu": waktu.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            "status": status or "",
                            "punch": punch,
                            "device_ip": device_ip,
                            "filename": filename,
                        })

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()
            connection.close()

        _DAT_IMPORT_CACHE["files"] = [
            {
                "filename": f.filename or "",
                "valid": bool(
                    f.filename
                    and f.filename.lower().endswith(".dat")
                )
            }
            for f in files
        ]

        return jsonify({
            "success": True,
            "total_files": len(files),
            "total_lines": total_lines,
            "inserted": inserted,
            "duplicate": duplicate,
            "invalid": invalid,
            "admin_raw": admin_raw,
            "preview": preview,
            "message": (
                f"Import .DAT selesai. "
                f"{inserted} record masuk FINGER_HARVEST_RAW."
            )
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def api_normalisasi_commit_dat():
    """
    COMMIT FILE .DAT YANG SUDAH ADA DI STAGING
    KE FINGER_HARVEST_RAW.

    Tidak mengubah TIME_RECORDER atau ABSENSI.
    Tahap ini hanya memasukkan raw fingerprint.
    """

    try:
        from datetime import datetime

        staging_dir = Path("/opt/hris/app/var/dat-import")

        if not staging_dir.exists():
            return jsonify({
                "success": False,
                "error": "Folder staging .DAT tidak ditemukan."
            }), 400

        dat_files = sorted(
            staging_dir.glob("*.dat")
        )

        if not dat_files:
            return jsonify({
                "success": False,
                "error": "Tidak ada file .DAT di staging."
            }), 400

        connection = db.engine.raw_connection()

        inserted = 0
        duplicate = 0
        invalid = 0
        total_lines = 0
        files_processed = 0
        admin_count = 0

        try:
            cursor = connection.cursor()

            for dat_path in dat_files:

                files_processed += 1

                content = dat_path.read_bytes()

                content_text = content.decode(
                    "utf-8",
                    errors="replace"
                )

                for raw_line in content_text.splitlines():

                    line = raw_line.strip()

                    if not line:
                        continue

                    total_lines += 1

                    parts = line.split("\t")

                    if len(parts) < 5:
                        invalid += 1
                        continue

                    finger_id = parts[0].strip()
                    waktu_text = parts[1].strip()
                    status = parts[2].strip() or None
                    punch_text = parts[3].strip()
                    device_ip = parts[4].strip()

                    if (
                        not finger_id
                        or not waktu_text
                        or not device_ip
                    ):
                        invalid += 1
                        continue

                    try:
                        waktu = datetime.strptime(
                            waktu_text,
                            "%Y-%m-%d %H:%M"
                        )
                    except ValueError:
                        invalid += 1
                        continue

                    # Tolak tahun fingerprint yang tidak masuk akal.
                    # Data HRIS historis menggunakan tahun >= 2000
                    # dan tidak boleh melebihi tahun berjalan + 1.
                    if (
                        waktu.year < 2000
                        or waktu.year > datetime.now().year + 1
                    ):
                        invalid += 1
                        continue

                    try:
                        finger_id_int = int(finger_id)
                    except ValueError:
                        invalid += 1
                        continue

                    try:
                        punch = int(punch_text)
                    except ValueError:
                        punch = None

                    if finger_id in {"1", "2", "4", "5"}:
                        admin_count += 1

                    cursor.execute(
                        """
                        SELECT ID
                        FROM FINGER_HARVEST_RAW
                        WHERE DEVICE_IP = %s
                          AND USER_ID = %s
                          AND WAKTU = %s
                          AND COALESCE(PUNCH, -1)
                              = COALESCE(%s, -1)
                        LIMIT 1
                        """,
                        (
                            device_ip,
                            finger_id,
                            waktu,
                            punch,
                        )
                    )

                    if cursor.fetchone():
                        duplicate += 1
                        continue

                    cursor.execute(
                        """
                        INSERT INTO FINGER_HARVEST_RAW
                        (
                            HARVEST_DATE,
                            DEVICE_IP,
                            DEVICE_SERIAL,
                            DEVICE_NAME,
                            FINGER_ID,
                            UID_DEVICE,
                            USER_ID,
                            WAKTU,
                            STATUS,
                            PUNCH
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            NULL,
                            NULL,
                            %s,
                            NULL,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        """,
                        (
                            waktu.date(),
                            device_ip,
                            finger_id_int,
                            finger_id,
                            waktu,
                            status,
                            punch,
                        )
                    )

                    inserted += 1

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()
            connection.close()

        return jsonify({
            "success": True,
            "files_processed": files_processed,
            "total_lines": total_lines,
            "inserted": inserted,
            "duplicate": duplicate,
            "invalid": invalid,
            "admin_count": admin_count,
            "message": (
                "Import .DAT ke FINGER_HARVEST_RAW selesai."
            )
        })

    except Exception as e:

        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def data_absensi_non_finger():
    """
    Render halaman Data Absensi Non Finger.
    """
    return render_template('pages/dashboard_1/Data Absensi Non Finger.html')

def api_search_pegawai_non_finger():
    """
    API pencarian pegawai KHUSUS untuk form Absensi Non Finger.
    """
    keyword = request.args.get('keyword', '').strip()
    if len(keyword) < 2:
        return jsonify({'data': []})

    pegawai_list = (
        Pegawai.query
        .filter(Pegawai.NAMA.ilike(f'%{keyword}%'))
        .order_by(Pegawai.NAMA.asc())
        .limit(15)
        .all()
    )

    return jsonify({
        'data': [
            {'nip': p.NIP, 'nama': p.NAMA}
            for p in pegawai_list
        ]
    })

def api_absensi_non_finger_search():
    """API: Cari data absensi untuk form Non Finger (single record)"""
    try:
        nip = request.args.get('finger_id', '')  # ✅ Parameter bernama finger_id tapi isinya NIP
        tgl = request.args.get('tgl', '')
        
        if not nip or not tgl:
            return jsonify({'error': 'NIP dan Tanggal harus diisi', 'data': None})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        
        # ✅ Cari via NIP (bukan FINGER_ID)
        absensi = (
            db.session.query(Absensi, Pegawai)
            .join(Pegawai, Absensi.NIP == Pegawai.NIP)
            .filter(Absensi.NIP == nip)  # ✅ Pakai NIP
            .filter(db.func.date(Absensi.TGL_KERJA) == tgl_date.date())
            .first()
        )
        
        if absensi:
            a, p = absensi
            return jsonify({
                'success': True,
                'data': {
                    'finger_id': a.NIP or p.NIP,
                    'nip': a.NIP or p.NIP,
                    'nama': p.NAMA,
                    'tgl_kerja': a.TGL_KERJA.strftime('%Y-%m-%d') if a.TGL_KERJA else '',
                    'jam_in': a.TGL_JAM_IN.strftime('%H:%M') if a.TGL_JAM_IN and a.TGL_JAM_IN.year > 1900 else '',
                    'jam_out': a.TGL_JAM_OUT.strftime('%H:%M') if a.TGL_JAM_OUT and a.TGL_JAM_OUT.year > 1900 else '',
                    'jam_baku_in': a.TGL_JAM_BAKU_IN.strftime('%H:%M') if a.TGL_JAM_BAKU_IN and a.TGL_JAM_BAKU_IN.year > 1900 else '',
                    'jam_baku_out': a.TGL_JAM_BAKU_OUT.strftime('%H:%M') if a.TGL_JAM_BAKU_OUT and a.TGL_JAM_BAKU_OUT.year > 1900 else '',
                    'ket_in': a.KET_IN or '',
                    'ket_out': a.KET_OUT or '',
                    'awal_tlm': a.AWAL_TLM or 0,
                    'total_tlm': a.TOTAL_TLM or 0,
                    'total_psw': a.TOTAL_PSW or 0,
                    'tingkat_tlm': a.TINGKAT_TLM or '',
                    'tingkat_psw': a.TINGKAT_PSW or '',
                    'persen_pot_tlm': a.PERSEN_POT_TLM or 0,
                    'persen_pot_psw': a.PERSEN_POT_PSW or 0,
                    'is_in_valid': (a.IS_INVALID or '').upper() == 'Y',
                    'is_out_valid': (a.IS_OUTVALID or '').upper() == 'Y',
                    'transaksi_in': a.TRANSAKSI_IN or '',
                    'transaksi_out': a.TRANSAKSI_OUT or '',
                    'pendukung_in': a.PENDUKUNG_IN or '',
                    'pendukung_out': a.PENDUKUNG_OUT or '',
                    'update_in_by': a.UPDATE_IN_BY or '',
                    'update_in_date': a.UPDATE_IN_DATE.strftime('%d/%m/%Y %H:%M') if a.UPDATE_IN_DATE else '',
                    'update_out_by': a.UPDATE_OUT_BY or '',
                    'update_out_date': a.UPDATE_OUT_DATE.strftime('%d/%m/%Y %H:%M') if a.UPDATE_OUT_DATE else '',
                }
            })
        
        # Kalau tidak ada di ABSENSI, coba cari di TIME_RECORDER
        tr = (
            TimeRecorder.query
            .filter(TimeRecorder.KET_INJECT == nip)
            .filter(TimeRecorder.MESIN == '999')
            .filter(db.func.date(TimeRecorder.WAKTU) == tgl_date.date())
            .order_by(TimeRecorder.WAKTU.asc())
            .all()
        )
        
        if tr:
            pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
            jam_in = ''
            jam_out = ''
            for t in tr:
                if t.STATUS == 'IN':
                    jam_in = t.WAKTU.strftime('%H:%M') if t.WAKTU else ''
                elif t.STATUS == 'OUT':
                    jam_out = t.WAKTU.strftime('%H:%M') if t.WAKTU else ''
            
            return jsonify({
                'success': True,
                'data': {
                    'finger_id': nip,
                    'nip': nip,
                    'nama': pegawai.NAMA if pegawai else '',
                    'tgl_kerja': tgl,
                    'jam_in': jam_in,
                    'jam_out': jam_out,
                    'jam_baku_in': '',
                    'jam_baku_out': '',
                    'ket_in': '',
                    'ket_out': '',
                    'awal_tlm': 0,
                    'total_tlm': 0,
                    'total_psw': 0,
                    'tingkat_tlm': '',
                    'tingkat_psw': '',
                    'persen_pot_tlm': 0,
                    'persen_pot_psw': 0,
                    'is_in_valid': True,
                    'is_out_valid': True,
                    'transaksi_in': 'MANUAL',
                    'transaksi_out': 'MANUAL',
                    'pendukung_in': 'Y',
                    'pendukung_out': 'Y',
                    'update_in_by': '',
                    'update_in_date': '',
                    'update_out_by': '',
                    'update_out_date': '',
                }
            })
        
        return jsonify({'success': True, 'data': None, 'message': 'Data tidak ditemukan'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'data': None})


def api_absensi_non_finger_koreksi():
    """API: Koreksi/Simulasi perhitungan TLM & PSW"""
    try:
        data = request.get_json()
        tgl = data.get('tgl', '')
        jam_in = data.get('jam_in', '')
        jam_out = data.get('jam_out', '')
        shift = data.get('shift', '1')
        
        if not tgl or not jam_in or not jam_out:
            return jsonify({'error': 'Data tidak lengkap'})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        
        # Ambil jam baku
        hari = tgl_date.weekday()
        shift_filter = '2' if hari == 4 else '1'  # Jumat = shift 2
        
        jam_kerja = (
            MfJamKerja.query
            .filter(MfJamKerja.TGL_MULAI_BERLAKU <= tgl_date)
            .filter(MfJamKerja.SHIFT == shift_filter)
            .filter(MfJamKerja.SHIFT_KERJA == shift)
            .order_by(MfJamKerja.TGL_MULAI_BERLAKU.desc())
            .first()
        )
        
        if not jam_kerja:
            return jsonify({'error': 'Jam kerja tidak ditemukan'})
        
        baku_in = jam_kerja.STD_JAM_IN
        baku_out = jam_kerja.STD_JAM_OUT
        
        # Parse jam
        tgl_base = datetime.combine(tgl_date, datetime.min.time())
        
        if hasattr(baku_in, 'time'):
            baku_in_dt = datetime.combine(tgl_date, baku_in.time()) if baku_in.time() else tgl_base
        else:
            baku_in_str = str(baku_in)[:8] if len(str(baku_in)) > 8 else str(baku_in)
            baku_in_dt = datetime.strptime(f"{tgl} {baku_in_str}", '%Y-%m-%d %H:%M:%S') if ':' in baku_in_str else tgl_base
        
        if hasattr(baku_out, 'time'):
            baku_out_dt = datetime.combine(tgl_date, baku_out.time()) if baku_out.time() else tgl_base
        else:
            baku_out_str = str(baku_out)[:8] if len(str(baku_out)) > 8 else str(baku_out)
            baku_out_dt = datetime.strptime(f"{tgl} {baku_out_str}", '%Y-%m-%d %H:%M:%S') if ':' in baku_out_str else tgl_base
        
        tgl_in = datetime.strptime(f"{tgl} {jam_in}", '%Y-%m-%d %H:%M')
        tgl_out = datetime.strptime(f"{tgl} {jam_out}", '%Y-%m-%d %H:%M')
        
        # Hitung TLM
        diff_in = tgl_in - baku_in_dt
        awal_tlm = diff_in.total_seconds() / 60
        if tgl_in < baku_in_dt:
            awal_tlm = awal_tlm * -1
        
        # Hitung PSW
        diff_out = tgl_out - baku_out_dt
        total_psw = diff_out.total_seconds() / 60
        if tgl_out < baku_out_dt:
            total_psw = total_psw * -1
        
        # Hitung Total TLM
        if awal_tlm > 0 and awal_tlm <= 30:
            total_tlm = awal_tlm - total_psw
        else:
            total_tlm = awal_tlm
        
        # Cek libur
        kalender = MfKalender.query.filter(
            db.func.date(MfKalender.TGL_KERJA) == tgl_date.date()
        ).first()
        
        is_libur = False
        if kalender:
            is_libur = kalender.IS_LIBUR == 'Y'
        elif tgl_date.weekday() >= 5:
            is_libur = True
        
        # Tentukan tingkat & potongan
        tingkat_tlm = ''
        persen_pot_tlm = 0
        tingkat_psw = ''
        persen_pot_psw = 0
        
        if not is_libur:
            # Cari di MFPot
            potongan = MfPot.query.filter(
                MfPot.KATEGORI.in_(['TLM', 'PSW']),
                MfPot.TGL_MULAI <= tgl_date
            ).all()
            
            for pot in potongan:
                if pot.KATEGORI == 'TLM' and pot.RANGE_AWAL is not None and pot.RANGE_AKHIR is not None:
                    if pot.RANGE_AWAL <= total_tlm <= pot.RANGE_AKHIR:
                        tingkat_tlm = pot.TINGKAT or ''
                        persen_pot_tlm = pot.PERSEN_POT or 0
                        break
                elif pot.KATEGORI == 'PSW' and pot.RANGE_AWAL is not None and pot.RANGE_AKHIR is not None:
                    if pot.RANGE_AWAL <= total_psw <= pot.RANGE_AKHIR:
                        tingkat_psw = pot.TINGKAT or ''
                        persen_pot_psw = pot.PERSEN_POT or 0
                        break
            
            # Default jika tidak ada di MFPot
            if not tingkat_tlm and total_tlm > 0:
                if total_tlm <= 30:
                    tingkat_tlm = 'TLM-1'
                    persen_pot_tlm = 0.5
                elif total_tlm <= 60:
                    tingkat_tlm = 'TLM-2'
                    persen_pot_tlm = 1
                elif total_tlm <= 90:
                    tingkat_tlm = 'TLM-3'
                    persen_pot_tlm = 1.25
                elif total_tlm > 90:
                    tingkat_tlm = 'TLM-4'
                    persen_pot_tlm = 1.5
            
            if not tingkat_psw and total_psw < 0:
                if total_psw >= -30:
                    tingkat_psw = 'PSW-1'
                    persen_pot_psw = 0.5
                elif total_psw >= -60:
                    tingkat_psw = 'PSW-2'
                    persen_pot_psw = 1
                elif total_psw >= -90:
                    tingkat_psw = 'PSW-3'
                    persen_pot_psw = 1.25
                elif total_psw < -90:
                    tingkat_psw = 'PSW-4'
                    persen_pot_psw = 1.5
        
        return jsonify({
            'success': True,
            'data': {
                'jam_baku_in': baku_in_dt.strftime('%H:%M') if baku_in_dt else '',
                'jam_baku_out': baku_out_dt.strftime('%H:%M') if baku_out_dt else '',
                'awal_tlm': round(awal_tlm, 2),
                'total_tlm': round(total_tlm, 2),
                'total_psw': round(total_psw, 2),
                'tingkat_tlm': tingkat_tlm,
                'tingkat_psw': tingkat_psw,
                'persen_pot_tlm': persen_pot_tlm,
                'persen_pot_psw': persen_pot_psw,
                'is_in_valid': True,
                'is_out_valid': True,
                'is_libur': is_libur,
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_absensi_non_finger_save():
    """API: Simpan absensi non finger (single record)"""
    try:
        data = request.get_json()
        nip = data.get('finger_id', '')  # ✅ Parameter bernama finger_id tapi isinya NIP
        tgl = data.get('tgl', '')
        jam_in = data.get('jam_in', '')
        jam_out = data.get('jam_out', '')
        shift = data.get('shift', '1')
        ket_in = data.get('ket_in', '')
        ket_out = data.get('ket_out', '')
        mode = data.get('mode', 0)  # 0=IN+OUT, 1=IN only, 2=OUT only
        
        if not nip or not tgl:
            return jsonify({'error': 'NIP dan Tanggal harus diisi'})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        
        # Hitung shift
        tgl_cek_in = tgl_date
        tgl_cek_out = tgl_date
        if shift == '2':
            tgl_cek_out = tgl_date + timedelta(days=1)
        
        # ✅ Delete existing manual record untuk NIP ini (via KET_INJECT)
        TimeRecorder.query.filter(
            TimeRecorder.KET_INJECT == nip,
            TimeRecorder.MESIN == '999',
            db.func.date(TimeRecorder.WAKTU) == tgl_date.date()
        ).delete()
        
        # Insert IN
        if (mode in [0, 1]) and jam_in:
            tgl_jam_in = datetime.strptime(f"{tgl_cek_in.strftime('%Y-%m-%d')} {jam_in}", '%Y-%m-%d %H:%M')
            tr_in = TimeRecorder(
                FINGER_ID=0,  # Placeholder karena kolom ini NOT NULL
                WAKTU=tgl_jam_in,
                STATUS='IN',
                MESIN='999',
                KET='MANUAL',
                TRANSAKSI='MANUAL',
                KET_INJECT=nip,  # ✅ Simpan NIP di sini
                UPDATE_IN_BY='admin',
                UPDATE_DATE=datetime.now()
            )
            db.session.add(tr_in)
        
        # Insert OUT
        if (mode in [0, 2]) and jam_out:
            tgl_jam_out = datetime.strptime(f"{tgl_cek_out.strftime('%Y-%m-%d')} {jam_out}", '%Y-%m-%d %H:%M')
            tr_out = TimeRecorder(
                FINGER_ID=0,
                WAKTU=tgl_jam_out,
                STATUS='OUT',
                MESIN='999',
                KET='MANUAL',
                TRANSAKSI='MANUAL',
                KET_INJECT=nip,  # ✅ Simpan NIP di sini
                UPDATE_IN_BY='admin',
                UPDATE_DATE=datetime.now()
            )
            db.session.add(tr_out)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data berhasil disimpan'})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_absensi_non_finger_delete():
    """API: Delete absensi non finger"""
    try:
        data = request.get_json()
        nip = data.get('finger_id', '')  # ✅ NIP
        tgl = data.get('tgl', '')
        
        if not nip or not tgl:
            return jsonify({'error': 'Data tidak lengkap'})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        
        # ✅ Delete by NIP di KET_INJECT
        result = TimeRecorder.query.filter(
            TimeRecorder.KET_INJECT == nip,
            TimeRecorder.MESIN == '999',
            db.func.date(TimeRecorder.WAKTU) == tgl_date.date(),
            TimeRecorder.TRANSAKSI == 'MANUAL'
        ).delete()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{result} data berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


def data_absensi_normalisasi_finger():
    """
    Render halaman Data Absensi Normalisasi Absensi Finger.
    """
    return render_template('pages/dashboard_1/Data Absensi Normalisasi Absensi Finger.html')

def data_absensi_impor_file():
    return render_template(
        'pages/dashboard_1/Data Absensi Impor File.html'
    )


def api_normalisasi_get_fields():
    """
    API: daftar field yang bisa dipakai untuk filter (dropdown "- Pilih Field -").
    Menggantikan dbMf.daMFFieldCari("EntryPeg") di VB.NET.
    """
    fields = [
        {'field_id': 'NIP', 'field_name': 'NIP'},
        {'field_id': 'Nama', 'field_name': 'Nama'},
        {'field_id': 'UnitKerjaName', 'field_name': 'Unit Kerja'},
    ]
    return jsonify({'success': True, 'data': fields})


def api_normalisasi_import_finger():
    """
    TAB 1 - VIEW DATA.

    Sumber data:
        FINGER_HARVEST_RAW

    Data ini dapat berasal dari:
        1. HRIS Finger Collector / mesin finger
        2. Import file .DAT

    VIEW DATA hanya membaca RAW.
    Tidak melakukan normalisasi dan tidak mengubah ABSENSI.
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')

        if not tgl_awal_str or not tgl_akhir_str:
            return jsonify({
                'error': 'Tanggal periode kosong',
                'data': []
            })

        tgl_awal = datetime.strptime(
            tgl_awal_str,
            '%Y-%m-%d'
        )

        tgl_akhir = (
            datetime.strptime(
                tgl_akhir_str,
                '%Y-%m-%d'
            )
            + timedelta(days=1)
        )

        sql = text("""
            SELECT
                r.ID,
                r.FINGER_ID,
                r.USER_ID,
                r.WAKTU,
                r.STATUS,
                r.PUNCH,
                r.DEVICE_IP,
                p.NIP,
                p.Nama AS NAMA,
                p.Gol AS GOL,
                p.UnitKerja AS UNIT_KERJA
            FROM FINGER_HARVEST_RAW r
            INNER JOIN PEGAWAI p
                ON CAST(r.USER_ID AS CHAR)
                 = CAST(p.FingerID AS CHAR)
            WHERE r.WAKTU >= :tgl_awal
              AND r.WAKTU < :tgl_akhir
        """)

        params = {
            'tgl_awal': tgl_awal,
            'tgl_akhir': tgl_akhir,
        }

        conditions = []

        field_mapping = {
            'NIP': 'p.NIP',
            'Nama': 'p.Nama',
            'UnitKerjaName': 'p.UnitKerja',
        }

        if filter_field1 and filter_value1:
            field = field_mapping.get(filter_field1)
            if field:
                conditions.append(
                    f"{field} LIKE :filter_value1"
                )
                params['filter_value1'] = (
                    f"%{filter_value1}%"
                )

        if filter_field2 and filter_value2:
            field = field_mapping.get(filter_field2)
            if field:
                conditions.append(
                    f"{field} LIKE :filter_value2"
                )
                params['filter_value2'] = (
                    f"%{filter_value2}%"
                )

        if conditions:
            sql = text("""
                SELECT
                    r.ID,
                    r.FINGER_ID,
                    r.USER_ID,
                    r.WAKTU,
                    r.STATUS,
                    r.PUNCH,
                    r.DEVICE_IP,
                    p.NIP,
                    p.Nama AS NAMA,
                    p.Gol AS GOL,
                    p.UnitKerja AS UNIT_KERJA
                FROM FINGER_HARVEST_RAW r
                INNER JOIN PEGAWAI p
                    ON CAST(r.USER_ID AS CHAR)
                     = CAST(p.FingerID AS CHAR)
                WHERE r.WAKTU >= :tgl_awal
                  AND r.WAKTU < :tgl_akhir
                  AND """ + " AND ".join(conditions) + """
                ORDER BY CAST(p.UnitKerja AS UNSIGNED), r.FINGER_ID, r.WAKTU
            """)
        else:
            sql = text("""
                SELECT
                    r.ID,
                    r.FINGER_ID,
                    r.USER_ID,
                    r.WAKTU,
                    r.STATUS,
                    r.PUNCH,
                    r.DEVICE_IP,
                    p.NIP,
                    p.Nama AS NAMA,
                    p.Gol AS GOL,
                    p.UnitKerja AS UNIT_KERJA
                FROM FINGER_HARVEST_RAW r
                INNER JOIN PEGAWAI p
                    ON CAST(r.USER_ID AS CHAR)
                     = CAST(p.FingerID AS CHAR)
                WHERE r.WAKTU >= :tgl_awal
                  AND r.WAKTU < :tgl_akhir
                ORDER BY CAST(p.UnitKerja AS UNSIGNED), r.FINGER_ID, r.WAKTU
            """)

        rows = db.session.execute(
            sql,
            params
        ).mappings().all()

        data = []
        cache_rows = []

        for i, r in enumerate(rows, 1):
            status = str(
                r['STATUS'] or ''
            ).strip().upper()

            if status not in ('IN', 'OUT'):
                if r['PUNCH'] == 0:
                    status = 'IN'
                elif r['PUNCH'] == 1:
                    status = 'OUT'

            row = {
                'no': i,
                'finger_id': str(
                    r['FINGER_ID'] or ''
                ),
                'nip': r['NIP'] or '',
                'nama': r['NAMA'] or '',
                'gol': r['GOL'] or '',
                'unit_kerja': r['UNIT_KERJA'] or '',
                'waktu': (
                    r['WAKTU'].strftime(
                        '%Y-%m-%d %H:%M:%S'
                    )
                    if r['WAKTU']
                    else ''
                ),
                'status': status,
                'punch': r['PUNCH'],
                'device_ip': r['DEVICE_IP'] or '',
                'transaksi': (
                    r['STATUS'] or status
                ),
            }

            data.append(row)
            cache_rows.append(row)

        _NORMALISASI_CACHE['import'] = cache_rows

        if not data:
            return jsonify({
                'success': True,
                'data': [],
                'total': 0,
                'message': 'Data Log Finger Print Kosong'
            })

        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            'error': str(e),
            'data': []
        })


def api_normalisasi_process():
    """
    TAB 2 - Normalisasi.
    Hitung TLM (terlambat) & PSW (pulang sebelum waktunya) per pegawai per hari,
    berdasarkan data yang sudah diimport (tab 1) dan jam kerja standar (MfJamKerja).

    NOTE: ini versi disederhanakan dari logic VB.NET asli (yang menangani shift 2 / siaga
    / VIP secara sangat detail). Di sini hanya menangani 1 shift standar per hari.
    """
    try:
        data = request.get_json()
        default_tdk_check = data.get('default_tdk_check', 180)  # RNQtyIn di VB.NET
        tgl_awal_str = data.get('tgl_awal', '')
        tgl_akhir_str = data.get('tgl_akhir', '')

        filter_field1 = str(data.get('filter_field1') or '').strip()
        filter_value1 = str(data.get('filter_value1') or '').strip()
        filter_field2 = str(data.get('filter_field2') or '').strip()
        filter_value2 = str(data.get('filter_value2') or '').strip()

        if not default_tdk_check:
            return jsonify({'error': 'Nilai default TLM/PSW tdk check in/out kosong'})
        if not tgl_awal_str or not tgl_akhir_str:
            return jsonify({'error': 'Tanggal periode kosong'})

        xdefault = float(default_tdk_check) + 1
        tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
        tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d')

        # ============================================================
        # SUMBER NORMALISASI:
        # FINGER_HARVEST_RAW
        #
        # Jangan lagi bergantung pada _NORMALISASI_CACHE['import'].
        # RAW adalah sumber permanen hasil import file .DAT.
        # ============================================================

        from sqlalchemy import text

        # ============================================================
        # FILTER DARI TAB FROM DATABASE
        #
        # Filter yang dipilih user harus ikut terbawa ke NORMALISASI.
        # Gunakan whitelist kolom agar nama field tidak menjadi SQL
        # injection.
        # ============================================================

        filter_column_map = {
            'NIP': 'p.NIP',
            'Nama': 'p.Nama',
            'NAMA': 'p.Nama',
            'UnitKerja': 'p.UnitKerja',
            'Unit Kerja': 'p.UnitKerja',
            'Gol': 'p.Gol',
            'Gol-Pangkat': 'p.Gol',
        }

        filter_clauses = []
        filter_params = {}

        for idx, (field, value) in enumerate(
            (
                (filter_field1, filter_value1),
                (filter_field2, filter_value2),
            ),
            start=1
        ):
            column = filter_column_map.get(field)

            if column and value:
                param_name = f'filter_value{idx}'
                filter_clauses.append(
                    f"AND {column} LIKE :{param_name}"
                )
                filter_params[param_name] = f'%{value}%'

        filter_sql = ''
        if filter_clauses:
            filter_sql = '\n              ' + '\n              '.join(
                filter_clauses
            )

        raw_sql = text(f"""
            SELECT
                r.FINGER_ID,
                r.USER_ID,
                r.WAKTU,
                r.STATUS,
                r.PUNCH,
                r.DEVICE_IP,
                p.NIP,
                p.Nama AS NAMA,
                p.Gol AS GOL,
                p.UnitKerja AS UNIT_KERJA
            FROM FINGER_HARVEST_RAW r
            INNER JOIN PEGAWAI p
                ON CAST(r.USER_ID AS CHAR) = CAST(p.FingerID AS CHAR)
            WHERE r.WAKTU >= :tgl_awal_raw
              AND r.WAKTU < :tgl_akhir_raw
              {filter_sql}
            ORDER BY CAST(p.UnitKerja AS UNSIGNED), r.FINGER_ID, r.WAKTU
        """)

        query_params = {
            # Shift 2 Siaga membutuhkan fingerprint
            # mulai dari malam tanggal sebelumnya.
            'tgl_awal_raw': tgl_awal - timedelta(days=1),
            'tgl_akhir_raw': tgl_akhir + timedelta(days=1),
            **filter_params,
        }

        raw_rows = db.session.execute(
            raw_sql,
            query_params
        ).mappings().all()

        if not raw_rows:
            return jsonify({
                'error': (
                    'Data FINGER_HARVEST_RAW kosong '
                    'untuk periode yang dipilih.'
                )
            })

        # ============================================================
        # Kelompokkan log per (finger_id, tanggal)
        # ============================================================

        grouped = defaultdict(list)

        for r in raw_rows:
            waktu = r['WAKTU']

            if not waktu:
                continue

            status = str(r['STATUS'] or '').strip().upper()
            punch = r['PUNCH']

            # PUNCH adalah sumber utama arah fingerprint:
            #   0 = IN / MASUK
            #   1 = OUT / PULANG
            #
            # STATUS pada RAW dapat berupa kode numerik dari mesin,
            # sehingga jangan digunakan untuk menentukan arah.
            if punch == 0:
                status = 'IN'
            elif punch == 1:
                status = 'OUT'
            elif status not in ('IN', 'OUT'):
                status = None

            grouped[
                (
                    str(r['FINGER_ID']),
                    waktu.strftime('%Y-%m-%d')
                )
            ].append({
                'finger_id': str(r['FINGER_ID']),
                'nip': r['NIP'] or '',
                'nama': r['NAMA'] or '',
                'gol': r['GOL'] or '',
                'unit_kerja': r['UNIT_KERJA'] or '',
                'waktu': waktu.strftime('%Y-%m-%d %H:%M:%S'),
                'status': status,
                'punch': r['PUNCH'],
                'device_ip': r['DEVICE_IP'] or '',
            })

        if not grouped:
            return jsonify({
                'error': (
                    'Tidak ada log fingerprint valid '
                    'yang dapat dinormalisasi.'
                )
            })

        # ============================================================
        # SHIFT 2 SIAGA
        #
        # Penentuan Shift 2 TIDAK berasal dari MF_JAM_KERJA.
        #
        # Shift 2 ditentukan oleh:
        #   LOG_ACTIVITIY
        #   Activity = Piket Siaga
        #   Shift = 2
        #
        # ActivityDate adalah tanggal SIAGA.
        # Kehadiran fingerprint Shift 2 menjadi ABSENSI
        # pada HARI BERIKUTNYA.
        #
        # StatusID = 3 / shift2 = 1
        #     -> hadir dan boleh dinormalisasi
        #
        # Selain itu
        #     -> fingerprint tetap berada di RAW,
        #        tetapi TIDAK masuk ABSENSI.
        # ============================================================

        shift2_sql = text("""
            SELECT
                NIP,
                ActivityDate,
                StatusID,
                shift2,
                Shift,
                GUIDTim,
                Fungsional,
                IDUnitKerja
            FROM LOG_ACTIVITIY
            WHERE Activity = 'Piket Siaga'
              AND Shift = '2'
              AND ActivityDate >= :activity_awal
              AND ActivityDate <= :activity_akhir
        """)

        shift2_rows = db.session.execute(
            shift2_sql,
            {
                'activity_awal': (tgl_awal - timedelta(days=1)).date(),
                'activity_akhir': (tgl_akhir - timedelta(days=1)).date(),
            }
        ).mappings().all()

        # key:
        #   (NIP, tanggal_absensi)
        #
        # value:
        #   {
        #       hadir: True/False,
        #       activity_date: tanggal siaga
        #   }
        shift2_map = {}

        for sr in shift2_rows:
            nip_siaga = str(sr['NIP'] or '').strip()

            if not nip_siaga or not sr['ActivityDate']:
                continue

            activity_date = sr['ActivityDate']

            if hasattr(activity_date, 'date'):
                activity_date = activity_date.date()

            target_date = activity_date + timedelta(days=1)

            # Kehadiran Shift 2 ditentukan oleh checkbox lama:
            #
            # STATUS_ID = 3
            # atau
            # SHIFT_2 = 1
            #
            hadir_shift2 = (
                int(sr['shift2'] or 0) == 1
            )

            shift2_map[
                (nip_siaga, target_date.strftime('%Y-%m-%d'))
            ] = {
                'hadir': hadir_shift2,
                'activity_date': activity_date,
                'guid_tim': sr['GUIDTim'],
                'fungsional': sr['Fungsional'],
                'unit_kerja_id': sr['IDUnitKerja'],
            }

        # Index RAW berdasarkan NIP.
        #
        # Kita sengaja tidak memakai tanggal sebagai satu-satunya
        # grouping karena Shift 2 mengambil IN dari H-1 dan OUT dari H.
        raw_by_nip = defaultdict(list)

        for r in raw_rows:
            nip_raw = str(r['NIP'] or '').strip()

            if not nip_raw:
                continue

            raw_by_nip[nip_raw].append(r)

        # Ambil kalender & jam kerja & MfPot sekali saja
        kalender_rows = MfKalender.query.filter(
            MfKalender.TGL_KERJA.between(tgl_awal, tgl_akhir)
        ).all()
        kalender_map = {k.TGL_KERJA.strftime('%Y-%m-%d'): k.IS_LIBUR for k in kalender_rows}

        jam_kerja_list = (
            MfJamKerja.query
            .filter(MfJamKerja.TGL_MULAI_BERLAKU <= tgl_akhir)
            .order_by(MfJamKerja.TGL_MULAI_BERLAKU.desc())
            .all()
        )
        potongan_list = MfPot.query.filter(
            MfPot.KATEGORI.in_(['TLM', 'PSW']),
            MfPot.TGL_MULAI <= tgl_akhir
        ).all()

        def get_jam_kerja(tgl_dt, shift_kerja='1'):
            # MF_JAM_KERJA:
            #   Shift      = 1 -> Senin-Kamis
            #   Shift      = 2 -> Jumat
            #   ShiftKerja = 1 -> Shift 1 / pegawai umum
            #   ShiftKerja = 2 -> Shift 2 / petugas siaga
            #
            # Ambil konfigurasi TERBARU yang sudah berlaku
            # pada tanggal absensi.

            shift_hari = (
                '2'
                if tgl_dt.weekday() == 4
                else '1'
            )

            kandidat = [
                jk
                for jk in jam_kerja_list
                if (
                    str(jk.SHIFT or '') == shift_hari
                    and str(jk.SHIFT_KERJA or '') == str(shift_kerja)
                    and jk.TGL_MULAI_BERLAKU is not None
                    and jk.TGL_MULAI_BERLAKU <= tgl_dt
                )
            ]

            if not kandidat:
                return None

            # Konfigurasi paling akhir adalah yang berlaku.
            kandidat.sort(
                key=lambda jk: (
                    jk.TGL_MULAI_BERLAKU,
                    jk.IDJKERJA or 0
                ),
                reverse=True
            )

            return kandidat[0]

        def hitung_potongan(total_tlm, total_psw, tgl_dt):
            tk_tlm, pot_tlm, tk_psw, pot_psw = '', 0, '', 0
            for pot in potongan_list:
                if pot.TGL_MULAI and pot.TGL_MULAI > tgl_dt:
                    continue
                if pot.KATEGORI == 'TLM' and pot.RANGE_AWAL is not None and pot.RANGE_AWAL <= total_tlm <= pot.RANGE_AKHIR:
                    tk_tlm, pot_tlm = pot.TINGKAT or '', pot.PERSEN_POT or 0
                elif pot.KATEGORI == 'PSW' and pot.RANGE_AWAL is not None and pot.RANGE_AWAL <= total_psw <= pot.RANGE_AKHIR:
                    tk_psw, pot_psw = pot.TINGKAT or '', pot.PERSEN_POT or 0
            # fallback default tier kalau tidak ada di MfPot
            if not tk_tlm and total_tlm > 0:
                if total_tlm <= 30: tk_tlm, pot_tlm = 'TLM-1', 0.5
                elif total_tlm <= 60: tk_tlm, pot_tlm = 'TLM-2', 1
                elif total_tlm <= 90: tk_tlm, pot_tlm = 'TLM-3', 1.25
                else: tk_tlm, pot_tlm = 'TLM-4', 1.5
            if not tk_psw and total_psw < 0:
                if total_psw >= -30: tk_psw, pot_psw = 'PSW-1', 0.5
                elif total_psw >= -60: tk_psw, pot_psw = 'PSW-2', 1
                elif total_psw >= -90: tk_psw, pot_psw = 'PSW-3', 1.25
                else: tk_psw, pot_psw = 'PSW-4', 1.5
            return tk_tlm, pot_tlm, tk_psw, pot_psw

        # ============================================================
        # ENGINE NORMALISASI
        #
        # JALUR 1 : ABSENSI REGULER
        #   fingerprint tanggal H
        #   -> ABSENSI tanggal H
        #
        # JALUR 2 : SHIFT 2 SIAGA
        #   ActivityDate H
        #   -> fingerprint IN H malam
        #   -> fingerprint OUT H+1 pagi
        #   -> ABSENSI tanggal H+1
        #
        # Shift 2 hanya boleh masuk apabila operator mencentang
        # kehadiran Shift 2 pada menu Absensi Kehadiran Siaga.
        #
        # Fingerprint Shift 2 yang tidak dicentang:
        #   tetap tersimpan di FINGER_HARVEST_RAW
        #   tetapi tidak menghasilkan ABSENSI.
        # ============================================================

        result = []
        no = 0

        # ============================================================
        # HELPER PEMBUAT ROW
        # ============================================================

        def build_normal_row(
            nip,
            finger_id,
            nama,
            gol,
            unit_kerja,
            tgl_kerja,
            jam_in_dt,
            jam_out_dt,
            jk,
            is_libur,
        ):
            nonlocal no

            if not jk:
                return None

            baku_in_time = (
                jk.STD_JAM_IN.time()
                if jk.STD_JAM_IN
                else None
            )

            baku_out_time = (
                jk.STD_JAM_OUT.time()
                if jk.STD_JAM_OUT
                else None
            )

            baku_in = (
                datetime.combine(tgl_kerja, baku_in_time)
                if baku_in_time
                else tgl_kerja
            )

            baku_out = (
                datetime.combine(tgl_kerja, baku_out_time)
                if baku_out_time
                else tgl_kerja
            )

            # --------------------------------------------------------
            # SHIFT MALAM
            # --------------------------------------------------------

            if (
                baku_in_time
                and baku_out_time
                and baku_out_time <= baku_in_time
            ):
                baku_out += timedelta(days=1)

            # --------------------------------------------------------
            # TLM
            #
            # Datang lebih awal / tepat waktu:
            #   TLM = 0
            #
            # Datang terlambat:
            #   TLM = selisih menit positif
            # --------------------------------------------------------

            if jam_in_dt:
                selisih_in = (
                    jam_in_dt - baku_in
                ).total_seconds() / 60

                awal_tlm = max(0, selisih_in)

                row_jam_in = jam_in_dt.strftime('%H:%M:%S')
                is_valid_in = True
            else:
                awal_tlm = xdefault
                row_jam_in = '00:00:00'
                is_valid_in = False

            # --------------------------------------------------------
            # PSW
            #
            # Pulang tepat / lebih lambat:
            #   PSW = 0
            #
            # Pulang lebih awal:
            #   PSW = selisih menit negatif
            # --------------------------------------------------------

            if jam_out_dt:
                selisih_out = (
                    jam_out_dt - baku_out
                ).total_seconds() / 60

                total_psw = min(0, selisih_out)

                # Waktu pulang setelah jam baku adalah kelebihan
                # waktu yang hanya boleh dipakai untuk kompensasi
                # TLM-1.
                tambahan_pulang = max(0, selisih_out)

                row_jam_out = jam_out_dt.strftime('%H:%M:%S')
                is_valid_out = True
            else:
                total_psw = -1 * xdefault
                tambahan_pulang = 0
                row_jam_out = '00:00:00'
                is_valid_out = False

            # --------------------------------------------------------
            # PENGGANTIAN TLM-1
            #
            # HANYA TLM-1 (<= 30 menit) yang boleh diganti
            # dengan kelebihan waktu pulang.
            #
            # TLM-2 / TLM-3 / TLM-4 tidak boleh diganti.
            # --------------------------------------------------------

            penggantian_ok = (
                (jk.PENGGANTIAN_TLM1 or 'Y').upper() != 'N'
            )

            if (
                not is_libur
                and 0 < awal_tlm <= 30
                and penggantian_ok
            ):
                total_tlm = max(
                    0,
                    awal_tlm - tambahan_pulang
                )
            else:
                total_tlm = awal_tlm
                total_tlm = awal_tlm

            tk_tlm, pot_tlm, tk_psw, pot_psw = (
                ('', 0, '', 0)
                if is_libur
                else hitung_potongan(
                    total_tlm,
                    total_psw,
                    tgl_kerja,
                )
            )

            no += 1

            return {
                'no': no,
                'finger_id': finger_id,
                'nip': nip,
                'nama': nama,
                'tgl_kerja': tgl_kerja.strftime('%Y-%m-%d'),
                'hari': tgl_kerja.strftime('%A'),
                'jam_baku_in': baku_in.strftime('%H:%M'),
                'jam_baku_out': baku_out.strftime('%H:%M'),
                'jam_in': row_jam_in,
                'jam_out': row_jam_out,
                'is_valid_in': is_valid_in,
                'is_valid_out': is_valid_out,
                'is_libur': (
                    'LIBUR'
                    if is_libur
                    else 'TDKLIBUR'
                ),
                'awal_tlm': round(awal_tlm, 2),
                'total_tlm': round(total_tlm, 2),
                'tingkat_tlm': tk_tlm,
                'persen_pot_tlm': pot_tlm,
                'total_psw': round(total_psw, 2),
                'tingkat_psw': tk_psw,
                'persen_pot_psw': pot_psw,
                'gol': gol,
                'unit_kerja': unit_kerja,
            }

        # ============================================================
        # 1. SHIFT 2 SIAGA
        # ============================================================

        shift2_consumed = set()

        for (nip_siaga, target_date_str), info in shift2_map.items():

            # --------------------------------------------------------
            # Hanya yang dicentang operator.
            # --------------------------------------------------------

            if not info['hadir']:
                continue

            target_date = datetime.strptime(
                target_date_str,
                '%Y-%m-%d'
            )

            activity_date = info['activity_date']

            raw_person = raw_by_nip.get(
                nip_siaga,
                []
            )

            if not raw_person:
                continue

            # --------------------------------------------------------
            # Shift 2:
            #
            # IN  = window fingerprint Shift 2 pada tanggal SIAGA
            # OUT = window fingerprint Shift 2 pada tanggal BERIKUTNYA
            #
            # Window mengikuti MF_LOAD_FINGER / SHIFT_KERJA = '2'.
            # --------------------------------------------------------

            load_finger_rows = (
                MfLoadFinger.query
                .filter(
                    MfLoadFinger.SHIFT_KERJA == '2',
                    MfLoadFinger.TGL_MULAI_BERLAKU <= target_date.date(),
                )
                .order_by(
                    MfLoadFinger.TGL_MULAI_BERLAKU.desc()
                )
                .all()
            )

            load_finger = (
                load_finger_rows[0]
                if load_finger_rows
                else None
            )

            if not load_finger:
                continue

            def combine_config_time(base_date, value):
                if value is None:
                    return None

                return datetime.combine(
                    base_date,
                    value.time()
                )

            start_in = combine_config_time(
                activity_date,
                load_finger.START_FINGER
            )

            end_in = combine_config_time(
                activity_date,
                load_finger.END_FINGER
            )

            start_out = combine_config_time(
                target_date.date(),
                load_finger.START_FINGER_OUT
            )

            end_out = combine_config_time(
                target_date.date(),
                load_finger.END_FINGER_OUT
            )

            shift2_in = []
            shift2_out = []

            for raw in raw_person:

                waktu = raw['WAKTU']

                if not waktu:
                    continue

                # IN Shift 2:
                # tanggal siaga + window MF_LOAD_FINGER
                if (
                    raw['PUNCH'] == 0
                    and start_in is not None
                    and end_in is not None
                    and start_in <= waktu <= end_in
                ):
                    shift2_in.append(raw)

                # OUT Shift 2:
                # tanggal berikutnya + window MF_LOAD_FINGER
                elif (
                    raw['PUNCH'] == 1
                    and start_out is not None
                    and end_out is not None
                    and start_out <= waktu <= end_out
                ):
                    shift2_out.append(raw)

            shift2_in.sort(
                key=lambda r: r['WAKTU']
            )

            shift2_out.sort(
                key=lambda r: r['WAKTU']
            )

            jam_in_dt = (
                shift2_in[0]['WAKTU']
                if shift2_in
                else None
            )

            jam_out_dt = (
                shift2_out[-1]['WAKTU']
                if shift2_out
                else None
            )

            # --------------------------------------------------------
            # Kalau tidak ada satupun fingerprint Shift 2,
            # jangan membuat row.
            # --------------------------------------------------------

            if not jam_in_dt and not jam_out_dt:
                continue

            # --------------------------------------------------------
            # Master pegawai
            # --------------------------------------------------------

            source_raw = (
                shift2_in[0]
                if shift2_in
                else shift2_out[-1]
            )

            finger_id = str(
                source_raw['FINGER_ID']
            )

            nama = source_raw['NAMA'] or ''
            gol = source_raw['GOL'] or ''
            unit_kerja = source_raw['UNIT_KERJA'] or ''

            # --------------------------------------------------------
            # Jam kerja Shift 2 Siaga selalu:
            #
            # standar IN  = 19:30
            # standar OUT = 04:00 / 04:30
            #
            # Pemilihan ShiftKerja mengikuti data MF_JAM_KERJA.
            #
            # Untuk saat ini gunakan konfigurasi malam terbaru.
            # --------------------------------------------------------

            jam_malam = None

            for kandidat in jam_kerja_list:
                if str(kandidat.SHIFT_KERJA or '') == '2':
                    if kandidat.TGL_MULAI_BERLAKU <= target_date:
                        jam_malam = kandidat
                        break

            if not jam_malam:
                for kandidat in jam_kerja_list:
                    if kandidat.STD_JAM_IN:
                        if kandidat.STD_JAM_IN.hour >= 18:
                            jam_malam = kandidat
                            break

            if not jam_malam:
                continue

            # --------------------------------------------------------
            # Jam kerja dihitung pada TANGGAL ABSENSI (H+1).
            #
            # IN aktual tetap berasal dari H malam.
            # --------------------------------------------------------

            row = build_normal_row(
                nip=nip_siaga,
                finger_id=finger_id,
                nama=nama,
                gol=gol,
                unit_kerja=unit_kerja,
                tgl_kerja=target_date,
                jam_in_dt=jam_in_dt,
                jam_out_dt=jam_out_dt,
                jk=jam_malam,
                is_libur=(
                    kalender_map.get(
                        target_date.strftime('%Y-%m-%d'),
                        'N'
                    ) == 'Y'
                ),
            )

            if row:
                row['shift'] = '2'
                row['shift2_siaga'] = True
                row['activity_date_siaga'] = (
                    activity_date.strftime('%Y-%m-%d')
                )

                result.append(row)

                # Tandai fingerprint yang sudah dipakai
                for raw in shift2_in:
                    shift2_consumed.add(
                        id(raw)
                    )

                for raw in shift2_out:
                    shift2_consumed.add(
                        id(raw)
                    )

        # ============================================================
        # 2. ABSENSI REGULER
        #
        # Shift 2 yang sudah dipakai di atas tidak boleh diproses lagi.
        # ============================================================

        for (finger_id, tgl_str), logs in grouped.items():

            tgl_dt = datetime.strptime(
                tgl_str,
                '%Y-%m-%d'
            )

            # --------------------------------------------------------
            # Jangan proses fingerprint yang sudah menjadi Shift 2.
            # --------------------------------------------------------

            filtered_logs = [
                raw
                for raw in logs
                if id(raw) not in shift2_consumed
            ]

            if not filtered_logs:
                continue

            # --------------------------------------------------------
            # Jika fingerprint berasal dari Shift 2 yang TIDAK
            # dicentang, jangan tampilkan sebagai absensi reguler.
            #
            # Cari apakah NIP + tanggal ini memiliki konfigurasi
            # Shift 2 siaga tetapi tidak hadir.
            # --------------------------------------------------------

            nip_reguler = str(
                filtered_logs[0]['nip'] or ''
            ).strip()

            if (
                nip_reguler,
                tgl_str
            ) in shift2_map:
                info = shift2_map[
                    (nip_reguler, tgl_str)
                ]

                if not info['hadir']:
                    # Fingerprint tetap RAW, tetapi tidak masuk
                    # normalisasi/ABSENSI.
                    continue

            is_libur = (
                kalender_map.get(
                    tgl_str,
                    'N'
                ) == 'Y'
            )

            if (
                kalender_map.get(tgl_str) is None
                and tgl_dt.weekday() >= 5
            ):
                is_libur = True

            jk = get_jam_kerja(tgl_dt, '1')

            if not jk:
                continue

            logs_in = sorted(
                [
                    l for l in filtered_logs
                    if l.get('punch') == 0
                ],
                key=lambda l: l['waktu']
            )

            logs_out = sorted(
                [
                    l for l in filtered_logs
                    if l.get('punch') == 1
                ],
                key=lambda l: l['waktu']
            )

            jam_in_dt = (
                datetime.strptime(
                    logs_in[0]['waktu'],
                    '%Y-%m-%d %H:%M:%S'
                )
                if logs_in
                else None
            )

            jam_out_dt = (
                datetime.strptime(
                    logs_out[-1]['waktu'],
                    '%Y-%m-%d %H:%M:%S'
                )
                if logs_out
                else None
            )

            source_raw = filtered_logs[0]

            row = build_normal_row(
                nip=nip_reguler,
                finger_id=finger_id,
                nama=source_raw.get('nama') or source_raw.get('NAMA') or '',
                gol=source_raw.get('gol') or source_raw.get('GOL') or '',
                unit_kerja=source_raw.get('unit_kerja') or source_raw.get('UNIT_KERJA') or '',
                tgl_kerja=tgl_dt,
                jam_in_dt=jam_in_dt,
                jam_out_dt=jam_out_dt,
                jk=jk,
                is_libur=is_libur,
            )

            if row:
                row['shift'] = '1'
                row['shift2_siaga'] = False
                row['activity_date_siaga'] = None

                result.append(row)

        def _normalisasi_sort_key(r):
            unit = str(
                r.get('unit_kerja') or ''
            ).strip()

            try:
                unit_num = int(unit)
            except (TypeError, ValueError):
                unit_num = 999999

            return (
                unit_num,
                str(r.get('finger_id') or ''),
                r.get('tgl_kerja') or ''
            )

        result.sort(key=_normalisasi_sort_key)
        for i, r in enumerate(result, 1):
            r['no'] = i

        _NORMALISASI_CACHE['normal'] = result
        _NORMALISASI_CACHE['normal_tgl_awal'] = tgl_awal_str
        _NORMALISASI_CACHE['normal_tgl_akhir'] = tgl_akhir_str

        return jsonify({
            'success': True,
            'data': result,
            'total': len(result)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_normalisasi_export():
    """
    TAB 2 - tombol EXPORT.

    Simpan hasil normalisasi ke tabel ABSENSI
    dengan mekanisme INSERT / UPDATE.

    Hanya pegawai yang memiliki NIP yang boleh
    masuk ke ABSENSI.
    """
    try:
        # --------------------------------------------------------
        # EXPORT menggunakan hasil NORMALISASI yang dikirim
        # langsung dari browser.
        #
        # Jangan bergantung pada _NORMALISASI_CACHE karena
        # Gunicorn menggunakan lebih dari satu worker.
        # --------------------------------------------------------

        data = request.get_json(silent=True) or {}

        tgl_awal_export = str(
            data.get('tgl_awal') or ''
        ).strip()

        tgl_akhir_export = str(
            data.get('tgl_akhir') or ''
        ).strip()

        rows = data.get('rows') or []

        if not tgl_awal_export or not tgl_akhir_export:
            return jsonify({
                'error': 'Periode export kosong.'
            })

        if not isinstance(rows, list) or not rows:
            return jsonify({
                'error': (
                    'Tidak ada hasil normalisasi untuk diekspor. '
                    'Silakan lakukan NORMALISASI terlebih dahulu.'
                )
            })

            return jsonify({
                'error': (
                    'Tidak ada data hasil normalisasi. '
                    'Jalankan Normalisasi dulu.'
                )
            })

        saved = 0
        skipped = 0
        exported_rows = []

        for r in rows:

            # --------------------------------------------------------
            # Pegawai tanpa NIP tidak boleh masuk ABSENSI.
            # --------------------------------------------------------

            nip = str(r.get('nip') or '').strip()

            if not nip:
                skipped += 1
                continue

            # --------------------------------------------------------
            # Validasi tanggal kerja.
            # --------------------------------------------------------

            tgl_kerja_str = str(
                r.get('tgl_kerja') or ''
            ).strip()

            if not tgl_kerja_str:
                skipped += 1
                continue

            tgl_kerja = datetime.strptime(
                tgl_kerja_str,
                '%Y-%m-%d'
            )

            # --------------------------------------------------------
            # Jam aktual.
            #
            # Normalisasi menggunakan 00:00:00 untuk fingerprint
            # yang tidak ada. Tetap pertahankan perilaku lama.
            # --------------------------------------------------------

            jam_in = str(
                r.get('jam_in') or '00:00:00'
            )

            jam_out = str(
                r.get('jam_out') or '00:00:00'
            )

            tgl_jam_in = datetime.strptime(
                f"{tgl_kerja_str} {jam_in}",
                '%Y-%m-%d %H:%M:%S'
            )

            tgl_jam_out = datetime.strptime(
                f"{tgl_kerja_str} {jam_out}",
                '%Y-%m-%d %H:%M:%S'
            )

            # --------------------------------------------------------
            # Jam baku.
            # --------------------------------------------------------

            tgl_jam_baku_in = datetime.strptime(
                f"{tgl_kerja_str} {r['jam_baku_in']}",
                '%Y-%m-%d %H:%M'
            )

            tgl_jam_baku_out = datetime.strptime(
                f"{tgl_kerja_str} {r['jam_baku_out']}",
                '%Y-%m-%d %H:%M'
            )

            # --------------------------------------------------------
            # Cari ABSENSI existing berdasarkan FINGER_ID + tanggal.
            # --------------------------------------------------------

            existing = Absensi.query.filter(
                Absensi.FINGER_ID == r['finger_id'],
                db.func.date(
                    Absensi.TGL_KERJA
                ) == tgl_kerja.date()
            ).first()

            if existing:
                existing.TGL_JAM_IN = tgl_jam_in
                existing.TGL_JAM_OUT = tgl_jam_out
                existing.TRANSAKSI_IN = 'LogFP'
                existing.TRANSAKSI_OUT = 'LogFP'
                existing.TINGKAT_TLM = r['tingkat_tlm']
                existing.TOTAL_TLM = r['total_tlm']
                existing.PERSEN_POT_TLM = r['persen_pot_tlm']
                existing.TINGKAT_PSW = r['tingkat_psw']
                existing.TOTAL_PSW = r['total_psw']
                existing.PERSEN_POT_PSW = r['persen_pot_psw']
                existing.AWAL_TLM = r['awal_tlm']
                existing.IS_INVALID = (
                    'Y' if r['is_valid_in'] else 'N'
                )
                existing.IS_OUTVALID = (
                    'Y' if r['is_valid_out'] else 'N'
                )
                existing.TGL_JAM_BAKU_IN = tgl_jam_baku_in
                existing.TGL_JAM_BAKU_OUT = tgl_jam_baku_out
                existing.UPDATE_IN_DATE = datetime.now()
                existing.UPDATE_OUT_DATE = datetime.now()

            else:
                absensi = Absensi(
                    FINGER_ID=r['finger_id'],
                    TGL_KERJA=tgl_kerja,
                    TGL_JAM_IN=tgl_jam_in,
                    TGL_JAM_OUT=tgl_jam_out,
                    TRANSAKSI_IN='LogFP',
                    TRANSAKSI_OUT='LogFP',
                    TINGKAT_TLM=r['tingkat_tlm'],
                    TOTAL_TLM=r['total_tlm'],
                    PERSEN_POT_TLM=r['persen_pot_tlm'],
                    TINGKAT_PSW=r['tingkat_psw'],
                    TOTAL_PSW=r['total_psw'],
                    AWAL_TLM=r['awal_tlm'],
                    IS_INVALID=(
                        'Y' if r['is_valid_in'] else 'N'
                    ),
                    IS_OUTVALID=(
                        'Y' if r['is_valid_out'] else 'N'
                    ),
                    TGL_JAM_BAKU_IN=tgl_jam_baku_in,
                    TGL_JAM_BAKU_OUT=tgl_jam_baku_out,
                    UPDATE_IN_DATE=datetime.now(),
                    UPDATE_OUT_DATE=datetime.now(),
                )

                db.session.add(absensi)

            saved += 1

            # --------------------------------------------------------
            # Simpan representasi hasil export untuk langsung
            # dikirim kembali ke browser.
            #
            # Tidak perlu query ulang seluruh tabel ABSENSI.
            # --------------------------------------------------------

            exported_rows.append({
                'no': saved,
                'nama': r.get('nama') or '',
                'finger_id': r.get('finger_id') or '',
                'tgl_kerja': (
                    tgl_kerja.strftime('%d %b %Y')
                    if tgl_kerja
                    else ''
                ),
                'hari': (
                    tgl_kerja.strftime('%A')
                    if tgl_kerja
                    else ''
                ),
                'jam_baku_in': (
                    tgl_jam_baku_in.strftime('%H:%M')
                    if tgl_jam_baku_in
                    else ''
                ),
                'jam_baku_out': (
                    tgl_jam_baku_out.strftime('%H:%M')
                    if tgl_jam_baku_out
                    else ''
                ),
                'jam_in': (
                    tgl_jam_in.strftime('%H:%M')
                    if tgl_jam_in
                    else ''
                ),
                'jam_out': (
                    tgl_jam_out.strftime('%H:%M')
                    if tgl_jam_out
                    else ''
                ),
                'awal_tlm': r.get('awal_tlm'),
                'total_tlm': r.get('total_tlm'),
                'tingkat_tlm': r.get('tingkat_tlm'),
                'persen_pot_tlm': r.get('persen_pot_tlm'),
                'total_psw': r.get('total_psw'),
                'tingkat_psw': r.get('tingkat_psw'),
                'persen_pot_psw': r.get('persen_pot_psw'),
                'transaksi_in': 'LogFP',
                'transaksi_out': 'LogFP',
            })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Export Sukses ({saved} data)'
                + (
                    f' | Dilewati tanpa NIP: {skipped}'
                    if skipped
                    else ''
                )
            ),
            'saved': saved,
            'skipped': skipped,
            'data': exported_rows,
        })

    except Exception as e:
        db.session.rollback()

        import traceback
        traceback.print_exc()

        return jsonify({
            'error': str(e)
        })


def api_normalisasi_absensi_view():
    """
    TAB 3 - View Data Absensi (Hasil Export). Tombol Refresh.
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')

        if not tgl_awal_str or not tgl_akhir_str:
            return jsonify({'error': 'Tanggal periode kosong', 'data': []})

        tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
        tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d') + timedelta(days=1)

        query = (
            db.session.query(Absensi, Pegawai)
            .outerjoin(Pegawai, Absensi.NIP == Pegawai.NIP)
            .filter(Absensi.TGL_KERJA >= tgl_awal, Absensi.TGL_KERJA < tgl_akhir)
            .order_by(Absensi.FINGER_ID, Absensi.TGL_KERJA)
        )
        results = query.all()

        data = []
        for i, (a, peg) in enumerate(results, 1):
            data.append({
                'no': i,
                'nama': peg.NAMA if peg else '',
                'finger_id': a.FINGER_ID,
                'tgl_kerja': a.TGL_KERJA.strftime('%d %b %Y') if a.TGL_KERJA else '',
                'hari': a.TGL_KERJA.strftime('%A') if a.TGL_KERJA else '',
                'jam_baku_in': a.TGL_JAM_BAKU_IN.strftime('%H:%M') if a.TGL_JAM_BAKU_IN else '',
                'jam_baku_out': a.TGL_JAM_BAKU_OUT.strftime('%H:%M') if a.TGL_JAM_BAKU_OUT else '',
                'jam_in': a.TGL_JAM_IN.strftime('%H:%M') if a.TGL_JAM_IN else '',
                'jam_out': a.TGL_JAM_OUT.strftime('%H:%M') if a.TGL_JAM_OUT else '',
                'awal_tlm': a.AWAL_TLM,
                'total_tlm': a.TOTAL_TLM,
                'tingkat_tlm': a.TINGKAT_TLM,
                'persen_pot_tlm': a.PERSEN_POT_TLM,
                'total_psw': a.TOTAL_PSW,
                'tingkat_psw': a.TINGKAT_PSW,
                'persen_pot_psw': a.PERSEN_POT_PSW,
                'transaksi_in': a.TRANSAKSI_IN,
                'transaksi_out': a.TRANSAKSI_OUT,
            })

        return jsonify({'success': True, 'data': data, 'total': len(data)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'data': []})


def api_closing_get():
    """TAB 4 - ambil tanggal closing absensi saat ini."""
    try:
        row = MediaInformasi.query.filter(
            MediaInformasi.TRX == 'closingabsensi'
        ).order_by(MediaInformasi.PUBLISH_DATE_START.desc()).first()

        return jsonify({
            'success': True,
            'data': row.to_dict() if row else None
        })
    except Exception as e:
        return jsonify({'error': str(e)})


def api_closing_save():
    """TAB 4 - simpan / update tanggal closing absensi."""
    try:
        data = request.get_json()
        tgl_str = data.get('tgl_closing', '')
        updated_by = data.get('updated_by', 'admin')

        if not tgl_str:
            return jsonify({'error': 'Tanggal Closing Kosong'})

        tgl_closing = datetime.strptime(tgl_str, '%Y-%m-%d').date()

        row = MediaInformasi.query.filter(
            MediaInformasi.TRX == 'closingabsensi'
        ).order_by(MediaInformasi.PUBLISH_DATE_START.desc()).first()

        if row:
            row.PUBLISH_DATE_START = tgl_closing
            row.UPDATE_BY = updated_by
            row.UPDATE_DATE = datetime.now()
            msg = 'Update Sukses'
        else:
            row = MediaInformasi(
                PUBLISH_DATE_START=tgl_closing,
                TRX='closingabsensi',
                UPDATE_BY=updated_by,
                UPDATE_DATE=datetime.now()
            )
            db.session.add(row)
            msg = 'Insert Sukses'

        db.session.commit()
        return jsonify({'success': True, 'message': msg})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


def data_absensi_pegawai_manual():
    """
    Render halaman Data Absensi Pegawai Absensi Manual.
    """
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Data Absensi Pegawai Absensi Manual.html',
        unit_kerja_list=unit_kerja_list
    )

# Tambahkan API functions:
def api_inject_absensi_get_pegawai():
    """API: Ambil daftar pegawai by unit kerja"""
    unit_kerja_id = request.args.get('unit_kerja_id', '')
    tgl = request.args.get('tgl', '')
    
    if not unit_kerja_id or not tgl:
        return jsonify({'error': 'Unit Kerja dan Tanggal harus diisi', 'data': []})
    
    try:
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d').date()
        
        # Subquery pegawai yang sedang dinas luar/sakit/cuti
        subquery = (
            db.session.query(DinasLuar.NIP)
            .filter(
                DinasLuar.TRANSAKSI.in_(['sakit', 'cuti']),
                DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_date,
                DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_date
            )
        )
        
        pegawai_list = (
            Pegawai.query
            .filter(Pegawai.UNIT_KERJA_ID == int(unit_kerja_id))
            .filter(Pegawai.IS_KELUAR == 'N')
            .filter(~Pegawai.NIP.in_(subquery))
            .order_by(Pegawai.NAMA)
            .all()
        )
        
        return jsonify({
            'success': True,
            'data': [
                {
                    'nip': p.NIP,
                    'nama': p.NAMA,
                    'gol': p.GOL_ID or ''
                }
                for p in pegawai_list
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})


def api_inject_absensi_acak_jam():
    """API: Acak jam IN/OUT"""
    try:
        data = request.get_json()
        tgl = data.get('tgl', '')
        shift = data.get('shift', '1')
        pegawai_list = data.get('pegawai', [])
        acak_in = data.get('acak_in', True)
        acak_out = data.get('acak_out', True)
        
        if not tgl or not pegawai_list:
            return jsonify({'error': 'Data tidak lengkap'})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        
        # Ambil jam baku - PERBAIKAN: ambil semua jam kerja dulu
        jam_kerja_list = (
            MfJamKerja.query
            .filter(MfJamKerja.TGL_MULAI_BERLAKU <= tgl_date)
            .order_by(MfJamKerja.TGL_MULAI_BERLAKU.desc())
            .all()
        )
        
        if not jam_kerja_list:
            return jsonify({'error': 'Jam kerja tidak ditemukan di database'})
        
        # Gunakan jam kerja pertama sebagai default
        jam_kerja = jam_kerja_list[0]
        
        # ✅ PERBAIKAN: Ambil jam dari DateTime dengan cara yang aman
        baku_in_str = '05:00'  # Default
        baku_out_str = '17:00'  # Default
        
        if jam_kerja.STD_JAM_IN:
            if isinstance(jam_kerja.STD_JAM_IN, datetime):
                baku_in_str = jam_kerja.STD_JAM_IN.strftime('%H:%M')
            else:
                baku_in_str = str(jam_kerja.STD_JAM_IN)[:5]
        
        if jam_kerja.STD_JAM_OUT:
            if isinstance(jam_kerja.STD_JAM_OUT, datetime):
                baku_out_str = jam_kerja.STD_JAM_OUT.strftime('%H:%M')
            else:
                baku_out_str = str(jam_kerja.STD_JAM_OUT)[:5]
        
        print(f"DEBUG: Baku IN={baku_in_str}, Baku OUT={baku_out_str}")
        
        # Parse jam baku
        baku_in_parts = baku_in_str.split(':')
        baku_out_parts = baku_out_str.split(':')
        
        jam_in_hour = int(baku_in_parts[0])
        jam_in_min = int(baku_in_parts[1]) if len(baku_in_parts) > 1 else 0
        jam_out_hour = int(baku_out_parts[0])
        jam_out_min = int(baku_out_parts[1]) if len(baku_out_parts) > 1 else 0
        
        result = []
        for i, peg in enumerate(pegawai_list):
            nama = peg.get('nama', '')
            no = i + 1
            
            # Algoritma random seperti VB.NET
            konstanta = 9
            batas_max = 61
            # Hitung tambahan menit berdasarkan urutan dan nama
            tambahan = (no + konstanta + ((len(nama) + no) * no)) % batas_max
            
            if tambahan > batas_max:
                tambahan = (tambahan % konstanta) + len(nama) + (no % 19)
            
            if tambahan < 7:
                jam_pulang_tambah = tambahan + len(nama)
            else:
                jam_pulang_tambah = tambahan - (no % 7)
            
            # Hitung jam IN (mundur dari baku)
            total_menit_in = jam_in_hour * 60 + jam_in_min - tambahan
            if total_menit_in < 0:
                total_menit_in = 0
            jam_in_h = total_menit_in // 60
            jam_in_m = total_menit_in % 60
            
            # Hitung jam OUT (maju dari baku)
            total_menit_out = jam_out_hour * 60 + jam_out_min + jam_pulang_tambah
            jam_out_h = total_menit_out // 60
            jam_out_m = total_menit_out % 60
            
            result.append({
                'nip': peg.get('nip', ''),
                'nama': nama,
                'jam_in': f"{jam_in_h:02d}:{jam_in_m:02d}" if acak_in else '',
                'jam_out': f"{jam_out_h:02d}:{jam_out_m:02d}" if acak_out else '',
                'jam_baku_in': baku_in_str[:5],
                'jam_baku_out': baku_out_str[:5],
            })
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_inject_absensi_save():
    """API: Simpan absensi manual"""
    try:
        data = request.get_json()
        tgl = data.get('tgl', '')
        no_surat = data.get('no_surat', '')
        keterangan = data.get('keterangan', '')
        shift = data.get('shift', '1')
        pegawai_list = data.get('pegawai', [])
        
        if not tgl or not pegawai_list:
            return jsonify({'error': 'Tanggal dan pegawai harus diisi'})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        saved_count = 0
        
        for peg in pegawai_list:
            nip = peg.get('nip', '')
            jam_in = peg.get('jam_in', '')
            jam_out = peg.get('jam_out', '')
            ket_in = peg.get('ket_in', keterangan)
            ket_out = peg.get('ket_out', keterangan)
            
            if not jam_in and not jam_out:
                continue
            
            # ✅ CARI FINGER_ID DARI PEGAWAI (jika ada)
            pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
            
            # ✅ Gunakan NIP sebagai string untuk FINGER_ID (ubah tipe kolom jika perlu)
            # Atau simpan NIP di REF_INJECT untuk referensi
            finger_id_str = nip  # Simpan NIP sebagai string
            
            # Delete existing manual record for this date (by NIP in REF_INJECT)
            TimeRecorder.query.filter(
                TimeRecorder.REF_INJECT == no_surat if no_surat else True,
                TimeRecorder.MESIN == '999',
                db.func.date(TimeRecorder.WAKTU) == tgl_date.date(),
                TimeRecorder.KET_INJECT == nip  # ✅ Cari by NIP di KET_INJECT
            ).delete()
            
            # Insert IN
            if jam_in:
                tgl_jam_in = datetime.strptime(f"{tgl} {jam_in}", '%Y-%m-%d %H:%M')
                tr_in = TimeRecorder(
                    FINGER_ID=pegawai.ABSENSI_ID if pegawai else 0,  # Gunakan ABSENSI_ID atau 0
                    WAKTU=tgl_jam_in,
                    STATUS='IN',
                    MESIN='999',
                    KET='MANUAL',
                    TRANSAKSI='MANUAL',
                    KET_INJECT=nip,  # ✅ Simpan NIP di sini untuk referensi
                    REF_INJECT=no_surat or '',
                    UPDATE_IN_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(tr_in)
            
            # Insert OUT
            if jam_out:
                tgl_jam_out = datetime.strptime(f"{tgl} {jam_out}", '%Y-%m-%d %H:%M')
                tr_out = TimeRecorder(
                    FINGER_ID=pegawai.ABSENSI_ID if pegawai else 0,
                    WAKTU=tgl_jam_out,
                    STATUS='OUT',
                    MESIN='999',
                    KET='MANUAL',
                    TRANSAKSI='MANUAL',
                    KET_INJECT=nip,  # ✅ Simpan NIP di sini
                    REF_INJECT=no_surat or '',
                    UPDATE_IN_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(tr_out)
            
            saved_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{saved_count} data berhasil disimpan',
            'saved': saved_count
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def data_absensi_pegawai_lembur_manual():
    """Render halaman Lembur Manual"""
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Data Absensi Pegawai Lembur Manual.html',
        unit_kerja_list=unit_kerja_list
    )

def api_inject_lembur_get_pegawai():
    """API: Ambil daftar pegawai by unit kerja (untuk lembur)"""
    unit_kerja_id = request.args.get('unit_kerja_id', '')
    tgl = request.args.get('tgl', '')
    
    if not unit_kerja_id or not tgl:
        return jsonify({'error': 'Unit Kerja dan Tanggal harus diisi', 'data': []})
    
    try:
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d').date()
        
        subquery = (
            db.session.query(DinasLuar.NIP)
            .filter(
                DinasLuar.TRANSAKSI.in_(['sakit', 'cuti']),
                DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_date,
                DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_date
            )
        )
        
        pegawai_list = (
            Pegawai.query
            .filter(Pegawai.UNIT_KERJA_ID == int(unit_kerja_id))
            .filter(Pegawai.IS_KELUAR == 'N')
            .filter(~Pegawai.NIP.in_(subquery))
            .order_by(Pegawai.NAMA)
            .all()
        )
        
        return jsonify({
            'success': True,
            'data': [{'nip': p.NIP, 'nama': p.NAMA, 'gol': p.GOL_ID or ''} for p in pegawai_list]
        })
    except Exception as e:
        return jsonify({'error': str(e), 'data': []})


def api_inject_lembur_acak_jam():
    """API: Acak jam lembur IN/OUT"""
    try:
        data = request.get_json()
        tgl = data.get('tgl', '')
        shift = data.get('shift', '1')
        pegawai_list = data.get('pegawai', [])
        acak_in = data.get('acak_in', True)
        acak_out = data.get('acak_out', True)
        
        if not tgl or not pegawai_list:
            return jsonify({'error': 'Data tidak lengkap'})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        
        # Ambil jam baku
        jam_kerja_list = (
            MfJamKerja.query
            .filter(MfJamKerja.TGL_MULAI_BERLAKU <= tgl_date)
            .order_by(MfJamKerja.TGL_MULAI_BERLAKU.desc())
            .all()
        )
        
        if not jam_kerja_list:
            return jsonify({'error': 'Jam kerja tidak ditemukan'})
        
        jam_kerja = jam_kerja_list[0]
        
        # Default jam lembur (pagi buta)
        baku_in_str = '05:00'
        baku_out_str = '10:30'
        
        if jam_kerja.STD_JAM_IN:
            if isinstance(jam_kerja.STD_JAM_IN, datetime):
                baku_in_str = jam_kerja.STD_JAM_IN.strftime('%H:%M')
            else:
                baku_in_str = str(jam_kerja.STD_JAM_IN)[:5]
        
        if jam_kerja.STD_JAM_OUT:
            if isinstance(jam_kerja.STD_JAM_OUT, datetime):
                baku_out_str = jam_kerja.STD_JAM_OUT.strftime('%H:%M')
            else:
                baku_out_str = str(jam_kerja.STD_JAM_OUT)[:5]
        
        baku_in_parts = baku_in_str.split(':')
        jam_in_hour = int(baku_in_parts[0])
        jam_in_min = int(baku_in_parts[1]) if len(baku_in_parts) > 1 else 0
        
        baku_out_parts = baku_out_str.split(':')
        jam_out_hour = int(baku_out_parts[0])
        jam_out_min = int(baku_out_parts[1]) if len(baku_out_parts) > 1 else 0
        
        result = []
        for i, peg in enumerate(pegawai_list):
            nama = peg.get('nama', '')
            no = i + 1
            
            # Random menit
            konstanta = 9
            batas_max = 61
            tambahan = (no + konstanta + ((len(nama) + no) * no)) % batas_max
            if tambahan > batas_max:
                tambahan = (tambahan % konstanta) + len(nama) + (no % 19)
            if tambahan < 7:
                jam_pulang_tambah = tambahan + len(nama)
            else:
                jam_pulang_tambah = tambahan - (no % 7)
            
            total_menit_in = jam_in_hour * 60 + jam_in_min - tambahan
            if total_menit_in < 0:
                total_menit_in = 0
            jam_in_h = total_menit_in // 60
            jam_in_m = total_menit_in % 60
            
            total_menit_out = jam_out_hour * 60 + jam_out_min + jam_pulang_tambah
            jam_out_h = total_menit_out // 60
            jam_out_m = total_menit_out % 60
            
            result.append({
                'nip': peg.get('nip', ''),
                'nama': nama,
                'jam_in': f"{jam_in_h:02d}:{jam_in_m:02d}" if acak_in else '',
                'jam_out': f"{jam_out_h:02d}:{jam_out_m:02d}" if acak_out else '',
                'jam_baku_in': baku_in_str[:5],
                'jam_baku_out': baku_out_str[:5],
            })
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def api_inject_lembur_save():
    """API: Simpan lembur manual ke tabel LEMBUR"""
    try:
        data = request.get_json()
        tgl = data.get('tgl', '')
        no_surat = data.get('no_surat', '')
        keterangan = data.get('keterangan', '')
        shift = data.get('shift', '1')
        pegawai_list = data.get('pegawai', [])
        
        if not tgl or not pegawai_list:
            return jsonify({'error': 'Tanggal dan pegawai harus diisi'})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        saved_count = 0
        
        for peg in pegawai_list:
            nip = peg.get('nip', '')
            jam_in = peg.get('jam_in', '')
            jam_out = peg.get('jam_out', '')
            jam_baku_in = peg.get('jam_baku_in', '')
            jam_baku_out = peg.get('jam_baku_out', '')
            ket = peg.get('ket_out', keterangan)
            
            if not jam_in and not jam_out:
                continue
            
            # Resolve NIP -> FingerID karena LEMBUR legacy
            # tidak menyimpan NIP.
            pegawai = (
                Pegawai.query
                .filter(Pegawai.NIP == nip)
                .first()
            )

            if not pegawai or not pegawai.FingerID:
                continue

            finger_id = pegawai.FingerID

            # Cek existing berdasarkan natural key legacy:
            # FingerID + TglKerja
            existing = Lembur.query.filter(
                Lembur.FINGER_ID == finger_id,
                Lembur.TGL_KERJA == tgl_date.date()
            ).first()

            tgl_jam_in = datetime.strptime(f"{tgl} {jam_in}", '%Y-%m-%d %H:%M') if jam_in else None
            tgl_jam_out = datetime.strptime(f"{tgl} {jam_out}", '%Y-%m-%d %H:%M') if jam_out else None
            tgl_jam_baku_in = datetime.strptime(f"{tgl} {jam_baku_in}", '%Y-%m-%d %H:%M') if jam_baku_in else None
            tgl_jam_baku_out = datetime.strptime(f"{tgl} {jam_baku_out}", '%Y-%m-%d %H:%M') if jam_baku_out else None
            
            if existing:
                # Update
                if jam_in:
                    existing.JAM_IN = tgl_jam_in
                    existing.JAM_BAKU_IN = tgl_jam_baku_in
                if jam_out:
                    existing.JAM_OUT = tgl_jam_out
                    existing.JAM_BAKU_OUT = tgl_jam_baku_out
                existing.KETERANGAN = ket
                existing.NO_SURAT = no_surat
                existing.UPDATE_BY = 'admin'
                existing.UPDATE_DATE = datetime.now()
            else:
                # Insert
                lembur = Lembur(
                    FINGER_ID=finger_id,
                    TGL_KERJA=tgl_date.date(),
                    JAM_IN=tgl_jam_in,
                    JAM_OUT=tgl_jam_out,
                    JAM_BAKU_IN=tgl_jam_baku_in,
                    JAM_BAKU_OUT=tgl_jam_baku_out,
                    KETERANGAN=ket,
                    NO_SURAT=no_surat,
                    UPDATE_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
                db.session.add(lembur)
            
            saved_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{saved_count} data lembur berhasil disimpan',
            'saved': saved_count
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def data_absensi_trace_tunjangan():
    """
    Render halaman Data Absensi Trace Tunjangan.
    """
    from app.models.unitKerjaModel import MfUnitKerja
    unit_kerja_list = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    return render_template(
        'pages/dashboard_1/Data Absensi Trace Tunjangan.html',
        unit_kerja_list=unit_kerja_list
    )

def api_trace_tunjangan():
    """
    API Trace Tunjangan - sesuai VB.NET TraceTunKin.aspx
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')
        unit_kerja_ids = request.args.getlist('unit_kerja[]')
        
        if not tgl_awal_str or not tgl_akhir_str:
            return jsonify({'error': 'Tanggal periode kosong', 'data': []})
        
        tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
        tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d')
        tgl_akhir_date = tgl_akhir.date()
        tgl_awal_date = tgl_awal.date()
        
        # Cek tgl server
        tgl_server = datetime.now()
        if tgl_server.date() < tgl_awal_date:
            return jsonify({'error': 'Tgl server lebih kecil dari tgl awal periode', 'data': []})
        if tgl_server.date() < tgl_akhir_date:
            tgl_akhir = tgl_server
            tgl_akhir_date = tgl_akhir.date()
        
        # 1. Ambil kalender
        kalender_rows = (
            MfKalender.query
            .filter(MfKalender.TGL_KERJA.between(tgl_awal, tgl_akhir))
            .all()
        )
        
        # 2. Ambil absensi (JOIN via NIP)
        absensi_query = (
            db.session.query(Absensi, Pegawai)
            .join(Pegawai, Absensi.NIP == Pegawai.NIP)
            .join(MfKalender, Absensi.TGL_KERJA == MfKalender.TGL_KERJA)
            .filter(Absensi.TGL_KERJA.between(tgl_awal, tgl_akhir))
            .filter(MfKalender.IS_LIBUR == 'N')
        )
        if unit_kerja_ids:
            absensi_query = absensi_query.filter(Pegawai.UNIT_KERJA_ID.in_(unit_kerja_ids))
        absensi_rows = absensi_query.all()
        
        # 3. Ambil pegawai dengan tunjangan & jabatan
        pegawai_query = (
            db.session.query(Pegawai, MfUnitKerja, MfJabatan)
            .join(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
            .outerjoin(MfJabatan, Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID)
            .filter(
                Pegawai.TGL_MASUK <= tgl_akhir,
                db.or_(
                    Pegawai.IS_KELUAR == 'N',
                    db.and_(Pegawai.IS_KELUAR == 'Y', Pegawai.TGL_KELUAR >= tgl_awal)
                )
            )
        )
        if unit_kerja_ids:
            pegawai_query = pegawai_query.filter(Pegawai.UNIT_KERJA_ID.in_(unit_kerja_ids))
        
        pegawai_rows = pegawai_query.order_by(
            MfJabatan.URUT_JABATAN.asc(),
            Pegawai.CLASS_ID.desc(),
            Pegawai.NIP.asc()
        ).all()
        
        if not pegawai_rows:
            return jsonify({'error': 'Data pegawai tidak ditemukan', 'data': []})
        
        # 4. Ambil MFPot
        potongan_list = (
            MfPot.query
            .filter(MfPot.TGL_MULAI <= tgl_akhir_date)
            .all()
        )
        
        # 5. Ambil DinasLuar > 4 bulan
        dinas_luar_rows = (
            db.session.query(DinasLuar, Pegawai)
            .join(Pegawai, DinasLuar.NIP == Pegawai.NIP)
            .filter(DinasLuar.TRANSAKSI == 'DinasLuar')
            .filter(DinasLuar.STATUS_UM == 1)
            .filter(DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_akhir)
            .filter(DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_awal)
        )
        if unit_kerja_ids:
            dinas_luar_rows = dinas_luar_rows.filter(Pegawai.UNIT_KERJA_ID.in_(unit_kerja_ids))
        dinas_luar_rows = dinas_luar_rows.all()
        
        # Build dict absensi per NIP
        absensi_dict = defaultdict(list)
        for a, p in absensi_rows:
            if a.NIP:
                absensi_dict[a.NIP.strip()].append(a)
        
        # Build dict DL per NIP
        dl_dict = defaultdict(list)
        for dl, p in dinas_luar_rows:
            if dl.NIP:
                dl_dict[dl.NIP.strip()].append(dl)
        
        # Ambil tunjangan per class
        class_tunjangan = {}
        for c in MfClass.query.filter(MfClass.TGL_MULAI <= tgl_akhir_date).order_by(MfClass.TGL_MULAI.desc()).all():
            if c.CLASS_ID not in class_tunjangan:
                class_tunjangan[c.CLASS_ID] = c.TUNJANGAN or 0
        
        # Hitung per pegawai
        data = []
        no = 1
        
        for peg, unit, jabatan in pegawai_rows:
            abs_list = absensi_dict.get((peg.NIP or '').strip(), [])
            dl_list = dl_dict.get((peg.NIP or '').strip(), [])
            tunjangan = class_tunjangan.get(peg.CLASS_ID, 0)
            
            # Hitung persen potongan
            persen_pot = 0
            tgl_masuk = peg.TGL_MASUK
            tgl_hitung = tgl_masuk if tgl_masuk and tgl_masuk > tgl_awal else tgl_awal
            
            d = tgl_hitung
            while d.date() <= tgl_akhir_date:
                tgl_str = d.strftime('%Y-%m-%d')
                
                # Cek libur
                is_libur = False
                kl = [k for k in kalender_rows if k.TGL_KERJA and k.TGL_KERJA.strftime('%Y-%m-%d') == tgl_str]
                if kl:
                    is_libur = kl[0].IS_LIBUR == 'Y'
                elif d.weekday() >= 5:
                    is_libur = True
                
                if not is_libur:
                    # Cari absensi untuk tanggal ini
                    a = None
                    for abs_item in abs_list:
                        if abs_item.TGL_KERJA and abs_item.TGL_KERJA.strftime('%Y-%m-%d') == tgl_str:
                            a = abs_item
                            break
                    
                    if a:
                        transaksi = (a.TRANSAKSI_IN or '').strip().lower()
                        if transaksi in ('alpa', 'sakit', 'ijin'):
                            persen_pot += a.PERSEN_POT_TLM or 0
                        elif transaksi == 'dinasluar':
                            pass  # Tidak ada potongan untuk DL
                        else:
                            persen_pot += (a.PERSEN_POT_TLM or 0) + (a.PERSEN_POT_PSW or 0)
                    else:
                        # TA - cari potongan TA di MFPot
                        for pot in potongan_list:
                            if pot.KATEGORI == 'TA':
                                persen_pot += pot.PERSEN_POT or 0
                                break
                    
                    # DL > 4 bulan
                    for dl in dl_list:
                        if dl.TGL_AWAL_DINAS_LUAR:
                            limit_dl = dl.TGL_AWAL_DINAS_LUAR + timedelta(days=120)
                            tgl_akhir_dl = dl.TGL_AKHIR_DINAS_LUAR.date() if dl.TGL_AKHIR_DINAS_LUAR else d.date()
                            if limit_dl.date() <= d.date() <= tgl_akhir_dl:
                                for pot in potongan_list:
                                    if pot.KATEGORI == 'DINASLUAR':
                                        persen_pot += pot.PERSEN_POT or 0
                                        break
                
                d += timedelta(days=1)
            
            # Hitung nilai
            nilai_pot = tunjangan * (persen_pot / 100) if persen_pot > 0 else 0
            jumlah_dibayar = tunjangan - nilai_pot
            
            data.append({
                'no': no,
                'nip': peg.NIP or '',
                'nama': peg.NAMA or '',
                'status_peg': 'PNS' if peg.STATUS_PEG == 1 else 'Non PNS',
                'jabatan': jabatan.NAMA_JABATAN if jabatan else '-',
                'tmt_jabatan': peg.TMT_JABATAN.strftime('%d/%m/%Y') if peg.TMT_JABATAN else '-',
                'class_id': peg.CLASS_ID or '',
                'tunjangan': tunjangan,
                'persen_pot': round(persen_pot, 2),
                'nilai_pot': round(nilai_pot, 2),
                'jumlah_dibayar': round(jumlah_dibayar, 2),
            })
            no += 1
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'data': []})


def data_absensi_trace():
    """
    Render halaman Data Absensi Trace.
    """
    return render_template('pages/dashboard_1/Data Absensi Trace.html')


def api_trace_absensi():
    """
    API untuk mengambil data Trace Absensi.
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        if not tgl_awal_str or not tgl_akhir_str:
            return jsonify({'error': 'Tanggal periode kosong', 'data': []})
        
        tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
        tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d') + timedelta(days=1)
        
        # ✅ Query utama - JOIN via NIP (bukan FINGER_ID)
        query = (
            db.session.query(
                Absensi,
                Pegawai,
                MfUnitKerja
            )
            .join(Pegawai, Absensi.NIP == Pegawai.NIP)  # ✅ PAKAI NIP
            .join(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
            .filter(
                Absensi.TGL_KERJA >= tgl_awal,
                Absensi.TGL_KERJA < tgl_akhir
            )
        )
        
        # Field mapping untuk filter
        field_mapping = {
            'FingerID': Absensi.FINGER_ID,
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'UnitKerjaName': MfUnitKerja.NAMA_UNIT_KERJA,
            'TransaksiIn': Absensi.TRANSAKSI_IN,
            'TransaksiOut': Absensi.TRANSAKSI_OUT,
            'TingkatTLM': Absensi.TINGKAT_TLM,
            'TingkatPSW': Absensi.TINGKAT_PSW,
        }
        
        if filter_field1 and filter_value1:
            field = field_mapping.get(filter_field1)
            if field:
                query = query.filter(field.ilike(f'%{filter_value1}%'))
        
        if filter_field2 and filter_value2:
            field = field_mapping.get(filter_field2)
            if field:
                query = query.filter(field.ilike(f'%{filter_value2}%'))
        
        # Order by NIP, TglKerja
        query = query.order_by(Pegawai.NIP, Absensi.TGL_KERJA)
        
        results = query.all()
        
        # Format data
        data = []
        for i, (absensi, pegawai, unit_kerja) in enumerate(results, 1):
            # Logika VB.NET: Manual -> LogFP
            transaksi_in = (absensi.TRANSAKSI_IN or '').strip()
            if transaksi_in.upper() == 'MANUAL':
                transaksi_in = 'LogFP'
            
            is_logfp = transaksi_in.upper() == 'LOGFP'
            status_um = absensi.STATUS_UM or 0
            
            # Jika LogFP atau StatusUM = 0/2, tampilkan jam
            if is_logfp or status_um in [0, 2]:
                jam_baku_in = absensi.TGL_JAM_BAKU_IN.strftime('%H:%M') if absensi.TGL_JAM_BAKU_IN else ''
                jam_baku_out = absensi.TGL_JAM_BAKU_OUT.strftime('%H:%M') if absensi.TGL_JAM_BAKU_OUT else ''
                jam_in = absensi.TGL_JAM_IN.strftime('%H:%M') if absensi.TGL_JAM_IN else ''
                jam_out = absensi.TGL_JAM_OUT.strftime('%H:%M') if absensi.TGL_JAM_OUT else ''
                awal_tlm = absensi.AWAL_TLM or 0
                total_tlm = absensi.TOTAL_TLM or 0
                persen_pot_tlm = absensi.PERSEN_POT_TLM or 0
                persen_pot_psw = absensi.PERSEN_POT_PSW or 0
                tingkat_tlm = absensi.TINGKAT_TLM or ''
                tingkat_psw = absensi.TINGKAT_PSW or ''
                total_psw = absensi.TOTAL_PSW or 0
            else:
                jam_baku_in = ''
                jam_baku_out = ''
                jam_in = ''
                jam_out = ''
                awal_tlm = ''
                total_tlm = ''
                persen_pot_tlm = ''
                persen_pot_psw = ''
                tingkat_tlm = ''
                tingkat_psw = ''
                total_psw = ''
            
            # Validasi
            is_valid_in = (absensi.IS_INVALID or '').upper() == 'Y'
            is_valid_out = (absensi.IS_OUTVALID or '').upper() == 'Y'
            is_valid_tgl = is_valid_in and is_valid_out
            
            # Nama update
            nama_update_in = ''
            if absensi.UPDATE_IN_BY:
                nama_update_in = absensi.UPDATE_IN_BY
                if absensi.UPDATE_IN_DATE:
                    nama_update_in += f" {absensi.UPDATE_IN_DATE.strftime('%d/%m/%Y %H:%M')}"
            
            nama_update_out = ''
            if absensi.UPDATE_OUT_BY:
                nama_update_out = absensi.UPDATE_OUT_BY
                if absensi.UPDATE_OUT_DATE:
                    nama_update_out += f" {absensi.UPDATE_OUT_DATE.strftime('%d/%m/%Y %H:%M')}"
            
            data.append({
                'no': i,
                'nip': pegawai.NIP or '',
                'nama': pegawai.NAMA or '',
                'finger_id': absensi.FINGER_ID or '',
                'tgl_kerja': absensi.TGL_KERJA.strftime('%d %b %Y') if absensi.TGL_KERJA else '',
                'hari': absensi.TGL_KERJA.strftime('%A') if absensi.TGL_KERJA else '',
                'jam_baku_in': jam_baku_in,
                'jam_baku_out': jam_baku_out,
                'jam_in': jam_in,
                'jam_out': jam_out,
                'awal_tlm': awal_tlm,
                'total_tlm': total_tlm,
                'persen_pot_tlm': persen_pot_tlm,
                'persen_pot_psw': persen_pot_psw,
                'tingkat_tlm': tingkat_tlm,
                'total_psw': total_psw,
                'tingkat_psw': tingkat_psw,
                'transaksi_in': transaksi_in,
                'transaksi_out': absensi.TRANSAKSI_OUT or '',
                'is_valid_in': is_valid_in,
                'is_valid_out': is_valid_out,
                'is_valid_tgl': is_valid_tgl,
                'nama_update_in': nama_update_in,
                'nama_update_out': nama_update_out,
                'unit_kerja': unit_kerja.NAMA_UNIT_KERJA if unit_kerja else '',
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


# ---- Cari Absensi (pencarian) ----

def cari_absensi_non_finger():
    """Render halaman Cari Absensi Non Finger."""
    return render_template('pages/dashboard_1/Cari Absensi Non Finger.html')

def api_cari_absensi_non_finger():
    """
    API Cari Absensi Non Finger - mencari data TimeRecorder 
    MESIN='999' (data inject manual saja)
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        # ✅ HANYA data inject manual (MESIN='999')
        query = (
            db.session.query(TimeRecorder, Pegawai, MfUnitKerja)
            .outerjoin(Pegawai, TimeRecorder.KET_INJECT == Pegawai.NIP)
            .outerjoin(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
            .filter(TimeRecorder.MESIN == '999')  # ✅ Hanya data manual
            .filter(TimeRecorder.STATUS.in_(['IN', 'OUT']))
        )
        
        # Filter periode
        if tgl_awal_str and tgl_akhir_str:
            tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
            tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(
                TimeRecorder.WAKTU >= tgl_awal,
                TimeRecorder.WAKTU < tgl_akhir
            )
        
        # Field mapping untuk filter tambahan
        field_mapping = {
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'UnitKerjaName': MfUnitKerja.NAMA_UNIT_KERJA,
            'Status': TimeRecorder.STATUS,
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
        query = query.order_by(TimeRecorder.WAKTU.desc())
        results = query.all()
        
        # Format data
        data = []
        for i, (tr, peg, unit) in enumerate(results, 1):
            data.append({
                'no': i,
                'nama': peg.NAMA if peg else '-',
                'nip': peg.NIP if peg else (tr.KET_INJECT or str(tr.FINGER_ID)),
                'finger_id': tr.FINGER_ID or '',
                'tanggal': tr.WAKTU.strftime('%d %b %Y') if tr.WAKTU else '',
                'jam': tr.WAKTU.strftime('%H:%M:%S') if tr.WAKTU else '',
                'waktu_raw': tr.WAKTU.strftime('%Y-%m-%d %H:%M:%S') if tr.WAKTU else '',
                'status': tr.STATUS or '',
                'transaksi': tr.TRANSAKSI or tr.KET or '',
                'mesin': tr.MESIN or '',
                'unit_kerja': unit.NAMA_UNIT_KERJA if unit else '-',
                'update_by': tr.UPDATE_IN_BY or '',
                'update_date': tr.UPDATE_DATE.strftime('%d/%m/%Y %H:%M') if tr.UPDATE_DATE else '',
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


def cari_absensi_normalisasi_finger():
    """Render halaman Cari Absensi Normalisasi Absensi Finger."""
    return render_template('pages/dashboard_1/Cari Absensi Normalisasi Absensi Finger.html')

def api_cari_absensi_normalisasi_finger():
    """
    API Cari Absensi Normalisasi Finger - mencari data TimeRecorder
    dengan status IN/OUT (semua data, tidak hanya inject manual)
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        # Query dari TimeRecorder join ke Pegawai via NIP (semua mesin)
        query = (
            db.session.query(TimeRecorder, Pegawai, MfUnitKerja)
            .outerjoin(Pegawai, TimeRecorder.KET_INJECT == Pegawai.NIP)
            .outerjoin(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
            .filter(TimeRecorder.MESIN == '999')
            .filter(TimeRecorder.STATUS.in_(['IN', 'OUT']))
        )
        
        # Filter periode
        if tgl_awal_str and tgl_akhir_str:
            tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
            tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(
                TimeRecorder.WAKTU >= tgl_awal,
                TimeRecorder.WAKTU < tgl_akhir
            )
        
        # Field mapping untuk filter tambahan
        field_mapping = {
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'UnitKerjaName': MfUnitKerja.NAMA_UNIT_KERJA,
            'Status': TimeRecorder.STATUS,
            'FingerID': TimeRecorder.FINGER_ID,
            'Transaksi': TimeRecorder.TRANSAKSI,
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
        query = query.order_by(TimeRecorder.WAKTU.desc())
        results = query.all()
        
        # Format data
        data = []
        for i, (tr, peg, unit) in enumerate(results, 1):
            nama = peg.NAMA if peg else '-'
            nip = peg.NIP if peg else (tr.KET_INJECT or str(tr.FINGER_ID))
            
            data.append({
                'no': i,
                'nama': nama,
                'nip': nip,
                'finger_id': tr.FINGER_ID or '',
                'tanggal': tr.WAKTU.strftime('%d %b %Y') if tr.WAKTU else '',
                'jam': tr.WAKTU.strftime('%H:%M:%S') if tr.WAKTU else '',
                'waktu_raw': tr.WAKTU.strftime('%Y-%m-%d %H:%M:%S') if tr.WAKTU else '',
                'status': tr.STATUS or '',
                'transaksi': tr.TRANSAKSI or tr.KET or '',
                'mesin': tr.MESIN or '',
                'unit_kerja': unit.NAMA_UNIT_KERJA if unit else '-',
                'update_by': tr.UPDATE_IN_BY or '',
                'update_date': tr.UPDATE_DATE.strftime('%d/%m/%Y %H:%M') if tr.UPDATE_DATE else '',
                'ket_inject': tr.KET_INJECT or '',
                'ref_inject': tr.REF_INJECT or '',
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


def cari_absensi_pegawai_manual():
    """Render halaman Cari Absensi Pegawai Absen Manual."""
    return render_template('pages/dashboard_1/Cari Absensi Pegawai Absen Manual.html')

def api_cari_absensi_manual():
    """
    API Cari Absensi Manual - mencari data TimeRecorder dengan MESIN='999'
    Join via KET_INJECT (NIP) ke PEGAWAI
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        # ✅ JOIN via KET_INJECT (tempat NIP disimpan)
        query = (
            db.session.query(TimeRecorder, Pegawai, MfUnitKerja)
            .outerjoin(Pegawai, TimeRecorder.KET_INJECT == Pegawai.NIP)
            .outerjoin(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
            .filter(TimeRecorder.MESIN == '999')
            .filter(TimeRecorder.STATUS.in_(['IN', 'OUT']))
        )
        
        # Filter periode
        if tgl_awal_str and tgl_akhir_str:
            tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
            tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(
                TimeRecorder.WAKTU >= tgl_awal,
                TimeRecorder.WAKTU < tgl_akhir
            )
        
        # Field mapping
        field_mapping = {
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'UnitKerjaName': MfUnitKerja.NAMA_UNIT_KERJA,
            'Status': TimeRecorder.STATUS,
            'UpdateBy': TimeRecorder.UPDATE_IN_BY,
        }
        
        if filter_field1 and filter_value1:
            field = field_mapping.get(filter_field1)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value1}%'))
        
        if filter_field2 and filter_value2:
            field = field_mapping.get(filter_field2)
            if field is not None:
                query = query.filter(field.ilike(f'%{filter_value2}%'))
        
        query = query.order_by(TimeRecorder.WAKTU.desc())
        results = query.all()
        
        data = []
        for i, (tr, peg, unit) in enumerate(results, 1):
            data.append({
                'no': i,
                'nama': peg.NAMA if peg else '-',
                'nip': peg.NIP if peg else (tr.KET_INJECT or tr.FINGER_ID),
                'finger_id': tr.FINGER_ID or '',
                'tanggal': tr.WAKTU.strftime('%d %b %Y') if tr.WAKTU else '',
                'jam': tr.WAKTU.strftime('%H:%M:%S') if tr.WAKTU else '',
                'waktu_raw': tr.WAKTU.strftime('%Y-%m-%d %H:%M:%S') if tr.WAKTU else '',
                'status': tr.STATUS or '',
                'transaksi': tr.TRANSAKSI or tr.KET or '',
                'update_by': tr.UPDATE_IN_BY or '',
                'update_date': tr.UPDATE_DATE.strftime('%d/%m/%Y %H:%M') if tr.UPDATE_DATE else '',
                'unit_kerja': unit.NAMA_UNIT_KERJA if unit else '-',
                'ket_inject': tr.KET_INJECT or '',
                'ref_inject': tr.REF_INJECT or '',
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


def api_cari_absensi_manual_delete():
    """API: Delete data absensi manual"""
    try:
        data = request.get_json()
        finger_id = data.get('finger_id', '')
        waktu = data.get('waktu', '')
        
        if not finger_id or not waktu:
            return jsonify({'error': 'Data tidak lengkap'})
        
        # Delete dari TimeRecorder
        result = TimeRecorder.query.filter(
            TimeRecorder.FINGER_ID == finger_id,
            TimeRecorder.WAKTU == datetime.strptime(waktu, '%Y-%m-%d %H:%M:%S'),
            TimeRecorder.MESIN == '999',
            TimeRecorder.KET == 'MANUAL'
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{result} data berhasil dihapus'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


def api_cari_absensi_manual_update():
    """API: Update data absensi manual (jam saja)"""
    try:
        data = request.get_json()
        finger_id = data.get('finger_id', '')
        waktu_lama = data.get('waktu_lama', '')
        jam_baru = data.get('jam_baru', '')
        status = data.get('status', '')
        
        if not finger_id or not waktu_lama or not jam_baru:
            return jsonify({'error': 'Data tidak lengkap'})
        
        tgl = datetime.strptime(waktu_lama, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        waktu_baru = datetime.strptime(f"{tgl} {jam_baru}", '%Y-%m-%d %H:%M:%S')
        
        # Delete old record
        TimeRecorder.query.filter(
            TimeRecorder.FINGER_ID == finger_id,
            TimeRecorder.WAKTU == datetime.strptime(waktu_lama, '%Y-%m-%d %H:%M:%S'),
            TimeRecorder.MESIN == '999'
        ).delete()
        
        # Insert new record
        tr = TimeRecorder(
            FINGER_ID=finger_id,
            WAKTU=waktu_baru,
            STATUS=status,
            MESIN='999',
            KET='MANUAL',
            TRANSAKSI='MANUAL',
            UPDATE_IN_BY='admin',
            UPDATE_DATE=datetime.now()
        )
        db.session.add(tr)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data berhasil diupdate'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


def cari_absensi_pegawai_lembur_manual():
    """Render halaman Cari Absensi Pegawai Lembur Manual."""
    return render_template('pages/dashboard_1/Cari Absensi Pegawai Lembur Manual.html')

def api_cari_lembur_manual():
    """
    API Cari Lembur Manual - mencari data dari tabel LEMBUR
    Join via NIP ke PEGAWAI
    """
    try:
        tgl_awal_str = request.args.get('tgl_awal', '')
        tgl_akhir_str = request.args.get('tgl_akhir', '')
        filter_field1 = request.args.get('filter_field1', '')
        filter_value1 = request.args.get('filter_value1', '')
        filter_field2 = request.args.get('filter_field2', '')
        filter_value2 = request.args.get('filter_value2', '')
        
        # Query dari tabel LEMBUR join ke PEGAWAI via NIP
        query = (
            db.session.query(Lembur, Pegawai, MfUnitKerja)
            .join(Pegawai, Lembur.FINGER_ID == Pegawai.FINGER_ID)
            .join(MfUnitKerja, Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID)
        )
        
        # Filter periode
        if tgl_awal_str and tgl_akhir_str:
            tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
            tgl_akhir = datetime.strptime(tgl_akhir_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(
                Lembur.TGL_KERJA >= tgl_awal,
                Lembur.TGL_KERJA < tgl_akhir
            )
        
        # Field mapping untuk filter tambahan
        field_mapping = {
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'UnitKerjaName': MfUnitKerja.NAMA_UNIT_KERJA,
            'Keterangan': Lembur.KETERANGAN,
            'NoSurat': Lembur.NO_SURAT,
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
        query = query.order_by(Lembur.TGL_KERJA.desc(), Pegawai.NAMA)
        results = query.all()
        
        # Format data
        data = []
        for i, (lembur, peg, unit) in enumerate(results, 1):
            data.append({
                'no': i,
                'id': f"{lembur.FINGER_ID}|{lembur.TGL_KERJA.strftime('%Y-%m-%d')}",
                'nama': peg.NAMA or '',
                'nip': peg.NIP or '',
                'tgl_kerja': lembur.TGL_KERJA.strftime('%d %b %Y') if lembur.TGL_KERJA else '',
                'jam_in': lembur.JAM_IN.strftime('%H:%M') if lembur.JAM_IN else '-',
                'jam_out': lembur.JAM_OUT.strftime('%H:%M') if lembur.JAM_OUT else '-',
                'jam_baku_in': lembur.JAM_BAKU_IN.strftime('%H:%M') if lembur.JAM_BAKU_IN else '-',
                'jam_baku_out': lembur.JAM_BAKU_OUT.strftime('%H:%M') if lembur.JAM_BAKU_OUT else '-',
                'keterangan': lembur.KETERANGAN or '',
                'no_surat': lembur.NO_SURAT or '',
                'unit_kerja': unit.NAMA_UNIT_KERJA if unit else '-',
                'update_by': lembur.UPDATE_BY or '',
                'update_date': lembur.UPDATE_DATE.strftime('%d/%m/%Y %H:%M') if lembur.UPDATE_DATE else '',
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


def api_cari_lembur_manual_delete():
    """API: Delete data lembur manual"""
    try:
        data = request.get_json()
        lembur_id = data.get('id', '')
        
        if not lembur_id:
            return jsonify({'error': 'ID tidak ditemukan'})
        
        try:
            finger_id, tgl_kerja = lembur_id.split('|', 1)
        except ValueError:
            return jsonify({'error': 'ID lembur tidak valid'})

        result = Lembur.query.filter(
            Lembur.FINGER_ID == finger_id,
            Lembur.TGL_KERJA == tgl_kerja
        ).delete()

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{result} data berhasil dihapus'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})


def api_cari_lembur_manual_update():
    """API: Update data lembur manual"""
    try:
        data = request.get_json()
        lembur_id = data.get('id', '')
        jam_in = data.get('jam_in', '')
        jam_out = data.get('jam_out', '')
        keterangan = data.get('keterangan', '')
        no_surat = data.get('no_surat', '')
        
        if not lembur_id:
            return jsonify({'error': 'ID tidak ditemukan'})
        
        try:
            finger_id, tgl_kerja = lembur_id.split('|', 1)
        except ValueError:
            return jsonify({'error': 'ID lembur tidak valid'})

        lembur = Lembur.query.filter(
            Lembur.FINGER_ID == finger_id,
            Lembur.TGL_KERJA == tgl_kerja
        ).first()

        if not lembur:
            return jsonify({'error': 'Data tidak ditemukan'})
        
        if jam_in:
            tgl = lembur.TGL_KERJA.strftime('%Y-%m-%d') if lembur.TGL_KERJA else datetime.now().strftime('%Y-%m-%d')
            lembur.JAM_IN = datetime.strptime(f"{tgl} {jam_in}", '%Y-%m-%d %H:%M')
        if jam_out:
            tgl = lembur.TGL_KERJA.strftime('%Y-%m-%d') if lembur.TGL_KERJA else datetime.now().strftime('%Y-%m-%d')
            lembur.JAM_OUT = datetime.strptime(f"{tgl} {jam_out}", '%Y-%m-%d %H:%M')
        if keterangan:
            lembur.KETERANGAN = keterangan
        if no_surat:
            lembur.NO_SURAT = no_surat
        
        lembur.UPDATE_BY = 'admin'
        lembur.UPDATE_DATE = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Data berhasil diupdate'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)})