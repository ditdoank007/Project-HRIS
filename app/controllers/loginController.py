from flask import request, jsonify, session
from app.models.pegawaiModel import Pegawai
from app.models.jabatanModel import MfJabatan

def login():
    data = request.get_json()
    nip = data.get('nip', '').strip()
    password = data.get('password', '').strip()
    remember = data.get('remember', False)  # ambil nilai checkbox

    if not nip or not password:
        return jsonify({'success': False, 'message': 'NIP dan Password wajib diisi.'}), 400

    pegawai = (
        Pegawai.query
        .outerjoin(
            MfJabatan,
            Pegawai.JABATAN_ID == MfJabatan.JABATAN_ID
        )
        .filter(
            Pegawai.NIP == nip
        )
        .first()
    )
    if not pegawai:
        return jsonify({'success': False, 'message': 'NIP tidak ditemukan.'}), 401

    if pegawai.PASS != password:
        return jsonify({'success': False, 'message': 'Password salah.'}), 401

    # Atur sesi berdasarkan pilihan "Ingat Saya"
    if remember:
        session.permanent = True   # cookie akan bertahan sesuai PERMANENT_SESSION_LIFETIME (misal 7 hari)
    else:
        session.permanent = False  # cookie akan hilang saat browser ditutup

    session['logged_in'] = True
    session['nip'] = pegawai.NIP
    session['nama'] = pegawai.NAMA

    return jsonify({
        'success': True,
        'message': 'Login berhasil.',
        'data': {
            'nip': pegawai.NIP,
            'nama': pegawai.NAMA,
            'jabatan': (
                MfJabatan.query
                .filter(
                    MfJabatan.JABATAN_ID == pegawai.JABATAN_ID
                )
                .with_entities(
                    MfJabatan.NAMA_JABATAN
                )
                .scalar()
                or '-'
            )
        }
    })

def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logout berhasil.'})