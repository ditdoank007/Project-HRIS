# controllers/dashboard_1DataAbsensiController.py
from flask import render_template, request, jsonify, session, send_file
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import func, text
from app import db
from app.helpers.attendanceNormalizationHelper import AttendanceNormalizationEngine
from app.services.attendanceNormalizationService import AttendanceNormalizationService
from app.models.absensiModel import Absensi
from app.models.lemburModel import Lembur
from app.models.pegawaiModel import Pegawai
from app.utils.pegawaiHelper import search_operational_pegawai
from app.models.unitKerjaModel import MfUnitKerja
from app.models.kalenderModel import MfKalender
from app.models.potModel import MfPot
from app.models.classModel import MfClass
from app.models.dinasLuarModel import DinasLuar
from app.models.jabatanModel import MfJabatan
from app.models.timeRecorderModel import TimeRecorder
from app.models.jamKerjaModel import MfJamKerja
from app.models.loadFingerModel import MfLoadFinger
from app.models.logActivityModel import LogActivity
from app.models.dinasLuarModel import DinasLuar
from app.models.mediaInformasiModel import MediaInformasi
from app.controllers.reportExportController import (
    REPORT_COLORS,
    ket_color_key,
)
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
    API pencarian pegawai untuk form Absensi Non Finger.

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
        #
        # Keterlambatan dapat dikompensasi oleh kelebihan
        # waktu pulang.
        #
        # Contoh:
        #   terlambat 7 menit
        #   pulang 10 menit lebih lambat
        #   TLM bersih = 7 - 10 = -3
        #
        # Jika seluruh keterlambatan sudah terkompensasi,
        # TOTAL TLM harus menjadi 0.
        #
        if awal_tlm > 0 and awal_tlm <= 30:
            total_tlm = awal_tlm - total_psw
        else:
            total_tlm = awal_tlm

        if total_tlm <= 0:
            total_tlm = 0
        
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
    """API: Simpan absensi non finger ke RAW + TIME_RECORDER."""
    try:
        data = request.get_json() or {}

        nip = str(data.get('finger_id', '')).strip()
        tgl = str(data.get('tgl', '')).strip()
        jam_in = str(data.get('jam_in', '')).strip()
        jam_out = str(data.get('jam_out', '')).strip()
        shift = str(data.get('shift', '1')).strip()
        ket_in = str(data.get('ket_in', '')).strip()
        ket_out = str(data.get('ket_out', '')).strip()
        mode = int(data.get('mode', 0))

        if not nip or not tgl:
            return jsonify({
                'success': False,
                'error': 'NIP dan Tanggal harus diisi'
            }), 400

        if mode not in [0, 1, 2]:
            return jsonify({
                'success': False,
                'error': 'Mode absensi tidak valid'
            }), 400

        pegawai = (
            Pegawai.query
            .filter(Pegawai.NIP == nip)
            .first()
        )

        if not pegawai:
            return jsonify({
                'success': False,
                'error': f'Pegawai dengan NIP {nip} tidak ditemukan'
            }), 404

        finger_id = str(pegawai.FINGER_ID or '').strip()

        if not finger_id:
            return jsonify({
                'success': False,
                'error': 'FingerID pegawai belum tersedia'
            }), 400

        try:
            finger_id_int = int(finger_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'FingerID {finger_id} bukan angka valid'
            }), 400

        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')

        tgl_cek_in = tgl_date
        tgl_cek_out = tgl_date + timedelta(days=1) if shift == '2' else tgl_date

        events = []

        if mode in [0, 1] and jam_in:
            events.append({
                'waktu': datetime.strptime(
                    f"{tgl_cek_in.strftime('%Y-%m-%d')} {jam_in}",
                    '%Y-%m-%d %H:%M'
                ),
                'status': 'IN',
                'punch': 0,
                'keterangan': ket_in or 'MANUAL'
            })

        if mode in [0, 2] and jam_out:
            events.append({
                'waktu': datetime.strptime(
                    f"{tgl_cek_out.strftime('%Y-%m-%d')} {jam_out}",
                    '%Y-%m-%d %H:%M'
                ),
                'status': 'OUT',
                'punch': 1,
                'keterangan': ket_out or 'MANUAL'
            })

        if not events:
            return jsonify({
                'success': False,
                'error': 'Jam masuk atau jam pulang harus diisi'
            }), 400

        raw_start = min(event['waktu'] for event in events)
        raw_end = max(event['waktu'] for event in events)

        # ============================================================
        # Hapus RAW manual lama untuk pegawai/periode yang sama.
        # DEVICE_IP='999' = sumber Absensi Non Finger.
        # ============================================================
        db.session.execute(
            text("""
                DELETE FROM FINGER_HARVEST_RAW
                WHERE USER_ID = :user_id
                  AND DEVICE_IP = '999'
                  AND WAKTU >= :raw_start
                  AND WAKTU <= :raw_end
            """),
            {
                'user_id': finger_id,
                'raw_start': raw_start,
                'raw_end': raw_end,
            }
        )

        # ============================================================
        # Hapus TIME_RECORDER manual lama.
        # Tetap dipertahankan untuk kompatibilitas modul lama.
        # ============================================================
        db.session.query(TimeRecorder).filter(
            TimeRecorder.KET_INJECT == nip,
            TimeRecorder.MESIN == '999',
            TimeRecorder.WAKTU >= raw_start,
            TimeRecorder.WAKTU <= raw_end
        ).delete(synchronize_session=False)

        for event in events:
            waktu = event['waktu']
            status = event['status']
            punch = event['punch']

            # ========================================================
            # 1. RAW ATTENDANCE
            # ========================================================
            db.session.execute(
                text("""
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
                        :harvest_date,
                        '999',
                        NULL,
                        'ABSENSI NON FINGER',
                        :finger_id,
                        NULL,
                        :user_id,
                        :waktu,
                        :status,
                        :punch
                    )
                """),
                {
                    'harvest_date': waktu.date(),
                    'finger_id': finger_id_int,
                    'user_id': finger_id,
                    'waktu': waktu,
                    'status': status,
                    'punch': punch,
                }
            )

            # ========================================================
            # 2. TIME_RECORDER
            # ========================================================
            db.session.add(
                TimeRecorder(
                    FINGER_ID=finger_id,
                    WAKTU=waktu,
                    STATUS=status,
                    MESIN='999',
                    KET='MANUAL',
                    TRANSAKSI='MANUAL',
                    KET_INJECT=nip,
                    UPDATE_IN_BY='admin',
                    UPDATE_DATE=datetime.now()
                )
            )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Data absensi manual berhasil disimpan '
                f'untuk {nip}. '
                f'{len(events)} record masuk RAW dan TIME_RECORDER.'
            )
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def api_absensi_non_finger_delete():
    """API: Hapus SATU transaksi Absensi Non Finger berdasarkan FingerID + waktu + status + mesin."""
    try:
        data = request.get_json() or {}

        finger_id = str(data.get('finger_id', '')).strip()
        waktu_raw = str(data.get('waktu', '')).strip()
        status = str(data.get('status', '')).strip().upper()
        mesin = str(data.get('mesin', '')).strip()

        if not finger_id or not waktu_raw or not status or not mesin:
            return jsonify({
                'success': False,
                'error': 'FingerID, waktu, status, dan mesin harus diisi'
            }), 400

        if mesin != '999':
            return jsonify({
                'success': False,
                'error': 'Hanya data Absensi Non Finger (MESIN=999) yang dapat dihapus'
            }), 400

        if status not in ('IN', 'OUT'):
            return jsonify({
                'success': False,
                'error': 'Status transaksi tidak valid'
            }), 400

        try:
            waktu = datetime.strptime(
                waktu_raw,
                '%Y-%m-%d %H:%M:%S'
            )
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Format waktu tidak valid'
            }), 400

        # ============================================================
        # IDENTITAS UTAMA = FingerID.
        # NIP tidak digunakan sebagai kunci transaksi.
        # ============================================================
        pegawai = (
            Pegawai.query
            .filter(Pegawai.FINGER_ID == finger_id)
            .first()
        )

        if not pegawai:
            return jsonify({
                'success': False,
                'error': f'Pegawai dengan FingerID {finger_id} tidak ditemukan'
            }), 404

        punch = 0 if status == 'IN' else 1

        # ============================================================
        # 1. Hapus RAW exact.
        # ============================================================
        raw_result = db.session.execute(
            text("""
                DELETE FROM FINGER_HARVEST_RAW
                WHERE USER_ID = :finger_id
                  AND DEVICE_IP = '999'
                  AND WAKTU = :waktu
                  AND PUNCH = :punch
            """),
            {
                'finger_id': finger_id,
                'waktu': waktu,
                'punch': punch,
            }
        )

        # ============================================================
        # 2. Hapus TIME_RECORDER exact.
        #
        # PK legacy:
        # FingerID + Waktu + Status + Mesin
        # ============================================================
        tr_result = db.session.query(TimeRecorder).filter(
            TimeRecorder.FINGER_ID == finger_id,
            TimeRecorder.WAKTU == waktu,
            TimeRecorder.STATUS == status,
            TimeRecorder.MESIN == mesin,
            TimeRecorder.TRANSAKSI == 'MANUAL'
        ).delete(synchronize_session=False)

        # ============================================================
        # KEDUA tabel wajib memiliki transaksi.
        # Jangan pernah commit kondisi parsial.
        # ============================================================
        if raw_result.rowcount != 1 or tr_result != 1:
            db.session.rollback()

            return jsonify({
                'success': False,
                'error': (
                    'Transaksi manual tidak dapat dihapus karena '
                    'data RAW dan TIME_RECORDER tidak berpasangan '
                    f'(RAW={raw_result.rowcount or 0}, '
                    f'TIME_RECORDER={tr_result or 0})'
                )
            }), 409

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Transaksi FingerID {finger_id} '
                f'{waktu.strftime("%d/%m/%Y %H:%M:%S")} {status} berhasil dihapus'
            ),
            'raw_deleted': raw_result.rowcount or 0,
            'time_recorder_deleted': tr_result or 0
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def api_absensi_non_finger_edit():
    """API: Edit SATU transaksi Absensi Non Finger berdasarkan FingerID."""
    try:
        data = request.get_json() or {}

        finger_id = str(data.get('finger_id', '')).strip()

        old_waktu_raw = str(data.get('old_waktu', '')).strip()
        old_status = str(data.get('old_status', '')).strip().upper()
        old_mesin = str(data.get('old_mesin', '')).strip()

        new_waktu_raw = str(data.get('new_waktu', '')).strip()
        new_status = str(data.get('new_status', '')).strip().upper()

        if not all([
            finger_id,
            old_waktu_raw,
            old_status,
            old_mesin,
            new_waktu_raw,
            new_status
        ]):
            return jsonify({
                'success': False,
                'error': 'Data transaksi belum lengkap'
            }), 400

        if old_mesin != '999':
            return jsonify({
                'success': False,
                'error': 'Hanya data Absensi Non Finger (MESIN=999) yang dapat diedit'
            }), 400

        if old_status not in ('IN', 'OUT') or new_status not in ('IN', 'OUT'):
            return jsonify({
                'success': False,
                'error': 'Status transaksi tidak valid'
            }), 400

        try:
            # Terima format dari tabel maupun input datetime-local browser.
            old_waktu_raw = old_waktu_raw.replace('T', ' ')
            new_waktu_raw = new_waktu_raw.replace('T', ' ')

            try:
                old_waktu = datetime.strptime(
                    old_waktu_raw,
                    '%Y-%m-%d %H:%M:%S'
                )
            except ValueError:
                old_waktu = datetime.strptime(
                    old_waktu_raw,
                    '%Y-%m-%d %H:%M'
                )

            try:
                new_waktu = datetime.strptime(
                    new_waktu_raw,
                    '%Y-%m-%d %H:%M:%S'
                )
            except ValueError:
                new_waktu = datetime.strptime(
                    new_waktu_raw,
                    '%Y-%m-%d %H:%M'
                )

        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Format waktu tidak valid'
            }), 400

        # ============================================================
        # IDENTITAS UTAMA = FingerID.
        # FingerID TIDAK boleh berubah melalui Edit transaksi.
        # ============================================================
        pegawai = (
            Pegawai.query
            .filter(Pegawai.FINGER_ID == finger_id)
            .first()
        )

        if not pegawai:
            return jsonify({
                'success': False,
                'error': f'Pegawai dengan FingerID {finger_id} tidak ditemukan'
            }), 404

        # ============================================================
        # Cari transaksi lama secara EXACT.
        # ============================================================
        old_tr = (
            TimeRecorder.query
            .filter(
                TimeRecorder.FINGER_ID == finger_id,
                TimeRecorder.WAKTU == old_waktu,
                TimeRecorder.STATUS == old_status,
                TimeRecorder.MESIN == old_mesin,
                TimeRecorder.TRANSAKSI == 'MANUAL'
            )
            .first()
        )

        if not old_tr:
            return jsonify({
                'success': False,
                'error': 'Transaksi TIME_RECORDER lama tidak ditemukan'
            }), 404

        old_punch = 0 if old_status == 'IN' else 1
        new_punch = 0 if new_status == 'IN' else 1

        # ============================================================
        # Jangan izinkan bentrok dengan transaksi manual lain.
        # ============================================================
        if (
            new_waktu != old_waktu
            or new_status != old_status
        ):
            duplicate_tr = (
                TimeRecorder.query
                .filter(
                    TimeRecorder.FINGER_ID == finger_id,
                    TimeRecorder.WAKTU == new_waktu,
                    TimeRecorder.STATUS == new_status,
                    TimeRecorder.MESIN == old_mesin,
                    TimeRecorder.TRANSAKSI == 'MANUAL'
                )
                .first()
            )

            if duplicate_tr:
                return jsonify({
                    'success': False,
                    'error': 'Sudah ada transaksi manual pada FingerID, waktu, status, dan mesin tersebut'
                }), 409

        # ============================================================
        # Cari RAW lama secara EXACT.
        # ============================================================
        raw_old = db.session.execute(
            text("""
                SELECT ID
                FROM FINGER_HARVEST_RAW
                WHERE USER_ID = :finger_id
                  AND DEVICE_IP = '999'
                  AND WAKTU = :waktu
                  AND PUNCH = :punch
                ORDER BY ID DESC
                LIMIT 1
            """),
            {
                'finger_id': finger_id,
                'waktu': old_waktu,
                'punch': old_punch,
            }
        ).mappings().first()

        # ============================================================
        # RAW wajib ada.
        # TIME_RECORDER sudah diverifikasi di atas.
        #
        # Jika salah satu tidak ada, jangan ubah apa pun.
        # ============================================================
        if not raw_old:
            db.session.rollback()

            return jsonify({
                'success': False,
                'error': (
                    'Transaksi FINGER_HARVEST_RAW lama tidak ditemukan. '
                    'Edit dibatalkan agar RAW dan TIME_RECORDER tetap sinkron.'
                )
            }), 409

        # ============================================================
        # UPDATE TIME_RECORDER.
        #
        # Karena PK TIME_RECORDER berubah bila waktu/status berubah,
        # record lama dihapus lalu record baru dibuat dalam transaction.
        # ============================================================
        old_ket = old_tr.KET
        old_transaksi = old_tr.TRANSAKSI
        old_update_by = old_tr.UPDATE_IN_BY
        old_ket_inject = old_tr.KET_INJECT
        old_ref_inject = old_tr.REF_INJECT
        old_trx = old_tr.TRX

        db.session.delete(old_tr)
        db.session.flush()

        db.session.add(
            TimeRecorder(
                FINGER_ID=finger_id,
                WAKTU=new_waktu,
                STATUS=new_status,
                MESIN=old_mesin,
                KET=old_ket or 'MANUAL',
                TRANSAKSI=old_transaksi or 'MANUAL',
                UPDATE_IN_BY=old_update_by or 'admin',
                UPDATE_DATE=datetime.now(),
                KET_INJECT=old_ket_inject,
                REF_INJECT=old_ref_inject,
                TRX=old_trx
            )
        )

        # ============================================================
        # UPDATE RAW.
        # ============================================================
        if raw_old:
            db.session.execute(
                text("""
                    UPDATE FINGER_HARVEST_RAW
                    SET WAKTU = :new_waktu,
                        HARVEST_DATE = :new_harvest_date,
                        STATUS = :new_status,
                        PUNCH = :new_punch
                    WHERE ID = :raw_id
                """),
                {
                    'new_waktu': new_waktu,
                    'new_harvest_date': new_waktu.date(),
                    'new_status': new_status,
                    'new_punch': new_punch,
                    'raw_id': raw_old['ID'],
                }
            )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Transaksi FingerID {finger_id} berhasil diubah '
                f'menjadi {new_waktu.strftime("%d/%m/%Y %H:%M:%S")} {new_status}'
            )
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

    Sumber data mengikuti HRIS 2013:
        TIME_RECORDER

    VIEW DATA hanya membaca log fingerprint yang sudah tersimpan
    di TIME_RECORDER. Tidak melakukan normalisasi dan tidak
    mengubah ABSENSI.
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

        params = {'tgl_awal': tgl_awal, 'tgl_akhir': tgl_akhir}
        field_mapping = {
            'NIP': 'p.NIP', 'Nama': 'p.Nama', 'NAMA': 'p.Nama',
            'FingerID': 'src.FINGER_ID', 'UnitKerja': 'uk.UnitKerjaName',
            'Unit': 'uk.UnitKerjaName', 'UnitKerjaName': 'uk.UnitKerjaName',
            'Jabatan': 'p.Jabatan', 'Gol': 'p.Gol', 'Gol-Pangkat': 'p.Gol',
            'Status': 'src.STATUS', 'Transaksi': 'src.TRANSAKSI',
        }
        conditions = []
        for idx, (field_name, field_value) in enumerate((
            (filter_field1, filter_value1),
            (filter_field2, filter_value2),
        ), start=1):
            if not field_name or not field_value:
                continue
            field = field_mapping.get(field_name)
            if not field:
                continue
            param_name = f'filter_value{idx}'
            conditions.append(f"{field} LIKE :{param_name}")
            params[param_name] = f"%{field_value}%"

        # VIEW DATA mengikuti HRIS 2013.
        # TAB 1 hanya membaca TIME_RECORDER. RAW tidak digabung di sini.
        # FINGER_HARVEST_RAW tetap menjadi sumber tambahan untuk TAB 2
        # NORMALISASI agar View Data tetap ringan untuk periode bulanan.
        source_field_map = {
            'NIP': 'p.NIP', 'Nama': 'p.Nama', 'NAMA': 'p.Nama',
            'UnitKerja': 'uk.UnitKerjaName', 'Unit': 'uk.UnitKerjaName',
            'UnitKerjaName': 'uk.UnitKerjaName',
            'Jabatan': 'p.Jabatan', 'Gol': 'p.Gol', 'Gol-Pangkat': 'p.Gol',
            'FingerID': 'tr.FingerID',
            'Status': 'tr.Status', 'Transaksi': 'tr.Transaksi',
        }

        conditions = []
        for idx, (field_name, field_value) in enumerate((
            (filter_field1, filter_value1),
            (filter_field2, filter_value2),
        ), start=1):
            if not field_name or not field_value:
                continue
            field = source_field_map.get(field_name)
            if not field:
                continue
            param_name = f'filter_value{idx}'
            conditions.append(f"{field} LIKE :{param_name}")
            params[param_name] = f"%{field_value}%"

        filter_sql = ''
        if conditions:
            filter_sql = ' AND ' + ' AND '.join(conditions)

        sql = text(f"""
            SELECT
                tr.FingerID AS FINGER_ID,
                tr.Waktu AS WAKTU,
                tr.Status AS STATUS,
                tr.Transaksi AS TRANSAKSI,
                p.NIP,
                p.Nama AS NAMA,
                p.Gol AS GOL,
                g.Pangkat AS PANGKAT,
                p.UnitKerja AS UNIT_KERJA,
                uk.UnitKerjaName AS UNIT_KERJA_NAME,
                p.IsVIP AS IS_VIP
            FROM TIME_RECORDER tr
            INNER JOIN PEGAWAI p
                ON p.FingerID = tr.FingerID
            LEFT JOIN MF_GOL g
                ON g.Gol = p.Gol
            LEFT JOIN MF_UNIT_KERJA uk
                ON uk.IDUnitKerja = p.UnitKerja
            WHERE tr.Waktu >= :tgl_awal
              AND tr.Waktu < :tgl_akhir
              AND UPPER(TRIM(COALESCE(p.isKeluar, ''))) IN ('N', '0')
              AND UPPER(TRIM(COALESCE(uk.isUse, ''))) IN ('Y', '1')
              AND tr.FingerID IS NOT NULL
              AND TRIM(CAST(tr.FingerID AS CHAR)) <> ''
              AND p.NIP IS NOT NULL
              AND TRIM(p.NIP) <> ''
              {filter_sql}
            ORDER BY tr.FingerID, tr.Waktu
        """)

        rows = db.session.execute(sql, params).mappings().all()
        data = []
        cache_rows = []

        for i, r in enumerate(rows, 1):
            status = str(r['STATUS'] or '').strip().upper()
            row = {
                'no': i,
                'finger_id': str(r['FINGER_ID'] or ''),
                'nip': r['NIP'] or '',
                'nama': r['NAMA'] or '',
                'gol': (
                    f"{r['GOL']} - {r['PANGKAT']}"
                    if r['GOL'] and r['PANGKAT']
                    else (r['GOL'] or '')
                ),
                'unit_kerja': (
                    f"{r['UNIT_KERJA']} - {r['UNIT_KERJA_NAME']}"
                    if r['UNIT_KERJA'] and r['UNIT_KERJA_NAME']
                    else (r['UNIT_KERJA'] or '')
                ),
                'waktu': r['WAKTU'].strftime('%Y-%m-%d %H:%M:%S') if r['WAKTU'] else '',
                'status': status,
                'punch': None,
                'device_ip': '',
                'transaksi': r['TRANSAKSI'] or '',
            }
            data.append(row)
            cache_rows.append(row)

        _NORMALISASI_CACHE['import'] = cache_rows
        if not data:
            return jsonify({'success': True, 'data': [], 'total': 0, 'message': 'Data Log Finger Print Kosong'})
        return jsonify({'success': True, 'data': data, 'total': len(data)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'data': []})

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
        # TIME_RECORDER + FINGER_HARVEST_RAW
        #
        # Jangan lagi bergantung pada _NORMALISASI_CACHE['import'].
        # RAW adalah sumber permanen hasil import file .DAT.
        # ============================================================

        from sqlalchemy import text, bindparam

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
            'FingerID': 'p.FingerID',
            'UnitKerja': 'uk.UnitKerjaName',
            'Unit': 'uk.UnitKerjaName',
            'Unit Kerja': 'uk.UnitKerjaName',
            'Jabatan': 'p.Jabatan',
            'Gol': 'p.Gol',
            'Gol-Pangkat': 'p.Gol',
        }

        filter_clauses = []
        source_filter_clauses = []
        filter_params = {}

        # Resolve the selected employee(s) first. This avoids forcing MySQL
        # to scan the whole TIME_RECORDER/FINGER_HARVEST_RAW period and then
        # discover that only one employee (e.g. Nama=Nanang Sigit) is needed.
        employee_filter_clauses = []
        for idx, (field, value) in enumerate(
            (
                (filter_field1, filter_value1),
                (filter_field2, filter_value2),
            ),
            start=1
        ):
            if not value:
                continue
            employee_column = {
                'NIP': 'p0.NIP',
                'Nama': 'p0.Nama',
                'NAMA': 'p0.Nama',
                'FingerID': 'p0.FingerID',
                'UnitKerja': 'uk0.UnitKerjaName',
                'Unit': 'uk0.UnitKerjaName',
                'Unit Kerja': 'uk0.UnitKerjaName',
                'Jabatan': 'p0.Jabatan',
                'Gol': 'p0.Gol',
                'Gol-Pangkat': 'p0.Gol',
            }.get(field)
            if employee_column:
                param_name = f'filter_value{idx}'
                employee_filter_clauses.append(
                    f"{employee_column} LIKE :{param_name}"
                )
                filter_params[param_name] = f'%{value}%'

        # Resolve the employee universe ONCE for both attendance sources.
        # This is the bulk-processing pattern: the normalization request
        # works for all selected employees in one pass, while TIME_RECORDER
        # can use its PRIMARY (FingerID, Waktu, Status, Mesin) index.
        employee_finger_ids = None
        if employee_filter_clauses:
            employee_sql = text(f"""
                SELECT DISTINCT p0.FingerID
                FROM PEGAWAI p0
                LEFT JOIN MF_UNIT_KERJA uk0
                    ON uk0.IDUnitKerja = p0.UnitKerja
                WHERE {' AND '.join(employee_filter_clauses)}
                  AND UPPER(TRIM(COALESCE(p0.isKeluar, ''))) IN ('N', '0')
                  AND UPPER(TRIM(COALESCE(uk0.isUse, ''))) IN ('Y', '1')
                  AND p0.FingerID IS NOT NULL
            """)
            employee_rows = db.session.execute(
                employee_sql,
                filter_params
            ).scalars().all()
        else:
            employee_sql = text("""
                SELECT DISTINCT p0.FingerID
                FROM PEGAWAI p0
                LEFT JOIN MF_UNIT_KERJA uk0
                    ON uk0.IDUnitKerja = p0.UnitKerja
                WHERE UPPER(TRIM(COALESCE(p0.isKeluar, ''))) IN ('N', '0')
                  AND UPPER(TRIM(COALESCE(uk0.isUse, ''))) IN ('Y', '1')
                  AND p0.FingerID IS NOT NULL
            """)
            employee_rows = db.session.execute(
                employee_sql
            ).scalars().all()

        employee_finger_ids = [
            str(value) for value in employee_rows if value is not None
        ]

        if not employee_finger_ids:
            return jsonify({
                'success': True,
                'data': [],
                'total': 0,
                'message': 'Data Log Finger Print Kosong'
            })

        source_filter_map = {
            'NIP': 'p0.NIP',
            'Nama': 'p0.Nama',
            'NAMA': 'p0.Nama',
            'FingerID': 'p0.FingerID',
            'UnitKerja': 'uk0.UnitKerjaName',
            'Unit': 'uk0.UnitKerjaName',
            'Unit Kerja': 'uk0.UnitKerjaName',
            'Jabatan': 'p0.Jabatan',
            'Gol': 'p0.Gol',
            'Gol-Pangkat': 'p0.Gol',
        }

        # When an employee filter is present, use the resolved FingerID list
        # directly in both source branches. This is much cheaper than joining
        # every attendance row to PEGAWAI and applying LIKE afterwards.
        if employee_finger_ids is not None:
            source_filter_clauses = [
                "AND tr.FingerID IN :employee_finger_ids"
            ]
            raw_source_filter_clauses = [
                "AND r.USER_ID IN :employee_finger_ids"
            ]
        else:
            raw_source_filter_clauses = []

        for idx, (field, value) in enumerate(
            (
                (filter_field1, filter_value1),
                (filter_field2, filter_value2),
            ),
            start=1
        ):
            column = filter_column_map.get(field)
            source_column = source_filter_map.get(field)

            if column and value:
                param_name = f'filter_value{idx}'
                filter_clauses.append(
                    f"AND {column} LIKE :{param_name}"
                )
                filter_params[param_name] = f'%{value}%'

            if source_column and value and employee_finger_ids is None:
                param_name = f'filter_value{idx}'
                source_filter_clauses.append(
                    f"AND {source_column} LIKE :{param_name}"
                )

        filter_sql = ''
        if filter_clauses:
            filter_sql = '\n              ' + '\n              '.join(
                filter_clauses
            )

        source_filter_sql = ''
        raw_source_filter_sql = ''
        if source_filter_clauses:
            source_filter_sql = '\n                  ' + '\n                  '.join(
                source_filter_clauses
            )
        if raw_source_filter_clauses:
            raw_source_filter_sql = '\n                  ' + '\n                  '.join(
                raw_source_filter_clauses
            )

        raw_sql = text(f"""
            SELECT
                src.FINGER_ID,
                p.FingerID AS PEGAWAI_FINGER_ID,
                src.USER_ID,
                src.WAKTU,
                src.STATUS,
                src.PUNCH,
                src.DEVICE_IP,
                p.NIP,
                p.Nama AS NAMA,
                p.Gol AS GOL,
                p.UnitKerja AS UNIT_KERJA,
                p.IsVIP AS IS_VIP
            FROM (
                /* TIME_RECORDER adalah event log aktif:
                   termasuk fingerprint mesin, manual finger,
                   dan event sintetis VIP yang legacy simpan
                   sebagai MESIN=999 / TRANSAKSI=MANUAL. */
                SELECT
                    tr.FingerID AS FINGER_ID,
                    tr.FingerID AS USER_ID,
                    tr.Waktu AS WAKTU,
                    tr.Status AS STATUS,
                    CASE
                        WHEN UPPER(TRIM(tr.Status)) = 'IN' THEN 0
                        WHEN UPPER(TRIM(tr.Status)) = 'OUT' THEN 1
                        ELSE NULL
                    END AS PUNCH,
                    tr.Mesin AS DEVICE_IP
                FROM TIME_RECORDER tr
                WHERE tr.Waktu >= :tgl_awal_raw
                  AND tr.Waktu < :tgl_akhir_raw
                  {source_filter_sql}

                UNION ALL

                /* File .DAT / RAW yang belum masuk TIME_RECORDER.
                   Jika event sudah ada di TIME_RECORDER, jangan
                   menggandakan record. */
                SELECT
                    r.FINGER_ID,
                    r.USER_ID,
                    r.WAKTU,
                    r.STATUS,
                    r.PUNCH,
                    r.DEVICE_IP
                FROM FINGER_HARVEST_RAW r
                WHERE r.WAKTU >= :tgl_awal_raw
                  AND r.WAKTU < :tgl_akhir_raw
                  {raw_source_filter_sql}
                  AND NOT EXISTS (
                      SELECT 1
                      FROM TIME_RECORDER tr2
                      WHERE tr2.FingerID = r.USER_ID
                        AND tr2.Waktu = r.WAKTU
                        AND tr2.Status = CASE
                            WHEN r.PUNCH = 0 THEN 'IN'
                            WHEN r.PUNCH = 1 THEN 'OUT'
                            ELSE r.STATUS
                        END
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM TIME_RECORDER tr3
                      WHERE tr3.FingerID = (CAST(r.FINGER_ID AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_unicode_ci)
                        AND tr3.Waktu = r.WAKTU
                        AND tr3.Status = CASE
                            WHEN r.PUNCH = 0 THEN 'IN'
                            WHEN r.PUNCH = 1 THEN 'OUT'
                            ELSE r.STATUS
                        END
                  )
            ) src
            INNER JOIN PEGAWAI p
                ON src.USER_ID = p.FingerID
            INNER JOIN MF_UNIT_KERJA uk
                ON uk.IDUnitKerja = p.UnitKerja
            WHERE 1=1
              {filter_sql}
            ORDER BY CAST(p.UnitKerja AS UNSIGNED), src.FINGER_ID, src.WAKTU
        """)

        query_params = {
            # Shift 2 Siaga membutuhkan fingerprint
            # mulai dari malam tanggal sebelumnya.
            'tgl_awal_raw': tgl_awal - timedelta(days=1),
            'tgl_akhir_raw': tgl_akhir + timedelta(days=1),
            **filter_params,
        }

        if employee_finger_ids is not None:
            raw_sql = raw_sql.bindparams(
                bindparam('employee_finger_ids', expanding=True)
            )
            query_params['employee_finger_ids'] = employee_finger_ids

        raw_rows = db.session.execute(
            raw_sql,
            query_params
        ).mappings().all()

        # FINGER_HARVEST_RAW boleh kosong.
        #
        # Dinas Luar StatusUM 1/2 tetap harus dapat
        # menghasilkan row normalisasi walaupun tidak
        # ada fingerprint.
        if not raw_rows:
            raw_rows = []

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
                    str(r['PEGAWAI_FINGER_ID']),
                    waktu.strftime('%Y-%m-%d')
                )
            ].append({
                # Business identity = FingerID pegawai.
                'finger_id': str(r['PEGAWAI_FINGER_ID']),
                # Raw machine UID tetap dipertahankan untuk
                # identitas record saat Shift 2 dikonsumsi.
                'FINGER_ID': r['FINGER_ID'],
                'nip': r['NIP'] or '',
                'nama': r['NAMA'] or '',
                'gol': r['GOL'] or '',
                'unit_kerja': r['UNIT_KERJA'] or '',
                'is_vip': str(r['IS_VIP'] or '').strip().upper() in ('Y', '1', 'YES', 'TRUE'),
                'waktu': waktu.strftime('%Y-%m-%d %H:%M:%S'),
                'status': status,
                'punch': r['PUNCH'],
                'device_ip': r['DEVICE_IP'] or '',
            })

        # grouped boleh kosong.
        #
        # Dinas Luar StatusUM 1/2 dapat menghasilkan
        # row normalisasi walaupun tidak ada fingerprint.
        if not grouped:
            grouped = {}

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
            # HRIS 2013: status 3 adalah tanda KEHADIRAN
            # Piket Siaga yang sudah diabsen/ditandai Kagahar.
            # SHIFT_2 hanya menunjukkan jenis shift, bukan status hadir.
            hadir_shift2 = (
                int(sr['StatusID'] or 0) == 3
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

        # ============================================================
        # SIAGA SHIFT 1
        #
        # Shift 1 tetap memakai hasil pairing reguler, tetapi status
        # presentation harus dipertahankan sebagai SIAGA di ABSENSI.
        # Sumber penandanya adalah LOG_ACTIVITIY Piket Siaga.
        # ============================================================

        shift1_sql = text("""
            SELECT
                NIP,
                ActivityDate,
                StatusID,
                shift1,
                Shift,
                StatusTrx
            FROM LOG_ACTIVITIY
            WHERE Activity = 'Piket Siaga'
              AND Shift = '1'
              AND ActivityDate >= :activity_awal
              AND ActivityDate <= :activity_akhir
              AND StatusTrx = '-'
              AND StatusID = 3
        """)

        shift1_rows = db.session.execute(
            shift1_sql,
            {
                'activity_awal': tgl_awal.date(),
                'activity_akhir': tgl_akhir.date(),
            }
        ).mappings().all()

        shift1_map = {}

        for sr in shift1_rows:
            nip_siaga = str(sr['NIP'] or '').strip()

            if not nip_siaga or not sr['ActivityDate']:
                continue

            activity_date = sr['ActivityDate']

            if hasattr(activity_date, 'date'):
                activity_date = activity_date.date()

            # Legacy Shift 1 siaga tampil pada tanggal yang sama.
            shift1_map[
                (nip_siaga, activity_date.strftime('%Y-%m-%d'))
            ] = True

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
        special_potongan_list = MfPot.query.filter(
            MfPot.KATEGORI.in_(['ijin', 'sakit', 'cuti']),
            MfPot.TGL_MULAI <= tgl_akhir
        ).all()



        # ============================================================
        # ATTENDANCE NORMALIZATION ENGINE
        #
        # BUSINESS ENGINE TUNGGAL
        #
        # Controller hanya bertugas:
        #   - mengambil data
        #   - menyiapkan dependency
        #   - menentukan konteks Shift 2 Siaga
        #   - memanggil engine
        #   - membentuk response JSON
        #
        # Business calculation TIDAK dilakukan lagi di controller.
        # ============================================================

        normalization_engine = AttendanceNormalizationEngine(
            jam_kerja=jam_kerja_list,
            potongan=potongan_list,
            load_finger=(
                MfLoadFinger.query
                .filter(
                    MfLoadFinger.TGL_MULAI_BERLAKU <= tgl_akhir.date()
                )
                .order_by(
                    MfLoadFinger.TGL_MULAI_BERLAKU.desc(),
                    MfLoadFinger.TRAKSAKSI_ID.desc()
                )
                .all()
            ),
            kalender=kalender_map,
            default_tdk_check=default_tdk_check,
        )

        normalization_service = AttendanceNormalizationService(
            engine=normalization_engine
        )

        result = []
        no = 0

        # ============================================================
        # SHIFT 2 SIAGA
        #
        # LOG_ACTIVITIY menentukan:
        #   ActivityDate = tanggal siaga
        #   target_date  = tanggal ABSENSI (H+1)
        #
        # Engine menentukan:
        #   - window fingerprint
        #   - IN
        #   - OUT
        #   - jam baku
        #   - TLM
        #   - kompensasi TLM-1
        #   - PSW
        #   - kategori/potongan
        # ============================================================

        # ============================================================
        # IDENTITAS RAW FINGERPRINT
        #
        # Jangan menggunakan id(raw).
        #
        # RAW yang dipakai pada proses Shift 2 berasal dari raw_rows,
        # sedangkan proses reguler memakai dictionary baru hasil
        # grouping. Object Python-nya berbeda walaupun record-nya sama.
        #
        # Karena itu identitas RAW harus berbasis nilai record:
        #
        #     FINGER_ID + WAKTU
        #
        # sehingga record yang sama tetap dikenali lintas proses.
        # ============================================================

        def _raw_consumed_key(raw):
            finger_id = (
                raw.get('FINGER_ID')
                or raw.get('finger_id')
                or ''
            )

            waktu = (
                raw.get('WAKTU')
                or raw.get('waktu')
            )

            if hasattr(waktu, 'strftime'):
                waktu = waktu.strftime(
                    '%Y-%m-%d %H:%M:%S'
                )

            return (
                str(finger_id),
                str(waktu or '')
            )

        shift2_consumed = set()

        for (nip_siaga, target_date_str), info in shift2_map.items():

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

            # Piket Siaga tetap harus dinormalisasi walaupun
            # tidak ada RAW fingerprint sama sekali.
            # Missing IN akan menghasilkan TLM-4 melalui engine.
            pegawai_siaga = (
                Pegawai.query
                .filter(Pegawai.NIP == nip_siaga)
                .first()
            )

            if not pegawai_siaga:
                continue

            unit_siaga = (
                MfUnitKerja.query
                .filter(
                    MfUnitKerja.UNIT_KERJA_ID
                    == pegawai_siaga.UNIT_KERJA_ID
                )
                .first()
            )

            if (
                str(pegawai_siaga.IS_KELUAR or '').strip().upper() not in ('N', '0')
                or not unit_siaga
                or str(unit_siaga.IS_USE or '').strip().upper() not in ('Y', '1')
            ):
                continue

            jam_in_dt, jam_out_dt = (
                normalization_service.pair_shift2(
                    raw_person=raw_person,
                    activity_date=activity_date,
                    target_date=target_date.date(),
                )
            )

            if not jam_in_dt and not jam_out_dt:
                continue

            # ========================================================
            # RAW SHIFT 2
            #
            # Business rule pairing dan consumed berada di service.
            # Controller hanya menggunakan hasil service.
            # ========================================================

            consumed_by_service = (
                normalization_service.shift2_consumed(
                    raw_person=raw_person,
                    activity_date=activity_date,
                    target_date=target_date.date(),
                )
            )

            shift2_consumed.update(
                consumed_by_service
            )

            source_raw = None

            # Ambil RAW yang menjadi IN Shift 2 sebagai sumber metadata.
            if jam_in_dt:
                for raw in raw_person:
                    waktu = normalization_engine._parse_waktu(raw)

                    if (
                        waktu == jam_in_dt
                        and (
                            raw.get('punch')
                            if raw.get('punch') is not None
                            else raw.get('PUNCH')
                        ) == 0
                    ):
                        source_raw = raw
                        break

            # Jika tidak ada IN, gunakan RAW OUT sebagai fallback metadata.
            if not source_raw and jam_out_dt:
                for raw in raw_person:
                    waktu = normalization_engine._parse_waktu(raw)

                    if (
                        waktu == jam_out_dt
                        and (
                            raw.get('punch')
                            if raw.get('punch') is not None
                            else raw.get('PUNCH')
                        ) == 1
                    ):
                        source_raw = raw
                        break

            if not source_raw:
                if raw_person:
                    source_raw = raw_person[0]
                else:
                    source_raw = {
                        'FINGER_ID': pegawai_siaga.FINGER_ID,
                        'NAMA': pegawai_siaga.NAMA,
                        'GOL': pegawai_siaga.GOL,
                        'UNIT_KERJA': pegawai_siaga.UNIT_KERJA,
                    }

            is_libur = (
                kalender_map.get(
                    target_date_str,
                    'N'
                ) == 'Y'
            )

            row = normalization_engine.normalize_row(
                nip=nip_siaga,
                finger_id=str(
                    source_raw.get('FINGER_ID') or ''
                ),
                nama=source_raw.get('NAMA') or '',
                gol=source_raw.get('GOL') or '',
                unit_kerja=source_raw.get('UNIT_KERJA') or '',
                tgl_kerja=target_date.date(),
                jam_in=jam_in_dt,
                jam_out=jam_out_dt,
                shift_kerja='2',
                is_libur=is_libur,
                tgl_jam_baku=activity_date,
            )

            if not row:
                continue

            no += 1

            row['no'] = no
            row['shift'] = '2'
            row['shift2_siaga'] = True
            row['siaga_shift'] = 2
            row['siaga'] = True
            row['activity_date_siaga'] = (
                activity_date.strftime('%Y-%m-%d')
                if hasattr(activity_date, 'strftime')
                else str(activity_date)
            )

            result.append(row)

        # ============================================================
        # ABSENSI REGULER
        #
        # Fingerprint yang sudah digunakan Shift 2 tidak boleh
        # diproses kembali.
        #
        # PENTING:
        # ABSENSI legacy memiliki primary key:
        #     FingerID + TglKerja
        #
        # Karena Shift 2 malam H -> H+1 disimpan pada TglKerja H+1,
        # tanggal H+1 yang sudah dimiliki row Shift 2 TIDAK BOLEH
        # dibuat lagi sebagai row reguler. Jika tetap dibuat, akan
        # terbentuk dua row normalisasi untuk key ABSENSI yang sama:
        #
        #   Shift 1 : 00:00 / 09:23
        #   Shift 2 : 19:01 / 09:23
        #
        # lalu EXPORT dapat menimpa hasil Shift 2 menjadi 00:00.
        # ============================================================

        shift2_owned_dates = {
            (
                str(row.get('nip') or '').strip(),
                str(row.get('tgl_kerja') or '').strip(),
            )
            for row in result
            if bool(row.get('shift2_siaga'))
        }

        for (finger_id, tgl_str), logs in grouped.items():

            tgl_dt = datetime.strptime(
                tgl_str,
                '%Y-%m-%d'
            )

            nip_group = str(
                logs[0].get('nip') or ''
            ).strip() if logs else ''

            # Shift 2 adalah pemilik ABSENSI pada TglKerja H+1.
            # Jangan membuat row reguler kedua untuk tanggal yang sama.
            if (
                nip_group,
                tgl_str,
            ) in shift2_owned_dates:
                continue

            filtered_logs = [
                raw
                for raw in logs
                if _raw_consumed_key(raw)
                not in shift2_consumed
                and str(raw.get('device_ip') or '').strip().upper() != 'WEB'
            ]

            if not filtered_logs:
                continue

            nip_reguler = str(
                filtered_logs[0].get('nip') or ''
            ).strip()

            # Fingerprint milik pegawai yang mempunyai konfigurasi
            # Shift 2 tetapi tidak dicentang operator tidak boleh
            # berubah menjadi absensi reguler.
            info = shift2_map.get(
                (nip_reguler, tgl_str)
            )

            if info and not info['hadir']:
                continue

            jam_in_dt, jam_out_dt = (
                normalization_engine.pair_regular(
                    filtered_logs
                )
            )

            is_libur = (
                kalender_map.get(
                    tgl_str,
                    'N'
                ) == 'Y'
            )

            row = normalization_engine.normalize_row(
                nip=nip_reguler,
                finger_id=str(finger_id),
                nama=(
                    filtered_logs[0].get('nama')
                    or filtered_logs[0].get('NAMA')
                    or ''
                ),
                gol=(
                    filtered_logs[0].get('gol')
                    or filtered_logs[0].get('GOL')
                    or ''
                ),
                unit_kerja=(
                    filtered_logs[0].get('unit_kerja')
                    or filtered_logs[0].get('UNIT_KERJA')
                    or ''
                ),
                tgl_kerja=tgl_dt.date(),
                jam_in=jam_in_dt,
                jam_out=jam_out_dt,
                shift_kerja='1',
                is_libur=is_libur,
            )

            if not row:
                continue

            no += 1

            row['no'] = no
            row['shift'] = '1'
            row['shift2_siaga'] = False

            # Pertahankan penanda Siaga Shift 1 sampai tahap EXPORT,
            # sehingga Rekap tetap READ-ONLY dari ABSENSI final.
            is_siaga_shift1 = bool(
                shift1_map.get(
                    (nip_reguler, tgl_str)
                )
            )
            row['siaga_shift'] = 1 if is_siaga_shift1 else None
            row['siaga'] = is_siaga_shift1

            result.append(row)

        # ============================================================
        # DINAS LUAR
        #
        # Layer transaksi khusus.
        #
        # Identity attendance = FingerID.
        #
        # StatusUM:
        #   0 = Tdk Terpotong, wajib cari fingerprint
        #   1 = Terpotong, tidak wajib fingerprint
        #   2 = Tdk Terpotong Penempatan, tidak wajib fingerprint
        #
        # DL tetap berlaku pada hari kerja maupun hari libur.
        #
        # Layer ini TIDAK mengubah FINGER_HARVEST_RAW.
        # ============================================================

        dinas_luar_rows = (
            db.session.query(
                DinasLuar,
                Pegawai
            )
            .join(
                Pegawai,
                db.func.trim(DinasLuar.FINGER_ID)
                == db.func.trim(Pegawai.FINGER_ID)
            )
            .outerjoin(
                MfUnitKerja,
                Pegawai.UNIT_KERJA_ID
                == MfUnitKerja.UNIT_KERJA_ID
            )
            .filter(
                DinasLuar.TRANSAKSI.in_([
                    'DinasLuar',
                    'sakit',
                    'cuti',
                    'alpa',
                    'ijin',
                    'WFH',
                ]),
                DinasLuar.TGL_AWAL_DINAS_LUAR <= tgl_akhir,
                DinasLuar.TGL_AKHIR_DINAS_LUAR >= tgl_awal,
                db.func.upper(db.func.trim(db.func.coalesce(Pegawai.IS_KELUAR, ''))).in_(['N', '0']),
                db.func.upper(db.func.trim(db.func.coalesce(MfUnitKerja.IS_USE, ''))).in_(['Y', '1']),
            )
            .all()
        )

        # Legacy memilih transaksi khusus berdasarkan:
        # PriorityTransaksi ASC, UpdateDate DESC.
        # Reborn mempertahankan urutan tersebut bila master
        # MF_PRIORITY_TRANSAKSI tersedia.
        try:
            priority_rows = db.session.execute(
                text("""
                    SELECT Transaksi, PriorityTransaksi
                    FROM MFPriorityTransaksi
                    WHERE Modul = 'Absensi'
                """)
            ).mappings().all()

            priority_map = {
                str(row['Transaksi'] or '').strip().upper():
                    int(row['PriorityTransaksi'] or 99)
                for row in priority_rows
            }
        except Exception:
            priority_map = {}

        dinas_luar_rows.sort(
            key=lambda item: (
                priority_map.get(
                    str(item[0].TRANSAKSI or '').strip().upper(),
                    99,
                ),
                -(
                    item[0].UPDATE_DATE.timestamp()
                    if item[0].UPDATE_DATE
                    else 0
                ),
            )
        )

        def _dl_filter_match(pegawai):
            for field, value in (
                (filter_field1, filter_value1),
                (filter_field2, filter_value2),
            ):
                if not field or not value:
                    continue

                value_text = str(value).strip().lower()

                if field == 'NIP':
                    candidate = str(
                        pegawai.NIP or ''
                    ).strip().lower()
                elif field in ('Nama', 'NAMA'):
                    candidate = str(
                        pegawai.NAMA or ''
                    ).strip().lower()
                elif field == 'FingerID':
                    candidate = str(
                        pegawai.FINGER_ID or ''
                    ).strip().lower()
                elif field in ('UnitKerja', 'Unit Kerja'):
                    candidate = str(
                        pegawai.UNIT_KERJA or ''
                    ).strip().lower()
                elif field in ('Gol', 'Gol-Pangkat'):
                    candidate = str(
                        pegawai.GOL or ''
                    ).strip().lower()
                else:
                    continue

                if value_text not in candidate:
                    return False

            return True

        def _sprin_code(dl):
            """
            Kode attendance dari Jenis SPRIN.

            Dinas Luar Umum  -> DL
            Dinas Luar Operasi -> OP
            Dinas Luar Sumda -> SD

            Nilai yang sudah berupa kode legacy juga diterima.
            Nilai yang tidak dikenali TIDAK ditebak.
            """
            jenis = str(getattr(dl, 'JENIS', '') or '').strip()
            key = jenis.lower().replace('_', ' ').replace('-', ' ')

            code_map = {
                'dl': 'DL',
                'dinas luar': 'DL',
                'dinas luar umum': 'DL',
                'umum': 'DL',
                'op': 'OP',
                'operasi': 'OP',
                'dinas luar operasi': 'OP',
                'sd': 'SD',
                'sumda': 'SD',
                'dinas luar sumda': 'SD',
            }
            return code_map.get(key, jenis.upper())

        def _sprin_mark_row(row, dl, *, display_color, fingerprint_required):
            code = _sprin_code(dl)
            status_um = int(dl.STATUS_UM if dl.STATUS_UM is not None else 0)

            row['transaksi_in'] = 'DinasLuar'
            row['transaksi_out'] = 'DinasLuar'
            row['status_um'] = status_um
            row['dinas_luar'] = True
            row['sprin'] = True
            row['sprin_code'] = code
            row['attendance_code'] = code
            row['attendance_layer'] = 'SPRIN'
            row['sprin_display_color'] = display_color
            row['sprin_fingerprint_required'] = fingerprint_required
            row['sprin_tlm_psw_enabled'] = fingerprint_required
            row['dinas_luar_transaksi_id'] = str(dl.TRANSAKSI_ID or '').strip()
            row['dinas_luar_jenis'] = str(dl.JENIS or '').strip()
            row['dinas_luar_keterangan'] = str(dl.KETERANGAN_DINAS_LUAR or '').strip()
            row['dinas_luar_pendukung'] = str(dl.PENDUKUNG or '').strip()

            # StatusUM 0 = fingerprint wajib.
            # StatusUM 1/2 = fingerprint tidak diperlukan dan
            # final attendance memakai jam baku tanpa TLM/PSW.
            if not fingerprint_required:
                row['jam_in'] = row.get('jam_baku_in') or ''
                row['jam_out'] = row.get('jam_baku_out') or ''
                row['awal_tlm'] = 0
                row['total_tlm'] = 0
                row['total_psw'] = 0
                row['tingkat_tlm'] = code
                row['tingkat_psw'] = code
                row['persen_pot_tlm'] = 0
                row['persen_pot_psw'] = 0
                row['is_valid_in'] = True
                row['is_valid_out'] = True

            return row

        def _dl_mark_existing_row(row, dl):
            # StatusUM=0: wajib fingerprint.
            # Fingerprint tetap menjadi sumber jam aktual/TLM/PSW,
            # tetapi SPRIN menjadi layer transaksi paling atas.
            return _sprin_mark_row(
                row,
                dl,
                display_color='dark-blue',
                fingerprint_required=True,
            )

        # ============================================================
        # WFH ONLINE — HRIS REBORN ADDITION
        #
        # HRIS 2013 has WFH as a special transaction, but it does not
        # have the WEB attendance punch introduced by HRIS Reborn.
        #
        # WEB IN/OUT is an actual attendance source. It must:
        #   - not be paired as ordinary fingerprint,
        #   - retain the actual clock-in/clock-out,
        #   - become TRANSAKSI_IN/OUT = WFH,
        #   - not generate TLM/PSW,
        #   - win over the generic DinasLuar WFH row for the same
        #     employee/date.
        # ============================================================

        wfh_online_grouped = defaultdict(list)

        for raw in raw_rows:
            if str(raw.get('DEVICE_IP') or '').strip().upper() != 'WEB':
                continue

            waktu = raw.get('WAKTU')
            if not waktu:
                continue

            work_date = waktu.date()
            if work_date < tgl_awal.date() or work_date > tgl_akhir.date():
                continue

            finger_key = str(
                raw.get('PEGAWAI_FINGER_ID')
                or raw.get('FINGER_ID')
                or ''
            ).strip()

            if not finger_key:
                continue

            status = str(raw.get('STATUS') or '').strip().upper()
            punch = raw.get('PUNCH')

            if punch == 0:
                status = 'IN'
            elif punch == 1:
                status = 'OUT'

            if status not in ('IN', 'OUT'):
                continue

            wfh_online_grouped[
                (finger_key, work_date.strftime('%Y-%m-%d'))
            ].append(raw)

        # Transaksi khusus dipilih sekali per pegawai/tanggal.
        # Urutan sudah ditentukan oleh MFPriorityTransaksi ASC,
        # lalu UpdateDate DESC.
        special_claimed = set()

        for (wfh_finger, wfh_date_str), web_logs in wfh_online_grouped.items():
            web_logs.sort(
                key=lambda item: item.get('WAKTU') or datetime.min
            )

            in_logs = [
                item for item in web_logs
                if (
                    (
                        item.get('PUNCH') == 0
                    )
                    or str(item.get('STATUS') or '').strip().upper() == 'IN'
                )
            ]
            out_logs = [
                item for item in web_logs
                if (
                    (
                        item.get('PUNCH') == 1
                    )
                    or str(item.get('STATUS') or '').strip().upper() == 'OUT'
                )
            ]

            jam_wfh_in = in_logs[0]['WAKTU'] if in_logs else None
            jam_wfh_out = out_logs[-1]['WAKTU'] if out_logs else None

            meta = web_logs[0]
            nip_wfh = str(meta.get('NIP') or '').strip()

            if not nip_wfh:
                continue

            tgl_wfh = datetime.strptime(
                wfh_date_str,
                '%Y-%m-%d'
            ).date()

            # WEB WFH is always regular workday attendance in the online
            # attendance flow. Calendar still determines the displayed
            # holiday flag, but it does not create TLM/PSW for WFH.
            is_libur_wfh = (
                kalender_map.get(
                    wfh_date_str,
                    'N'
                ) == 'Y'
            )

            row_wfh = normalization_engine.normalize_row(
                nip=nip_wfh,
                finger_id=wfh_finger,
                nama=meta.get('NAMA') or '',
                gol=meta.get('GOL') or '',
                unit_kerja=meta.get('UNIT_KERJA') or '',
                tgl_kerja=tgl_wfh,
                jam_in=jam_wfh_in,
                jam_out=jam_wfh_out,
                shift_kerja='1',
                is_libur=is_libur_wfh,
            )

            if not row_wfh:
                continue

            # Actual WEB attendance is final for this date.
            result[:] = [
                row
                for row in result
                if not (
                    str(row.get('finger_id') or '').strip() == wfh_finger
                    and str(row.get('tgl_kerja') or '').strip() == wfh_date_str
                )
            ]

            row_wfh['no'] = 0
            row_wfh['shift'] = '1'
            row_wfh['shift2_siaga'] = False
            row_wfh['transaksi_in'] = 'WFH'
            row_wfh['transaksi_out'] = 'WFH'
            row_wfh['wfh_online'] = True
            row_wfh['attendance_code'] = 'WFH'
            row_wfh['attendance_layer'] = 'WFH_ONLINE'
            row_wfh['status_um'] = None
            row_wfh['dinas_luar_transaksi_id'] = ''
            row_wfh['dinas_luar_jenis'] = 'WFH'
            row_wfh['dinas_luar_keterangan'] = 'ABSEN ONLINE WFH'
            row_wfh['dinas_luar_pendukung'] = '998'

            # WFH Online must not produce TLM/PSW deductions.
            row_wfh['awal_tlm'] = 0
            row_wfh['total_tlm'] = 0
            row_wfh['persen_pot_tlm'] = 0
            row_wfh['tingkat_tlm'] = ''
            row_wfh['total_psw'] = 0
            row_wfh['persen_pot_psw'] = 0
            row_wfh['tingkat_psw'] = ''
            row_wfh['is_valid_in'] = bool(jam_wfh_in)
            row_wfh['is_valid_out'] = bool(jam_wfh_out)

            result.append(row_wfh)
            special_claimed.add((nip_wfh, wfh_date_str))

        for dl, pegawai_dl in dinas_luar_rows:

            if not _dl_filter_match(pegawai_dl):
                continue

            finger_id_dl = str(
                pegawai_dl.FINGER_ID or ''
            ).strip()

            if not finger_id_dl:
                continue

            nip_dl = str(
                pegawai_dl.NIP or ''
            ).strip()

            if not nip_dl:
                continue

            status_um_dl = int(
                dl.STATUS_UM
                if dl.STATUS_UM is not None
                else 0
            )

            # ========================================================
            # STATUSUM 0
            #
            # "tidak memotong uang makan"
            # - fingerprint WAJIB
            # - actual IN/OUT dipertahankan
            # - TLM/PSW tetap berlaku
            # - SPRIN menjadi layer di atas Siaga/reguler
            # - recap menggunakan kode DL/OP/SD
            # ========================================================
            # StatusUM=0 hanya berarti fingerprint wajib untuk
            # Dinas Luar. Cuti/Sakit/Ijin/Alpa/WFH adalah transaksi
            # khusus yang tetap membentuk ABSENSI final per tanggal.
            transaksi_key_dl = str(
                dl.TRANSAKSI or ''
            ).strip().lower()

            if (
                status_um_dl == 0
                and transaksi_key_dl == 'dinasluar'
            ):

                for row in result:
                    row_finger = str(row.get('finger_id') or '').strip()
                    row_date = str(row.get('tgl_kerja') or '').strip()

                    claim_key = (
                        nip_dl,
                        row_date,
                    )

                    if claim_key in special_claimed:
                        continue

                    if (
                        row_finger == finger_id_dl
                        and row_date >= dl.TGL_AWAL_DINAS_LUAR.strftime('%Y-%m-%d')
                        and row_date <= dl.TGL_AKHIR_DINAS_LUAR.strftime('%Y-%m-%d')
                    ):
                        _dl_mark_existing_row(row, dl)
                        special_claimed.add(claim_key)

                continue

            # ========================================================
            # STATUSUM 1 / 2
            #
            # Tidak wajib fingerprint.
            #
            # DL harus dibuat untuk SETIAP tanggal dalam periode,
            # termasuk hari libur.
            #
            # Hasil fingerprint reguler pada tanggal yang sama
            # tidak boleh menang.
            # ========================================================

            dl_start = max(
                dl.TGL_AWAL_DINAS_LUAR.date(),
                tgl_awal.date()
            )

            dl_end = min(
                dl.TGL_AKHIR_DINAS_LUAR.date(),
                tgl_akhir.date()
            )

            if dl_start > dl_end:
                continue

            current_date = dl_start

            while current_date <= dl_end:

                tgl_str_dl = current_date.strftime(
                    '%Y-%m-%d'
                )

                claim_key = (
                    nip_dl,
                    tgl_str_dl,
                )

                # PriorityTransaksi: transaksi yang lebih tinggi
                # sudah memiliki hak atas tanggal ini.
                if claim_key in special_claimed:
                    current_date += timedelta(days=1)
                    continue

                # Hapus hasil fingerprint reguler
                # pada tanggal yang sedang ditangani.
                result[:] = [
                    row
                    for row in result
                    if not (
                        str(
                            row.get('finger_id') or ''
                        ).strip()
                        == finger_id_dl
                        and str(
                            row.get('tgl_kerja') or ''
                        ).strip()
                        == tgl_str_dl
                    )
                ]

                is_libur_dl = (
                    kalender_map.get(
                        tgl_str_dl,
                        'N'
                    ) == 'Y'
                )

                jam_baku_in_dl = ''
                jam_baku_out_dl = ''

                row_dl = {
                    'no': 0,
                    'finger_id': finger_id_dl,
                    'nip': nip_dl,
                    'nama': str(
                        pegawai_dl.NAMA or ''
                    ),
                    'gol': str(
                        pegawai_dl.GOL or ''
                    ),
                    'unit_kerja': str(
                        pegawai_dl.UNIT_KERJA or ''
                    ),
                    'tgl_kerja': tgl_str_dl,
                    'hari': current_date.strftime('%A'),
                    'jam_baku_in': jam_baku_in_dl,
                    'jam_baku_out': jam_baku_out_dl,
                    'jam_in': '',
                    'jam_out': '',
                    'awal_tlm': 0,
                    'total_tlm': 0,
                    'total_psw': 0,
                    'tingkat_tlm': '',
                    'tingkat_psw': '',
                    'persen_pot_tlm': 0,
                    'persen_pot_psw': 0,
                    'is_valid_in': True,
                    'is_valid_out': True,
                    'is_libur': is_libur_dl,
                    'shift': '1',
                    'shift_kerja': '1',
                    'shift2_siaga': False,
                    'transaksi_in': 'DinasLuar',
                    'transaksi_out': 'DinasLuar',
                    'status_um': status_um_dl,
                    'dinas_luar': True,
                    'dinas_luar_transaksi_id': (
                        str(
                            dl.TRANSAKSI_ID or ''
                        ).strip()
                    ),
                    'dinas_luar_jenis': str(
                        dl.JENIS or ''
                    ).strip(),
                    'dinas_luar_keterangan': str(
                        dl.KETERANGAN_DINAS_LUAR
                        or ''
                    ).strip(),
                    'dinas_luar_pendukung': str(
                        dl.PENDUKUNG or ''
                    ).strip(),
                }

                # ------------------------------------------------
                # SPRIN StatusUM 1 / 2 tidak membutuhkan fingerprint.
                # StatusUM=1 = memotong uang makan -> ORANGE.
                # StatusUM=2 = tidak memotong uang makan penempatan
                #                -> DARK BLUE.
                # Keduanya memakai jam baku dan tidak menghasilkan
                # TLM/PSW.
                # ------------------------------------------------
                display_color = (
                    'orange'
                    if status_um_dl == 1
                    else 'dark-blue'
                )

                # ------------------------------------------------
                # Bentuk hasil transaksi khusus mengikuti ABSENSI
                # legacy: jam baku sebagai TglJamIn/TglJamOut,
                # tidak dihitung sebagai TLM/PSW.
                # ------------------------------------------------
                jk_special = normalization_engine.resolve_jam_kerja(
                    current_date,
                    '1',
                )
                baku_special_in, baku_special_out = (
                    normalization_engine.resolve_jam_baku(
                        current_date,
                        jk_special,
                    )
                )

                transaksi_special = str(
                    dl.TRANSAKSI or ''
                ).strip()
                transaksi_key = transaksi_special.lower()

                special_percent = 0
                special_tingkat = ''

                if transaksi_key == 'alpa':
                    kandidat = [
                        pot for pot in special_potongan_list
                        if str(pot.KATEGORI or '').strip().lower() == 'ijin'
                        and (
                            not pot.TGL_MULAI
                            or pot.TGL_MULAI.date() <= current_date
                        )
                    ]
                    kandidat.sort(
                        key=lambda pot: pot.TGL_MULAI or datetime.min,
                        reverse=True,
                    )
                    if kandidat:
                        special_percent = kandidat[0].PERSEN_POT or 0
                    special_tingkat = 'I'

                elif transaksi_key in ('sakit', 'cuti'):
                    target_tingkat = str(
                        dl.PENEMPATAN_DINAS_LUAR or ''
                    ).strip()
                    kandidat = [
                        pot for pot in special_potongan_list
                        if str(pot.KATEGORI or '').strip().lower() == transaksi_key
                        and str(pot.TINGKAT or '').strip() == target_tingkat
                        and (
                            not pot.TGL_MULAI
                            or pot.TGL_MULAI.date() <= current_date
                        )
                    ]
                    kandidat.sort(
                        key=lambda pot: pot.TGL_MULAI or datetime.min,
                        reverse=True,
                    )
                    if kandidat:
                        special_percent = kandidat[0].PERSEN_POT or 0
                    special_tingkat = target_tingkat

                row_dl['jam_baku_in'] = (
                    baku_special_in.strftime('%H:%M')
                    if baku_special_in else ''
                )
                row_dl['jam_baku_out'] = (
                    baku_special_out.strftime('%H:%M')
                    if baku_special_out else ''
                )
                row_dl['jam_in'] = row_dl['jam_baku_in']
                row_dl['jam_out'] = row_dl['jam_baku_out']

                _sprin_mark_row(
                    row_dl,
                    dl,
                    display_color=display_color,
                    fingerprint_required=False,
                )

                row_dl['tingkat_tlm'] = (
                    _sprin_code(dl)
                    if transaksi_key == 'dinasluar'
                    else special_tingkat
                )
                row_dl['tingkat_psw'] = (
                    _sprin_code(dl)
                    if transaksi_key == 'dinasluar'
                    else special_tingkat
                )
                row_dl['persen_pot_tlm'] = special_percent
                row_dl['persen_pot_psw'] = 0
                row_dl['is_valid_in'] = True
                row_dl['is_valid_out'] = True
                row_dl['transaksi_in'] = transaksi_special
                row_dl['transaksi_out'] = transaksi_special
                row_dl['sprin'] = True
                row_dl['sprin_code'] = _sprin_code(dl)
                row_dl['attendance_code'] = _sprin_code(dl)
                row_dl['attendance_layer'] = 'SPRIN'
                row_dl['sprin_display_color'] = display_color
                row_dl['sprin_fingerprint_required'] = False
                row_dl['sprin_tlm_psw_enabled'] = False
                row_dl['status_um'] = status_um_dl
                row_dl['awal_tlm'] = 0
                row_dl['total_tlm'] = 0
                row_dl['total_psw'] = 0
                row_dl['persen_pot_tlm'] = 0
                row_dl['persen_pot_psw'] = 0

                result.append(row_dl)
                special_claimed.add(claim_key)

                current_date += timedelta(days=1)

        # VIP CORRECTION
        #
        # Pegawai.IsVIP adalah rule legacy.
        # VIP tidak membuat row baru bila IN dan OUT sama-sama kosong.
        # Jika salah satu sisi tersedia, sisi yang hilang / tidak sesuai
        # dikoreksi dengan rule VIP legacy.
        # ============================================================

        vip_sequence = 0

        for row in result:
            if str(row.get('transaksi_in') or '').strip().upper() not in ('', 'LOGFP', 'MANUAL'):
                continue

            nip_row = str(row.get('nip') or '').strip()
            if not nip_row:
                continue

            is_vip_row = False

            # Utamakan identitas dari RAW/TIME_RECORDER.
            for raw in raw_rows:
                if str(raw.get('NIP') or '').strip() == nip_row:
                    is_vip_row = (
                        str(raw.get('IS_VIP') or '').strip().upper()
                        in ('Y', '1', 'YES', 'TRUE')
                    )
                    if is_vip_row:
                        break

            if not is_vip_row:
                peg_vip = (
                    Pegawai.query
                    .filter(Pegawai.NIP == nip_row)
                    .first()
                )
                is_vip_row = bool(
                    peg_vip
                    and str(peg_vip.IS_VIP or '').strip().upper()
                    in ('Y', '1', 'YES', 'TRUE')
                )

            if not is_vip_row:
                continue

            jam_in_value = str(row.get('jam_in') or '').strip()
            jam_out_value = str(row.get('jam_out') or '').strip()

            # 00:00:00 adalah sentinel "tidak ada fingerprint".
            has_in = bool(jam_in_value and jam_in_value != '00:00:00')
            has_out = bool(jam_out_value and jam_out_value != '00:00:00')

            if not has_in and not has_out:
                continue

            activity_date_vip = str(
                row.get('activity_date_siaga') or ''
            ).strip()

            tgl_kerja_vip = datetime.strptime(
                str(row.get('tgl_kerja')),
                '%Y-%m-%d'
            ).date()

            if activity_date_vip:
                tgl_baku_in_vip = datetime.strptime(
                    f'{activity_date_vip} {row.get("jam_baku_in")}',
                    '%Y-%m-%d %H:%M'
                ) if row.get('jam_baku_in') else None
                tgl_baku_out_vip = datetime.strptime(
                    f'{row.get("tgl_kerja")} {row.get("jam_baku_out")}',
                    '%Y-%m-%d %H:%M'
                ) if row.get('jam_baku_out') else None
                tgl_actual_in_vip = datetime.strptime(
                    f'{activity_date_vip} {jam_in_value}',
                    '%Y-%m-%d %H:%M:%S'
                ) if has_in else None
                tgl_actual_out_vip = datetime.strptime(
                    f'{row.get("tgl_kerja")} {jam_out_value}',
                    '%Y-%m-%d %H:%M:%S'
                ) if has_out else None
            else:
                tgl_baku_in_vip = datetime.strptime(
                    f'{row.get("tgl_kerja")} {row.get("jam_baku_in")}',
                    '%Y-%m-%d %H:%M'
                ) if row.get('jam_baku_in') else None
                tgl_baku_out_vip = datetime.strptime(
                    f'{row.get("tgl_kerja")} {row.get("jam_baku_out")}',
                    '%Y-%m-%d %H:%M'
                ) if row.get('jam_baku_out') else None
                tgl_actual_in_vip = datetime.strptime(
                    f'{row.get("tgl_kerja")} {jam_in_value}',
                    '%Y-%m-%d %H:%M:%S'
                ) if has_in else None
                tgl_actual_out_vip = datetime.strptime(
                    f'{row.get("tgl_kerja")} {jam_out_value}',
                    '%Y-%m-%d %H:%M:%S'
                ) if has_out else None

            vip_sequence += 1

            new_in, new_out, changed = (
                normalization_engine.apply_vip_correction(
                    is_vip=True,
                    sequence_no=vip_sequence,
                    nama=row.get('nama') or '',
                    tgl_kerja=tgl_kerja_vip,
                    baku_in=tgl_baku_in_vip,
                    baku_out=tgl_baku_out_vip,
                    jam_in=tgl_actual_in_vip,
                    jam_out=tgl_actual_out_vip,
                )
            )

            if changed:
                row['jam_in'] = (
                    new_in.strftime('%H:%M:%S')
                    if new_in else '00:00:00'
                )
                row['jam_out'] = (
                    new_out.strftime('%H:%M:%S')
                    if new_out else '00:00:00'
                )
                row['is_valid_in'] = bool(new_in)
                row['is_valid_out'] = bool(new_out)
                row['vip'] = True
                row['vip_correction'] = True

        # ============================================================
        # ============================================================
        # URUTAN HASIL NORMALISASI
        #
        # Semua layer normalisasi (Shift 1, Shift 2, DL, WFH, dst.)
        # harus berada dalam SATU urutan kronologis.
        #
        # Sebelumnya sorting menggunakan:
        #   Unit -> FingerID -> Tanggal
        #
        # Hal tersebut membuat row yang berasal dari layer berbeda
        # dapat terpecah walaupun pegawai dan tanggalnya sama/berurutan
        # (contoh Shift 2 dan Shift 1/DL).
        #
        # Gunakan NIP sebagai identitas pegawai utama, lalu tanggal
        # kerja sebagai urutan utama di dalam kelompok pegawai.
        # Shift hanya menjadi tie-breaker.
        # ============================================================

        def _normalisasi_sort_key(r):
            nip = str(
                r.get('nip') or ''
            ).strip()

            nama = str(
                r.get('nama') or ''
            ).strip().upper()

            tgl_kerja = str(
                r.get('tgl_kerja') or ''
            ).strip()

            # ISO YYYY-MM-DD aman untuk sorting kronologis.
            # Jika kosong, letakkan di paling belakang.
            tanggal_sort = (
                tgl_kerja
                if len(tgl_kerja) == 10
                else '9999-12-31'
            )

            shift = str(
                r.get('shift_kerja')
                or r.get('shift')
                or '1'
            ).strip()

            return (
                nip,
                nama,
                tanggal_sort,
                shift,
                str(r.get('finger_id') or '').strip(),
            )

        result.sort(key=_normalisasi_sort_key)

        # Nomor ditetapkan SETELAH sorting final agar nomor pada
        # preview normalisasi dan hasil export selalu mengikuti
        # urutan tanggal yang sama.
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


def api_normalisasi_legacy_test():
    """
    EXPERIMENT - Legacy Compatibility Test.

    Tujuan:
        Menjalankan NORMALISASI EXISTING tanpa melakukan EXPORT
        ke tabel ABSENSI.

    Endpoint ini hanya mengambil hasil dari:
        api_normalisasi_process()

    lalu memfilter hasil berdasarkan NIP jika diberikan.

    Tidak:
        - INSERT ABSENSI
        - UPDATE ABSENSI
        - DELETE RAW
        - mengubah TIME_RECORDER
    """
    try:
        data = request.get_json(silent=True) or {}

        nip_test = str(
            data.get('nip') or ''
        ).strip()

        if not nip_test:
            return jsonify({
                'error': 'Parameter nip wajib diisi untuk Legacy Test.'
            }), 400

        # Jalankan NORMALISASI EXISTING menggunakan payload yang sama.
        # Kita tidak membuat engine/service baru di sini.
        response = api_normalisasi_process()

        # Flask jsonify() menghasilkan Response.
        response_data = response.get_json()

        if not response_data:
            return jsonify({
                'error': 'Response normalisasi kosong.'
            }), 500

        if not response_data.get('success'):
            return jsonify(response_data), response.status_code

        rows = response_data.get('data') or []

        matched = [
            row
            for row in rows
            if str(row.get('nip') or '').strip() == nip_test
        ]

        return jsonify({
            'success': True,
            'mode': 'legacy-test',
            'nip': nip_test,
            'total_normalisasi': len(rows),
            'total_match': len(matched),
            'data': matched,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e)
        }), 500


def api_normalisasi_export():
    """
    TAB 2 - tombol EXPORT.

    Simpan hasil normalisasi ke tabel ABSENSI
    dengan mekanisme INSERT / UPDATE.

    Hanya hasil normalisasi yang memiliki identitas
    pegawai/FingerID yang valid yang boleh masuk ke ABSENSI.
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

        if not tgl_awal_export or not tgl_akhir_export:
            return jsonify({
                'error': 'Periode export kosong.'
            })

        # --------------------------------------------------------
        # EXPORT SERVER-SIDE
        #
        # Browser TIDAK lagi mengirim seluruh hasil normalisasi.
        #
        # Sebelumnya:
        #   rows = normalisasiRows
        #
        # Hal tersebut menyebabkan request sangat besar dan
        # menghasilkan HTTP 413 Request Entity Too Large.
        #
        # Sekarang EXPORT menggunakan business pipeline yang sama
        # dengan tombol NORMALISASI.
        #
        # api_normalisasi_process() membaca:
        #   - periode
        #   - default TLM/PSW
        #   - filter
        #   - FINGER_HARVEST_RAW
        #   - LOG_ACTIVITIY
        #   - jam kerja
        #   - kalender
        #
        # sehingga tidak ada duplikasi logic normalisasi.
        # --------------------------------------------------------

        normalisasi_response = api_normalisasi_process()

        if isinstance(normalisasi_response, tuple):
            normalisasi_response = normalisasi_response[0]

        normalisasi_data = (
            normalisasi_response.get_json(
                silent=True
            )
            if normalisasi_response
            else None
        )

        if not normalisasi_data:
            return jsonify({
                'error': (
                    'Gagal memperoleh hasil normalisasi '
                    'dari server.'
                )
            })

        if normalisasi_data.get('error'):
            return jsonify({
                'error': normalisasi_data.get('error')
            })

        rows = normalisasi_data.get('data') or []

        if not isinstance(rows, list) or not rows:
            return jsonify({
                'error': (
                    'Tidak ada hasil normalisasi untuk diekspor.'
                )
            })

        if not normalisasi_data:
            return jsonify({
                'error': 'Gagal memperoleh hasil normalisasi.'
            })

        if normalisasi_data.get('error'):
            return jsonify({
                'error': normalisasi_data.get('error')
            })

        rows = normalisasi_data.get('data') or []

        if not isinstance(rows, list) or not rows:
            return jsonify({
                'error': (
                    'Tidak ada hasil normalisasi untuk diekspor. '
                    'Silakan lakukan NORMALISASI terlebih dahulu.'
                )
            })

        saved = 0
        skipped = 0
        exported_rows = []

        # --------------------------------------------------------
        # SAFETY GUARD: satu FingerID + TglKerja = satu ABSENSI.
        #
        # Normalisasi seharusnya sudah mencegah duplikasi ini.
        # Guard tetap dipasang di EXPORT agar row reguler yang salah
        # tidak pernah menimpa row Shift 2 pada database legacy.
        #
        # Jika terjadi duplikasi, Shift 2 selalu menjadi pemenang
        # karena merupakan transaksi lintas tengah malam yang memang
        # memiliki TglKerja H+1.
        # --------------------------------------------------------
        rows_by_absensi_key = {}

        for candidate in rows:
            candidate_key = (
                str(candidate.get('finger_id') or '').strip(),
                str(candidate.get('tgl_kerja') or '').strip(),
            )

            previous = rows_by_absensi_key.get(candidate_key)

            if previous is None:
                rows_by_absensi_key[candidate_key] = candidate
                continue

            candidate_shift2 = bool(
                candidate.get('shift2_siaga')
            )
            previous_shift2 = bool(
                previous.get('shift2_siaga')
            )

            if candidate_shift2 and not previous_shift2:
                rows_by_absensi_key[candidate_key] = candidate

        rows = list(rows_by_absensi_key.values())

        rows.sort(
            key=lambda row: (
                str(row.get('nip') or '').strip(),
                str(row.get('tgl_kerja') or '').strip(),
                str(
                    row.get('shift_kerja')
                    or row.get('shift')
                    or '1'
                ).strip(),
            )
        )

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

            # --------------------------------------------------------
            # Tanggal timestamp aktual.
            #
            # Normal:
            #   IN  = tanggal kerja
            #   OUT = tanggal kerja
            #
            # Shift 2:
            #   IN  = ActivityDate / H
            #   OUT = TglKerja / H+1
            #
            # Hasil normalisasi menyimpan activity_date_siaga
            # untuk membedakan tanggal mulai siaga.
            # --------------------------------------------------------

            activity_date_str = str(
                r.get('activity_date_siaga') or ''
            ).strip()

            is_shift2 = (
                str(r.get('shift_kerja') or '') == '2'
                or str(r.get('shift') or '') == '2'
                or bool(r.get('shift2_siaga'))
            )

            if is_shift2 and activity_date_str:
                tanggal_in = activity_date_str
            else:
                tanggal_in = tgl_kerja_str

            tanggal_out = tgl_kerja_str

            def _parse_export_datetime(date_text, time_text):
                time_value = str(time_text or '').strip()

                if not time_value:
                    return None

                for time_format in ('%H:%M:%S', '%H:%M'):
                    try:
                        return datetime.strptime(
                            f"{date_text} {time_value}",
                            f'%Y-%m-%d {time_format}'
                        )
                    except ValueError:
                        continue

                raise ValueError(
                    f"time data '{date_text} {time_value}' "
                    "does not match format '%Y-%m-%d %H:%M[:%S]'"
                )

            tgl_jam_in = _parse_export_datetime(
                tanggal_in,
                jam_in,
            )

            tgl_jam_out = _parse_export_datetime(
                tanggal_out,
                jam_out,
            )

            # --------------------------------------------------------
            # Jam baku.
            #
            # Shift 2:
            #   Baku IN  = H
            #   Baku OUT = H+1
            # --------------------------------------------------------

            if is_shift2 and activity_date_str:
                tanggal_baku_in = activity_date_str
                tanggal_baku_out = tgl_kerja_str
            else:
                tanggal_baku_in = tgl_kerja_str
                tanggal_baku_out = tgl_kerja_str

            jam_baku_in = str(
                r.get('jam_baku_in') or ''
            ).strip()

            jam_baku_out = str(
                r.get('jam_baku_out') or ''
            ).strip()

            tgl_jam_baku_in = (
                datetime.strptime(
                    f"{tanggal_baku_in} {jam_baku_in}",
                    '%Y-%m-%d %H:%M'
                )
                if jam_baku_in
                else None
            )

            tgl_jam_baku_out = (
                datetime.strptime(
                    f"{tanggal_baku_out} {jam_baku_out}",
                    '%Y-%m-%d %H:%M'
                )
                if jam_baku_out
                else None
            )

            # --------------------------------------------------------
            # Transaksi final mengikuti hasil NORMALISASI.
            #
            # HRIS 2013 tidak mengubah Cuti/Sakit/Alpa/DinasLuar/WFH
            # menjadi LogFP saat EXPORT.
            # --------------------------------------------------------
            transaksi_in = str(
                r.get('transaksi_in') or 'LogFP'
            ).strip() or 'LogFP'
            transaksi_out = str(
                r.get('transaksi_out') or transaksi_in
            ).strip() or transaksi_in

            special_transactions = {
                'DINASLUAR',
                'CUTI',
                'SAKIT',
                'ALPA',
                'IJIN',
                'WFH',
            }

            is_special = (
                transaksi_in.upper()
                in special_transactions
            )
            wfh_online = bool(r.get('wfh_online'))

            if is_special and not wfh_online:
                # Untuk transaksi khusus legacy, simpan jam baku.
                # Pengecualian: WFH Online HRIS Reborn harus mempertahankan
                # jam aktual dari WEB IN/OUT.
                tgl_jam_in = tgl_jam_baku_in
                tgl_jam_out = tgl_jam_baku_out

            ket_special = str(
                r.get('dinas_luar_keterangan')
                or r.get('dinas_luar_jenis')
                or transaksi_in
            ).strip()

            # Metadata tampilan Rekap dipersist bersama ABSENSI final.
            #
            # HRIS 2013 mengambil:
            #   - DL/OP/SD dari DINAS_LUAR.Jenis
            #   - CT/S-1 dari DINAS_LUAR.PenempatanDinasLuar
            #
            # Reborn tidak perlu membaca DINAS_LUAR lagi saat Rekap.
            # HISTORY_TRANSAKSI_IN/OUT dipakai sebagai carrier metadata
            # display final yang sebelumnya hilang saat EXPORT.
            if (
                bool(r.get('shift2_siaga'))
                or bool(r.get('siaga'))
            ):
                rekap_display_code = 'SIAGA'
            elif transaksi_in.upper() == 'DINASLUAR':
                rekap_display_code = str(
                    r.get('sprin_code')
                    or r.get('dinas_luar_jenis')
                    or ''
                ).strip().upper()
            elif transaksi_in.upper() in ('CUTI', 'SAKIT'):
                rekap_display_code = str(
                    r.get('tingkat_tlm')
                    or r.get('tingkat_psw')
                    or ''
                ).strip().upper()
            elif transaksi_in.upper() == 'ALPA':
                rekap_display_code = 'A'
            elif transaksi_in.upper() in ('IJIN', 'IZIN'):
                rekap_display_code = 'I'
            elif transaksi_in.upper() == 'WFH':
                rekap_display_code = 'WFH'
            else:
                rekap_display_code = ''

            update_by = (
                str(
                    session.get('nip')
                    or session.get('username')
                    or 'system'
                ).strip()
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
                existing.TRANSAKSI_IN = transaksi_in
                existing.TRANSAKSI_OUT = transaksi_out
                existing.KET_IN = (
                    ket_special if is_special else 'LogFP'
                )
                existing.KET_OUT = (
                    ket_special if is_special else 'LogFP'
                )
                existing.UPDATE_IN_BY = update_by
                existing.UPDATE_OUT_BY = update_by
                existing.TRANSAKSI_ID_FROM = (
                    r.get('dinas_luar_transaksi_id')
                    if is_special
                    else None
                )
                existing.PENDUKUNG_IN = (
                    r.get('dinas_luar_pendukung')
                    if is_special
                    else 'N'
                )
                existing.PENDUKUNG_OUT = (
                    r.get('dinas_luar_pendukung')
                    if is_special
                    else 'N'
                )
                existing.STATUS_UM = (
                    r.get('status_um')
                    if is_special
                    else None
                )
                existing.HISTORY_TRANSAKSI_IN = (
                    rekap_display_code
                    or None
                )
                existing.HISTORY_TRANSAKSI_OUT = (
                    rekap_display_code
                    or None
                )
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
                    TRANSAKSI_IN=transaksi_in,
                    TRANSAKSI_OUT=transaksi_out,
                    KET_IN=(
                        ket_special if is_special else 'LogFP'
                    ),
                    KET_OUT=(
                        ket_special if is_special else 'LogFP'
                    ),
                    UPDATE_IN_BY=update_by,
                    UPDATE_OUT_BY=update_by,
                    TRANSAKSI_ID_FROM=(
                        r.get('dinas_luar_transaksi_id')
                        if is_special
                        else None
                    ),
                    PENDUKUNG_IN=(
                        r.get('dinas_luar_pendukung')
                        if is_special
                        else 'N'
                    ),
                    PENDUKUNG_OUT=(
                        r.get('dinas_luar_pendukung')
                        if is_special
                        else 'N'
                    ),
                    STATUS_UM=(
                        r.get('status_um')
                        if is_special
                        else None
                    ),
                    HISTORY_TRANSAKSI_IN=(
                        rekap_display_code
                        or None
                    ),
                    HISTORY_TRANSAKSI_OUT=(
                        rekap_display_code
                        or None
                    ),
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
            # Metadata presentation dari ABSENSI final.
            #
            # KET dan Awal PSW dihitung dari row ABSENSI yang baru
            # saja. Tidak ada normalisasi ulang di tahap presentation.
            # --------------------------------------------------------
            final_absensi = existing if existing else absensi
            ket, ket_class = _absensi_ket_metadata(
                final_absensi,
                None,
                r.get('nip'),
                _load_master_potongan_meal_cut_codes(),
            )

            ket_color = (
                REPORT_COLORS.get(ket_class, '')
                if ket_class != 'normal'
                else ''
            )

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
                'awal_psw': _absensi_awal_psw(final_absensi),
                'total_psw': r.get('total_psw'),
                'tingkat_psw': r.get('tingkat_psw'),
                'persen_pot_psw': r.get('persen_pot_psw'),
                'ket': ket,
                'ket_class': ket_class,
                'ket_color': ket_color,
                'transaksi_in': transaksi_in,
                'transaksi_out': transaksi_out,
                # Simpan key sorting internal agar response export
                # mengikuti urutan yang sama dengan preview normalisasi.
                '_sort_nip': str(r.get('nip') or '').strip(),
                '_sort_tgl': tgl_kerja.strftime('%Y-%m-%d') if tgl_kerja else '9999-12-31',
                '_sort_shift': str(
                    r.get('shift_kerja')
                    or r.get('shift')
                    or '1'
                ).strip(),
            })

        if exported_rows:
            export_dates = [
                row.get('_sort_tgl')
                for row in exported_rows
                if row.get('_sort_tgl')
            ]
            if export_dates:
                export_start = datetime.strptime(
                    min(export_dates),
                    '%Y-%m-%d'
                )
                export_end = datetime.strptime(
                    max(export_dates),
                    '%Y-%m-%d'
                )
                export_siaga_map = _load_siaga_ket_map(
                    export_start,
                    export_end,
                )
                for row in exported_rows:
                    row_nip = str(row.get('_sort_nip') or '').strip()
                    row_date = row.get('_sort_tgl')
                    if row_nip and row_date:
                        siaga_code = export_siaga_map.get(
                            (row_nip, datetime.strptime(
                                row_date, '%Y-%m-%d'
                            ).date())
                        )
                        if siaga_code:
                            row['ket'] = siaga_code
                            row['ket_class'] = 'siaga'
                            row['ket_color'] = REPORT_COLORS['siaga']

        exported_rows.sort(
            key=lambda row: (
                row.get('_sort_nip') or '999999999999999999',
                row.get('_sort_tgl') or '9999-12-31',
                row.get('_sort_shift') or '1',
                str(row.get('finger_id') or '').strip(),
            )
        )

        for i, row in enumerate(exported_rows, 1):
            row['no'] = i
            row.pop('_sort_nip', None)
            row.pop('_sort_tgl', None)
            row.pop('_sort_shift', None)

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


def _load_siaga_ket_map(tgl_awal, tgl_akhir):
    """
    Ambil hasil kehadiran Piket Siaga dari LOG_ACTIVITIY.

    Source HRIS 2013:
      - StatusID = 3 berarti pegawai sudah HADIR/diabsen petugas.
      - shift1 = 1  -> KET = 'shift1' pada tanggal ActivityDate.
      - shift2 = 1  -> KET = 'shift2' pada tanggal ActivityDate + 1 hari.

    Hanya flag kehadiran petugas yang dipakai. Fingerprint tidak
    dipasangkan ulang di layer presentation.
    """
    if not tgl_awal or not tgl_akhir:
        return {}

    source_awal = tgl_awal - timedelta(days=1)
    source_akhir = tgl_akhir

    rows = (
        db.session.query(
            LogActivity.NIP,
            LogActivity.ACTIVITY_DATE,
            LogActivity.STATUS_ID,
            LogActivity.SHIFT_1,
            LogActivity.SHIFT_2,
        )
        .filter(
            LogActivity.ACTIVITY == 'Piket Siaga',
            LogActivity.STATUS_ID == 3,
            LogActivity.ACTIVITY_DATE >= source_awal,
            LogActivity.ACTIVITY_DATE <= source_akhir,
        )
        .all()
    )

    result = {}

    for nip, activity_date, status_id, shift1, shift2 in rows:
        if not nip or not activity_date or status_id != 3:
            continue

        nip_key = str(nip).strip()

        if int(shift1 or 0) == 1:
            target_date = activity_date
            if tgl_awal.date() <= target_date <= tgl_akhir.date():
                result[(nip_key, target_date)] = 'shift1'

        if int(shift2 or 0) == 1:
            target_date = activity_date + timedelta(days=1)
            if tgl_awal.date() <= target_date <= tgl_akhir.date():
                result[(nip_key, target_date)] = 'shift2'

    return result


def _load_master_potongan_meal_cut_codes():
    """Ambil kode Master Potongan yang berlaku sebagai ketidakhadiran/potong UM."""
    rows = (
        db.session.query(
            MfPot.TINGKAT,
            MfPot.KATEGORI,
            MfPot.NAMA_POT,
            MfPot.TINDAKAN,
        )
        .all()
    )

    codes = set()
    categories = {
        'CUTI', 'SAKIT', 'IJIN', 'IZIN', 'ALPA', 'CAP'
    }

    for tingkat, kategori, nama_pot, tindakan in rows:
        code = str(tingkat or '').strip().upper()
        if not code:
            continue

        kategori_u = str(kategori or '').strip().upper()
        nama_u = str(nama_pot or '').strip().upper()
        tindakan_u = str(tindakan or '').strip().upper()

        if (
            kategori_u in categories
            or 'UANG MAKAN' in nama_u
            or 'UANG MAKAN' in tindakan_u
        ):
            codes.add(code)

    # Kode yang sudah menjadi aturan bisnis eksplisit.
    codes.update({
        'CT', 'CAP', 'S', 'S-1', 'S-2',
        'I', 'IJIN', 'IZIN', 'ALPA',
    })
    return codes


def _absensi_ket_metadata(
    absensi,
    siaga_ket_map=None,
    nip=None,
    master_potongan_codes=None,
):
    """
    Presentation KET dari ABSENSI final.

    Tidak melakukan normalisasi ulang. Siaga berasal dari LOG_ACTIVITIY
    hasil kehadiran petugas; kode lainnya berasal dari ABSENSI final.
    """
    history = str(
        absensi.HISTORY_TRANSAKSI_IN
        or absensi.HISTORY_TRANSAKSI_OUT
        or ''
    ).strip().upper()

    transaksi = str(absensi.TRANSAKSI_IN or '').strip().upper()

    if siaga_ket_map and nip and absensi.TGL_KERJA:
        siaga_code = siaga_ket_map.get(
            (str(nip).strip(), absensi.TGL_KERJA.date())
        )
        if siaga_code:
            return siaga_code, ket_color_key(
                siaga_code,
                absensi.STATUS_UM,
                master_potongan_codes,
            )

    if history == 'SIAGA':
        return 'SIAGA', 'siaga'

    if history:
        code = history
    elif transaksi == 'DINASLUAR':
        code = 'DL'
    elif transaksi == 'CUTI':
        code = 'CT'
    elif transaksi == 'SAKIT':
        code = 'S'
    elif transaksi in ('IJIN', 'IZIN'):
        code = 'I'
    elif transaksi == 'ALPA':
        code = 'A'
    elif transaksi == 'WFH':
        code = 'WFH'
    else:
        code = ''

    code = code.strip().upper()

    return code, ket_color_key(
        code,
        absensi.STATUS_UM,
        master_potongan_codes,
    )

def _absensi_awal_psw(absensi):
    """
    Awal PSW = selisih mentah actual OUT terhadap jam baku OUT.

    Ini adalah nilai sebelum clamp PSW menjadi hanya nilai negatif.
    Jika data final tidak memiliki pasangan waktu, gunakan TotalPSW
    sebagai fallback agar hasil yang sudah dinormalisasi tetap terlihat.
    """
    if absensi.TGL_JAM_OUT and absensi.TGL_JAM_BAKU_OUT:
        try:
            return round(
                (
                    absensi.TGL_JAM_OUT
                    - absensi.TGL_JAM_BAKU_OUT
                ).total_seconds() / 60,
                2,
            )
        except Exception:
            pass

    return (
        round(float(absensi.TOTAL_PSW or 0), 2)
        if absensi.TOTAL_PSW is not None
        else 0
    )


def _data_absensi_export_rows_from_request():
    """Ambil dataset final ABSENSI periode laporan dari ABSENSI."""
    tgl_awal_str = str(request.args.get('tgl_awal') or '').strip()
    tgl_akhir_str = str(request.args.get('tgl_akhir') or '').strip()

    if not tgl_awal_str or not tgl_akhir_str:
        raise ValueError('Tanggal periode kosong.')

    tgl_awal = datetime.strptime(tgl_awal_str, '%Y-%m-%d')
    tgl_akhir_exclusive = datetime.strptime(
        tgl_akhir_str, '%Y-%m-%d'
    ) + timedelta(days=1)

    query = (
        db.session.query(Absensi, Pegawai, MfUnitKerja)
        .join(Pegawai, Absensi.FINGER_ID == Pegawai.FINGER_ID)
        .outerjoin(
            MfUnitKerja,
            Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID
        )
        .filter(
            Absensi.TGL_KERJA >= tgl_awal,
            Absensi.TGL_KERJA < tgl_akhir_exclusive,
            Pegawai.NIP.isnot(None),
            db.func.trim(Pegawai.NIP) != '',
            Absensi.FINGER_ID.isnot(None),
            db.func.trim(Absensi.FINGER_ID) != '',
            db.func.upper(db.func.trim(db.func.coalesce(Pegawai.IS_KELUAR, ''))).in_(['N', '0']),
            db.func.upper(db.func.trim(db.func.coalesce(MfUnitKerja.IS_USE, ''))).in_(['Y', '1']),
        )
    )

    filter_column_map = {
        'NIP': Pegawai.NIP,
        'Nama': Pegawai.NAMA,
        'NAMA': Pegawai.NAMA,
        'UnitKerja': MfUnitKerja.NAMA_UNIT_KERJA,
        'Unit': MfUnitKerja.NAMA_UNIT_KERJA,
        'Unit Kerja': MfUnitKerja.NAMA_UNIT_KERJA,
        'Jabatan': Pegawai.JABATAN,
        'FingerID': Absensi.FINGER_ID,
        'Finger ID': Absensi.FINGER_ID,
        'Fingerid': Absensi.FINGER_ID,
        'FINGER_ID': Absensi.FINGER_ID,
    }

    for field, value in (
        (str(request.args.get('filter_field1') or '').strip(),
         str(request.args.get('filter_value1') or '').strip()),
        (str(request.args.get('filter_field2') or '').strip(),
         str(request.args.get('filter_value2') or '').strip()),
    ):
        column = filter_column_map.get(field)
        if column is not None and value:
            query = query.filter(column.like(f'%{value}%'))

    results = query.order_by(
        Pegawai.NIP.asc(),
        Absensi.TGL_KERJA.asc(),
        Absensi.FINGER_ID.asc(),
    ).all()

    siaga_ket_map = _load_siaga_ket_map(
        tgl_awal,
        tgl_akhir_exclusive - timedelta(days=1),
    )

    master_potongan_codes = _load_master_potongan_meal_cut_codes()

    hari_map = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu',
        'Sunday': 'Minggu',
    }

    rows = []
    for no, (a, peg, _unit) in enumerate(results, 1):
        ket, ket_class = _absensi_ket_metadata(
            a,
            siaga_ket_map,
            peg.NIP,
            master_potongan_codes,
        )
        rows.append({
            'no': no,
            'nip': str(peg.NIP or ''),
            'nama': str(peg.NAMA or ''),
            'finger_id': str(a.FINGER_ID or ''),
            'tgl_kerja': a.TGL_KERJA.strftime('%d %b %Y') if a.TGL_KERJA else '',
            'hari': hari_map.get(a.TGL_KERJA.strftime('%A'), '') if a.TGL_KERJA else '',
            'jam_baku_in': a.TGL_JAM_BAKU_IN.strftime('%H:%M') if a.TGL_JAM_BAKU_IN else '',
            'jam_baku_out': a.TGL_JAM_BAKU_OUT.strftime('%H:%M') if a.TGL_JAM_BAKU_OUT else '',
            'jam_in': a.TGL_JAM_IN.strftime('%H:%M') if a.TGL_JAM_IN else '',
            'jam_out': a.TGL_JAM_OUT.strftime('%H:%M') if a.TGL_JAM_OUT else '',
            'awal_tlm': a.AWAL_TLM,
            'total_tlm': a.TOTAL_TLM,
            'tingkat_tlm': a.TINGKAT_TLM,
            'persen_pot_tlm': a.PERSEN_POT_TLM,
            'awal_psw': _absensi_awal_psw(a),
            'total_psw': a.TOTAL_PSW,
            'tingkat_psw': a.TINGKAT_PSW,
            'persen_pot_psw': a.PERSEN_POT_PSW,
            'ket': ket,
            'ket_class': ket_class,
            'ket_color': (
                REPORT_COLORS.get(ket_class, '')
                if ket_class != 'normal'
                else ''
            ),
        })

    return rows, f'{tgl_awal_str} s/d {tgl_akhir_str}'

def api_normalisasi_download_excel():
    try:
        from app.utils.dataAbsensiExportHelper import build_excel
        rows, period_label = _data_absensi_export_rows_from_request()
        output = build_excel(rows, period_label)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Data_Absensi_Export_{period_label.replace(" ", "_").replace("/", "-")}.xlsx',
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def api_normalisasi_download_pdf():
    try:
        from app.utils.dataAbsensiExportHelper import build_pdf
        rows, period_label = _data_absensi_export_rows_from_request()
        output = build_pdf(rows, period_label)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Data_Absensi_Export_{period_label.replace(" ", "_").replace("/", "-")}.pdf',
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def api_normalisasi_absensi_view():
    """
    TAB 3 - Data Hasil Ekspor.

    READ ONLY dari ABSENSI.

    Alur:
        NORMALISASI -> EXPORT -> ABSENSI

    View tidak menjalankan NORMALISASI ulang.
    View hanya membaca data ABSENSI berdasarkan:
        - periode
        - filter NIP
        - filter Nama
        - filter Unit Kerja
        - filter Finger ID
    """

    try:
        tgl_awal_str = str(
            request.args.get('tgl_awal') or ''
        ).strip()

        tgl_akhir_str = str(
            request.args.get('tgl_akhir') or ''
        ).strip()

        filter_field1 = str(
            request.args.get('filter_field1') or ''
        ).strip()

        filter_value1 = str(
            request.args.get('filter_value1') or ''
        ).strip()

        filter_field2 = str(
            request.args.get('filter_field2') or ''
        ).strip()

        filter_value2 = str(
            request.args.get('filter_value2') or ''
        ).strip()

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

        # ========================================================
        # QUERY ABSENSI
        #
        # ABSENSI adalah sumber hasil normalisasi.
        # Tidak memanggil api_normalisasi_process().
        # ========================================================

        query = (
            db.session.query(
                Absensi,
                Pegawai,
                MfUnitKerja
            )
            .outerjoin(
                Pegawai,
                Absensi.FINGER_ID == Pegawai.FINGER_ID
            )
            .outerjoin(
                MfUnitKerja,
                Pegawai.UNIT_KERJA_ID
                == MfUnitKerja.UNIT_KERJA_ID
            )
            .filter(
                Absensi.TGL_KERJA >= tgl_awal,
                Absensi.TGL_KERJA < tgl_akhir,
                Absensi.FINGER_ID.isnot(None),
                db.func.trim(Absensi.FINGER_ID) != '',
                Pegawai.NIP.isnot(None),
                db.func.trim(Pegawai.NIP) != '',
                db.func.upper(db.func.trim(db.func.coalesce(Pegawai.IS_KELUAR, ''))).in_(['N', '0']),
                db.func.upper(db.func.trim(db.func.coalesce(MfUnitKerja.IS_USE, ''))).in_(['Y', '1']),
            )
        )

        # ========================================================
        # FILTER
        #
        # Hanya kolom yang memang diketahui ada.
        # ========================================================

        filter_column_map = {
            'NIP': Pegawai.NIP,
            'Nama': Pegawai.NAMA,
            'NAMA': Pegawai.NAMA,
            'UnitKerja': MfUnitKerja.NAMA_UNIT_KERJA,
            'Unit': MfUnitKerja.NAMA_UNIT_KERJA,
            'Unit Kerja': MfUnitKerja.NAMA_UNIT_KERJA,
            'Jabatan': Pegawai.JABATAN,
            'FingerID': Absensi.FINGER_ID,
            'Finger ID': Absensi.FINGER_ID,
            'Fingerid': Absensi.FINGER_ID,
            'FINGER_ID': Absensi.FINGER_ID,
        }

        for field, value in (
            (filter_field1, filter_value1),
            (filter_field2, filter_value2),
        ):
            column = filter_column_map.get(field)

            if column is not None and value:
                query = query.filter(
                    column.like(f'%{value}%')
                )

        # ========================================================
        # URUTAN
        #
        # Untuk sementara mengikuti urutan database berdasarkan
        # Finger ID + tanggal.
        #
        # Sorting laporan berdasarkan pegawaiSortHelper akan kita
        # gunakan pada menu Rekap Absen Bulanan.
        # ========================================================

        results = (
            query
            .order_by(
                Absensi.FINGER_ID,
                Absensi.TGL_KERJA
            )
            .all()
        )

        # ========================================================
        # SERIALISASI
        # ========================================================

        data = []

        siaga_ket_map = _load_siaga_ket_map(
            tgl_awal,
            tgl_akhir,
        )
        master_potongan_codes = _load_master_potongan_meal_cut_codes()

        for i, (a, peg, unit) in enumerate(
            results,
            1
        ):

            ket, ket_class = _absensi_ket_metadata(
                a,
                siaga_ket_map,
                peg.NIP,
                master_potongan_codes,
            )

            data.append({
                'no': i,

                'nip': (
                    peg.NIP
                    if peg
                    else ''
                ),

                'nama': (
                    peg.NAMA
                    if peg
                    else ''
                ),

                'finger_id': (
                    a.FINGER_ID
                    if a.FINGER_ID is not None
                    else ''
                ),

                'unit_kerja': (
                    unit.NAMA_UNIT_KERJA
                    if unit
                    else ''
                ),

                'tgl_kerja': (
                    a.TGL_KERJA.strftime(
                        '%d %b %Y'
                    )
                    if a.TGL_KERJA
                    else ''
                ),

                'hari': (
                    a.TGL_KERJA.strftime(
                        '%A'
                    )
                    if a.TGL_KERJA
                    else ''
                ),

                'jam_baku_in': (
                    a.TGL_JAM_BAKU_IN.strftime(
                        '%H:%M'
                    )
                    if a.TGL_JAM_BAKU_IN
                    else ''
                ),

                'jam_baku_out': (
                    a.TGL_JAM_BAKU_OUT.strftime(
                        '%H:%M'
                    )
                    if a.TGL_JAM_BAKU_OUT
                    else ''
                ),

                'jam_in': (
                    a.TGL_JAM_IN.strftime(
                        '%H:%M'
                    )
                    if a.TGL_JAM_IN
                    else ''
                ),

                'jam_out': (
                    a.TGL_JAM_OUT.strftime(
                        '%H:%M'
                    )
                    if a.TGL_JAM_OUT
                    else ''
                ),

                'awal_tlm': a.AWAL_TLM,
                'total_tlm': a.TOTAL_TLM,
                'tingkat_tlm': a.TINGKAT_TLM,
                'persen_pot_tlm': a.PERSEN_POT_TLM,

                'awal_psw': _absensi_awal_psw(a),
                'total_psw': a.TOTAL_PSW,
                'tingkat_psw': a.TINGKAT_PSW,
                'persen_pot_psw': a.PERSEN_POT_PSW,

                'ket': ket,
                'ket_class': ket_class,
                'ket_color': (
                    REPORT_COLORS.get(ket_class, '')
                    if ket_class != 'normal'
                    else ''
                ),

                'is_invalid': a.IS_INVALID,
                'is_outvalid': a.IS_OUTVALID,

                'transaksi_in': a.TRANSAKSI_IN,
                'transaksi_out': a.TRANSAKSI_OUT,
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
        # ============================================================
        # HRIS REBORN BUSINESS RULE
        #
        # Populasi Data Absensi hanya berasal dari Unit Kerja aktif.
        #
        # MF_UNIT_KERJA.IS_USE:
        #   Y = unit operasional
        #   N = unit nonaktif / arsip
        #
        # Status pegawai tetap mengikuti aturan periode:
        #   N = masih aktif
        #   Y = keluar setelah / selama periode laporan
        #
        # Jadi:
        #   Unit aktif
        #       AND
        #   Pegawai aktif pada periode
        #
        # Data pegawai pada unit nonaktif tidak dihapus dari database.
        # ============================================================

        pegawai_query = (
            db.session.query(Pegawai, MfUnitKerja, MfJabatan)
            .join(
                MfUnitKerja,
                Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID
            )
            .outerjoin(
                MfJabatan,
                Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID
            )
            .filter(
                MfUnitKerja.IS_USE == 'Y'
            )
            .filter(
                Pegawai.TGL_MASUK <= tgl_akhir,
                db.or_(
                    Pegawai.IS_KELUAR == 'N',
                    db.and_(
                        Pegawai.IS_KELUAR == 'Y',
                        Pegawai.TGL_KELUAR >= tgl_awal
                    )
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