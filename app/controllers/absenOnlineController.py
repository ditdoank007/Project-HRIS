from datetime import datetime, time

from flask import jsonify, session

from app import db
from app.models.pegawaiModel import Pegawai
from app.models.kalenderModel import MfKalender
from app.models.timeRecorderModel import TimeRecorder
from app.models.absensiModel import Absensi


WFH_CODE = '998'
FWA_CODE = '997'


def _get_today_wfh():
    """
    WFH 998 pada MASTER KALENDER berlaku untuk seluruh pegawai.
    """
    today = datetime.now().date()

    return (
        MfKalender.query
        .filter(
            MfKalender.TGL_KERJA >= datetime.combine(
                today, time.min
            ),
            MfKalender.TGL_KERJA <= datetime.combine(
                today, time.max
            )
        )
        .first()
    )


def _get_logged_pegawai():
    nip = session.get('nip')

    if not nip:
        return None

    return Pegawai.query.filter_by(NIP=nip).first()


def status_absen_online():
    """
    Mengecek apakah user login dan hari ini merupakan WFH.

    Sebelum 12:00  -> ABSEN MASUK
    Mulai 12:00    -> ABSEN PULANG
    """

    if not session.get('logged_in'):
        return jsonify({
            'success': False,
            'message': 'Silakan login terlebih dahulu.'
        }), 401

    pegawai = _get_logged_pegawai()

    if not pegawai:
        return jsonify({
            'success': False,
            'message': 'Data pegawai tidak ditemukan.'
        }), 404

    kalender = _get_today_wfh()

    is_wfh = bool(
        kalender
        and (kalender.KET or '').strip().upper() == 'WFH'
    )

    if not is_wfh:
        return jsonify({
            'success': True,
            'available': False,
            'message': 'Hari ini bukan hari WFH.'
        })

    now = datetime.now()

    status = 'IN' if now.hour < 12 else 'OUT'
    jenis = 'ABSEN MASUK' if status == 'IN' else 'ABSEN PULANG'

    existing = (
        TimeRecorder.query
        .filter(
            TimeRecorder.FINGER_ID == pegawai.FINGER_ID,
            TimeRecorder.WAKTU >= datetime.combine(
                now.date(), time.min
            ),
            TimeRecorder.WAKTU <= datetime.combine(
                now.date(), time.max
            ),
            TimeRecorder.STATUS == status,
            TimeRecorder.MESIN == 'WEB'
        )
        .first()
    )

    return jsonify({
        'success': True,
        'available': True,
        'kode': WFH_CODE,
        'status': status,
        'jenis': jenis,
        'already_absen': bool(existing),
        'nama': pegawai.NAMA,
        'nip': pegawai.NIP,
        'finger_id': pegawai.FINGER_ID
    })


def punch_absen_online():
    """
    Menyimpan ABSEN ONLINE WFH.

    Jalur ini khusus WFH 998.
    Tidak menggunakan menu ABSEN NON FINGER.
    """

    if not session.get('logged_in'):
        return jsonify({
            'success': False,
            'message': 'Silakan login terlebih dahulu.'
        }), 401

    pegawai = _get_logged_pegawai()

    if not pegawai:
        return jsonify({
            'success': False,
            'message': 'Data pegawai tidak ditemukan.'
        }), 404

    kalender = _get_today_wfh()

    is_wfh = bool(
        kalender
        and (kalender.KET or '').strip().upper() == 'WFH'
    )

    if not is_wfh:
        return jsonify({
            'success': False,
            'message': 'Hari ini tidak ditetapkan sebagai WFH.'
        }), 400

    now = datetime.now()
    status = 'IN' if now.hour < 12 else 'OUT'

    # ============================================================
    # CEGAH ABSEN GANDA
    # ============================================================

    existing = (
        TimeRecorder.query
        .filter(
            TimeRecorder.FINGER_ID == pegawai.FINGER_ID,
            TimeRecorder.WAKTU >= datetime.combine(
                now.date(), time.min
            ),
            TimeRecorder.WAKTU <= datetime.combine(
                now.date(), time.max
            ),
            TimeRecorder.STATUS == status,
            TimeRecorder.MESIN == 'WEB'
        )
        .first()
    )

    if existing:
        return jsonify({
            'success': False,
            'duplicate': True,
            'message': (
                'Anda sudah melakukan '
                + ('ABSEN MASUK.' if status == 'IN'
                   else 'ABSEN PULANG.')
            )
        }), 409

    # ============================================================
    # TIME_RECORDER
    # ============================================================

    tr = TimeRecorder(
        FINGER_ID=pegawai.FINGER_ID,
        WAKTU=now,
        STATUS=status,
        MESIN='WEB',
        KET='WEB',
        TRANSAKSI='WEB',
        UPDATE_IN_BY='WEB',
        UPDATE_DATE=now,
        KET_INJECT=pegawai.NIP,
        REF_INJECT='WFH',
        TRX='-'
    )

    db.session.add(tr)

    # ============================================================
    # ABSENSI
    #
    # WFH disimpan sebagai transaksi WFH, tetapi jam aktual
    # tetap disimpan sebagai TglJamIn / TglJamOut.
    # ============================================================

    tgl_kerja = datetime.combine(now.date(), time.min)

    absensi = (
        Absensi.query
        .filter(
            Absensi.FINGER_ID == pegawai.FINGER_ID,
            Absensi.TGL_KERJA == tgl_kerja
        )
        .first()
    )

    if not absensi:
        absensi = Absensi(
            FINGER_ID=pegawai.FINGER_ID,
            TGL_KERJA=tgl_kerja
        )
        db.session.add(absensi)

    if status == 'IN':
        absensi.TGL_JAM_IN = now
        absensi.TRANSAKSI_IN = 'WFH'
        absensi.UPDATE_IN_BY = 'WEB'
        absensi.UPDATE_IN_DATE = now
        absensi.KET_IN = 'ABSEN ONLINE WFH'
        absensi.PENDUKUNG_IN = WFH_CODE

    else:
        absensi.TGL_JAM_OUT = now
        absensi.TRANSAKSI_OUT = 'WFH'
        absensi.UPDATE_OUT_BY = 'WEB'
        absensi.UPDATE_OUT_DATE = now
        absensi.KET_OUT = 'ABSEN ONLINE WFH'
        absensi.PENDUKUNG_OUT = WFH_CODE

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            'success': False,
            'message': 'ABSEN gagal disimpan ke database.'
        }), 500

    return jsonify({
        'success': True,
        'message': 'ABSEN BERHASIL',
        'status': status,
        'jenis': (
            'ABSEN MASUK'
            if status == 'IN'
            else 'ABSEN PULANG'
        ),
        'jam': now.strftime('%H:%M'),
        'nama': pegawai.NAMA
    })
