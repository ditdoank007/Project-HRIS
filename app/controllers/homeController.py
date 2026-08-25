# app/controllers/homeController.py

from flask import render_template, request, jsonify
from datetime import datetime
from app import db
from app.models.pegawaiModel import Pegawai
from app.models.kalenderModel import MfKalender
from app.models.timSiagaModel import MfTimSiaga
from app.models.timSiagaAnggotaModel import MfTimSiagaAnggota
from app.models.absensiModel import Absensi
from app.models.potModel import MfPot
from sqlalchemy import func, or_


def home():
    from app.controllers.dashboard_1MediaInformasiController import (
        get_latest_running_text, get_hero_images
    )

    running_text = get_latest_running_text()
    if not running_text:
        running_text = "Selamat Datang di Portal Internal Basarnas Surabaya"

    hero_images = get_hero_images()

    # ============================================================
    # ABSEN ONLINE
    # Tahap awal: tombol hanya aktif jika hari ini
    # ditetapkan sebagai WFH pada MASTER KALENDER.
    #
    # Kode:
    #   998 = WFH
    #   997 = FWA (akan dikembangkan kemudian)
    # ============================================================

    today = datetime.now().date()

    kalender_hari_ini = (
        MfKalender.query
        .filter(
            MfKalender.TGL_KERJA >= datetime.combine(
                today,
                datetime.min.time()
            ),
            MfKalender.TGL_KERJA <= datetime.combine(
                today,
                datetime.max.time()
            )
        )
        .first()
    )

    is_wfh_today = bool(
        kalender_hari_ini
        and (kalender_hari_ini.KET or '').strip().upper() == 'WFH'
    )

    return render_template(
        'index.html',
        running_text=running_text,
        hero_images=hero_images,
        is_wfh_today=is_wfh_today,
        online_attendance_code='998' if is_wfh_today else None
    )

def search_buku_telp():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    keyword = f'%{q.lower()}%'
    results = Pegawai.query.filter(
        func.lower(Pegawai.NAMA).like(keyword) |
        func.lower(Pegawai.NO_TELP).like(keyword) |
        func.lower(Pegawai.ALAMAT).like(keyword)
    ).all()

    data = [{
        'nama': p.NAMA or '',
        'instansi': 'Basarnas Surabaya',
        'no_telp': p.NO_TELP or '',
        'alamat': p.ALAMAT or ''
    } for p in results]

    return jsonify(data)


def get_piket_siaga():
    tanggal = request.args.get('tanggal')
    shift = request.args.get('shift')

    if not tanggal or not shift:
        return jsonify({'success': False, 'message': 'Tanggal dan shift wajib diisi.'}), 400

    try:
        year, month, _ = tanggal.split('-')
        month = str(int(month))
    except ValueError:
        return jsonify({'success': False, 'message': 'Format tanggal tidak valid.'}), 400

    anggota_list = MfTimSiagaAnggota.query.filter_by(
        BULAN_PERIODE=month,
        TAHUN_PERIODE=year,
        SHIFT=shift,
        IS_AKTIF='Y'
    ).all()

    if not anggota_list:
        return jsonify({'success': False, 'message': 'Tidak ada data piket siaga.'}), 404

    wilayah_map = {}
    for ag in anggota_list:
        pegawai = Pegawai.query.filter_by(NIP=ag.NIP).first()
        if not pegawai:
            continue

        wilayah = ag.ID_UNIT_KERJA or 'Tidak Diketahui'
        if wilayah not in wilayah_map:
            wilayah_map[wilayah] = []

        wilayah_map[wilayah].append({
            'nama': pegawai.NAMA,
            'no_telp': pegawai.NO_TELP,
            'fungsional': ag.FUNGSIONAL or ''
        })

    data = [{'wilayah': w, 'anggota': a} for w, a in wilayah_map.items()]

    return jsonify({
        'success': True,
        'periode': tanggal,
        'shift': shift,
        'data': data
    })


def get_pelanggaran_disiplin():
    """
    Mengambil data pelanggaran disiplin pegawai dari database.
    Chain query: PEGAWAI -> ABSENSI (via ABSENSI_ID) -> MF_POT (via POTONGAN_ID)

    Catatan kolom:
      - TOTAL_TLM  : total keterlambatan (satuan tergantung sistem — menit atau hari)
      - TOTAL_PSW  : total pulang sebelum waktu
      - TINGKAT_TLM: tingkat pelanggaran per record absensi ('RINGAN'/'SEDANG'/'BERAT')
      - MF_POT.TINGKAT   : tingkat dari aturan master potongan
      - MF_POT.TINDAKAN  : jenis hukuman disiplin
      - MF_POT.PERSEN_POT: persentase potongan tunjangan
      - MF_POT.DURASI_POT + SATUAN_DURASI: lama potongan
    """
    try:
        results = db.session.query(
            Pegawai.NAMA,
            Absensi.TOTAL_TLM,
            Absensi.TOTAL_PSW,
            Absensi.TINGKAT_TLM,
            MfPot.TINGKAT,
            MfPot.TINDAKAN,
            MfPot.NAMA_POT,
            MfPot.PERSEN_POT,
            MfPot.DURASI_POT,
            MfPot.SATUAN_DURASI
        ).select_from(Pegawai)\
         .join(Absensi, Pegawai.ABSENSI_ID == Absensi.ABSENSI_ID)\
         .join(MfPot, Absensi.POTONGAN_ID == MfPot.POTONGAN_ID)\
         .filter(
             MfPot.TINGKAT.isnot(None),
             or_(
                 Absensi.TOTAL_TLM > 0,
                 Absensi.TOTAL_PSW > 0
             )
         )\
         .order_by(Absensi.TOTAL_TLM.desc())\
         .all()

        if not results:
            return jsonify({'success': False, 'message': 'Tidak ada data pelanggaran disiplin.'}), 404

        data = []
        for i, row in enumerate(results, 1):

            # ── Kategori hukuman ─────────────────────────────────────────────
            # Prioritas: TINGKAT dari MF_POT, fallback ke TINGKAT_TLM di ABSENSI
            tingkat_raw = (row.TINGKAT or row.TINGKAT_TLM or '').strip().upper()
            if 'BERAT' in tingkat_raw:
                kategori = 'Hukuman Disiplin Berat'
            elif 'SEDANG' in tingkat_raw:
                kategori = 'Hukuman Disiplin Sedang'
            else:
                kategori = 'Hukuman Disiplin Ringan'

            # ── Jumlah hari pelanggaran ───────────────────────────────────────
            # TOTAL_TLM dan TOTAL_PSW satuannya bergantung konfigurasi sistem.
            # Jika dalam MENIT  → bagi dengan 480 (8 jam × 60 menit)
            # Jika dalam JAM    → bagi dengan 8
            # Jika sudah HARI   → gunakan langsung (tidak perlu dibagi)
            # Sesuaikan DIVISOR di bawah setelah mengecek data aktual di database.
            DIVISOR = 1  # ganti ke 480 jika TOTAL_TLM dalam menit
            total_tlm = row.TOTAL_TLM or 0
            total_psw = row.TOTAL_PSW or 0
            hari = int((total_tlm + total_psw) / DIVISOR)

            # ── Lama potongan ─────────────────────────────────────────────────
            if row.DURASI_POT and row.DURASI_POT > 0:
                lama_pot = f"{int(row.DURASI_POT)} {(row.SATUAN_DURASI or 'Bulan').strip()}"
            else:
                lama_pot = "0"

            data.append({
                'no': i,
                'nama': row.NAMA or '-',
                'hari': hari,
                'kategori': kategori,
                'jenis': row.TINDAKAN or row.NAMA_POT or '-',
                'potongan': int(row.PERSEN_POT or 0),
                'lama_pot': lama_pot
            })

        return jsonify({'success': True, 'data': data})

    # Di homeController.py, ubah bagian except sementara:
    except Exception as e:
        import traceback
        traceback.print_exc()   # cetak full traceback di terminal Flask
        return jsonify({'success': False, 'message': f'Gagal memuat data: {str(e)}'}), 500