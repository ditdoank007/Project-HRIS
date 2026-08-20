# app/routes/routes.py

from flask import Blueprint, jsonify
from app.utils.decorators import login_required
from app.controllers.homeController import get_pelanggaran_disiplin, get_piket_siaga, home, search_buku_telp
from app.controllers.loginController import login, logout
from app.controllers.dashboard_1HomeController import (
    dashboard_kgb, dashboard_pangkat, dashboard_pelanggaran, dashboard_pensiun, dashboard_trt)
from app.controllers.dashboard_1MasterFileController import (
    create_kalender_tahun, export_jam_finger_excel, export_tunjangan_excel, get_jabatan_list, get_jam_finger_list, get_jam_kerja_list, get_joblist_list, get_kalender_list,
    get_pegawai_vip_list, get_potongan_list, get_tunjangan_list, get_tunkin_class_detail, get_tunkin_class_list,
    delete_user_account, get_unit_kerja_list, get_user_account_detail, get_user_account_list, master_butir_kegiatan, master_jabatan, master_jam_finger, master_jam_kerja,
    master_kalender, master_pegawai_vip, master_potongan, master_trt as master_file_trt, master_tunkin_class,
    master_unit_kerja, master_user, master_uang_makan, cari_master_jabatan, cari_master_jam_finger, cari_master_jam_kerja,
    cari_master_kalender, cari_master_potongan, cari_master_tunkin_class, cari_master_uang_makan, cari_master_unit_kerja,
    cari_user_account, create_kalender, save_jabatan, save_jam_kerja, save_joblist, save_potongan, save_tunkin_class, save_uang_makan, save_unit_kerja, save_user_account,
    toggle_pegawai_vip, save_jam_finger,
)
from app.controllers.dashboard_1KepegawaianController import (
    kepegawaian_cari_data_pegawai,
    kepegawaian_cari_dinas_luar_umum,
    kepegawaian_data_pegawai,
    kepegawaian_dinas_luar_operasi,
    kepegawaian_dinas_luar_pelatihan,
    kepegawaian_dinas_luar_umum,
    kepegawaian_mutasi_penempatan_pegawai,
    kepegawaian_pegawai_cuti,
    kepegawaian_pegawai_sakit,
    kepegawaian_pegawai_tidak_hadir,
    kepegawaian_update_pendukung,
    api_pegawai_get as master_api_pegawai_get,
    api_pegawai_save as master_api_pegawai_save,
    api_pegawai_delete as master_api_pegawai_delete,
    api_pegawai_cari as master_api_pegawai_cari,
    api_pegawai_get_filter_fields as master_api_pegawai_get_filter_fields,
    api_dinas_luar_search_pegawai as master_api_dinas_luar_search_pegawai,
    api_dinas_luar_save as master_api_dinas_luar_save,
    api_dinas_luar_get as master_api_dinas_luar_get,
    api_dinas_luar_delete as master_api_dinas_luar_delete,
    api_sprin_header_save as master_api_sprin_header_save,
    api_dinas_luar_save_peserta as master_api_dinas_luar_save_peserta,
    api_dinas_luar_cari as master_api_dinas_luar_cari,
    api_dinas_luar_get_filter_fields as master_api_dinas_luar_get_filter_fields,
)
from app.controllers.dashboard_1MediaInformasiController import (
    media_informasi, media_informasi_detail,
    save_media_informasi, save_media_informasi_slide,
    get_media_informasi_list, get_media_informasi_by_id,
    update_media_informasi, nonaktifkan_media_informasi
)
from app.controllers.dashboard_1LaporanRekapController import (
    export_detail_jam_lembur_umum,
    export_rekap_absensi_all,
    export_rekap_absensi_individu,
    export_rekap_absensi_log_finger,
    export_rekap_clock_exception,
    export_rekap_daftar_lembur_umum,
    export_rekap_ketidakhadiran_pegawai,
    export_rekap_pelanggaran_disiplin,
    export_rekap_tunjangan_kinerja,
    export_rekap_uang_makan,
    laporan_cetak_daftar_lembur_umum,
    laporan_rekap_absensi_all,
    laporan_rekap_absensi_individu,
    laporan_rekap_absensi_log_finger,
    laporan_rekap_clock_exception,
    laporan_rekap_ketidakhadiran_pegawai,
    laporan_rekap_pelanggaran_disiplin,
    laporan_rekap_uang_makan,
    laporan_rekap_tunjangan_kinerja,
    search_pegawai_by_name,
)
from app.controllers.dashboard_1DataAbsensiController import (
    data_absensi_non_finger, data_absensi_normalisasi_finger, data_absensi_impor_file, data_absensi_pegawai_manual,
    data_absensi_pegawai_lembur_manual, data_absensi_trace_tunjangan, data_absensi_trace, cari_absensi_non_finger,
    cari_absensi_normalisasi_finger, cari_absensi_pegawai_manual, cari_absensi_pegawai_lembur_manual,
    api_trace_absensi as data_absensi_api_trace_absensi, api_trace_tunjangan as data_absensi_api_trace_tunjangan,
    api_inject_absensi_get_pegawai as data_absensi_api_inject_pegawai, api_inject_absensi_acak_jam as data_absensi_api_acak_jam,
    api_inject_absensi_save as data_absensi_api_save, api_cari_absensi_manual as data_absensi_api_cari_manual,
    api_cari_absensi_manual_delete as data_absensi_api_cari_delete, api_cari_absensi_manual_update as data_absensi_api_cari_update,
    api_inject_lembur_get_pegawai as data_absensi_api_inject_lembur_pegawai, api_inject_lembur_acak_jam as data_absensi_api_inject_lembur_acak,
    api_inject_lembur_save as data_absensi_api_inject_lembur_save, api_cari_lembur_manual as data_absensi_api_cari_lembur,
    api_cari_lembur_manual_delete as data_absensi_api_cari_lembur_delete, api_cari_lembur_manual_update as data_absensi_api_cari_lembur_update,
    api_absensi_non_finger_search as data_absensi_api_non_finger_search,
    api_absensi_non_finger_koreksi as data_absensi_api_non_finger_koreksi,
    api_absensi_non_finger_save as data_absensi_api_non_finger_save,
    api_absensi_non_finger_delete as data_absensi_api_non_finger_delete,
    api_search_pegawai_non_finger as data_absensi_api_search_pegawai,
    api_cari_absensi_non_finger as data_absensi_api_cari_non_finger,
    api_normalisasi_get_fields as data_absensi_api_normalisasi_fields,
    api_normalisasi_import_finger as data_absensi_api_normalisasi_import,
    api_normalisasi_process as data_absensi_api_normalisasi_process,
    api_normalisasi_upload_dat as data_absensi_api_normalisasi_upload_dat,
    api_normalisasi_commit_dat as data_absensi_api_normalisasi_commit_dat,
    api_normalisasi_export as data_absensi_api_normalisasi_export,
    api_normalisasi_absensi_view as data_absensi_api_normalisasi_absensi_view,
    api_closing_get as data_absensi_api_closing_get,
    api_closing_save as data_absensi_api_closing_save,
    api_cari_absensi_normalisasi_finger as data_absensi_api_cari_normalisasi_finger,
)
from app.controllers.dashboard_2DataSiagaController import (
    data_siaga_absensi_kehadiran, data_siaga_cetak_daftar_lembur_siaga, data_siaga_cetak_rekap_siaga,
    data_siaga_cetak_uang_siaga, data_siaga_jadwal_ulang, data_siaga_membuat_jadwal_piket_siaga,
    api_absensi_kehadiran_get as data_siaga_api_absensi_kehadiran_get,
    api_absensi_kehadiran_update as data_siaga_api_absensi_kehadiran_update,
)
from app.controllers.dashboard_2MasterDataController import (
    master_data_email_broadcast,
    master_data_kgr,
    master_data_nominal_ut_piket,
    master_data_tim_siaga,
    master_data_user_account,
    api_tim_siaga_save as master_data_api_tim_siaga_save,
    api_tim_siaga_delete as master_data_api_tim_siaga_delete,
    api_tim_siaga_get as master_data_api_tim_siaga_get,
    api_tim_siaga_save_as as master_data_api_tim_siaga_save_as,
    api_search_pegawai_tim as master_data_api_search_pegawai_tim,
    cari_data_kgr as master_data_cari_kgr,
    cari_data_piket_siaga as master_data_cari_piket_siaga,
    cari_data_piket_tim_siaga as master_data_cari_piket_tim_siaga,
    cari_data_tim_siaga as master_data_cari_tim_siaga,
    api_cari_tim_siaga as master_data_api_cari_tim_siaga,
    api_cari_tim_siaga_get as master_data_api_cari_tim_siaga_get,
    api_kgr_search_pegawai as master_data_api_kgr_search_pegawai,
    api_kgr_get_shift as master_data_api_kgr_get_shift,
    api_kgr_save as master_data_api_kgr_save,
    api_kgr_delete as master_data_api_kgr_delete,
    api_kgr_get as master_data_api_kgr_get,
    api_kgr_save_as as master_data_api_kgr_save_as,
    api_kgr_cari as master_data_api_kgr_cari,
    api_kgr_get_filter_fields as master_data_api_kgr_get_filter_fields,
    api_email_broadcast_get as master_data_api_email_broadcast_get,
    api_email_broadcast_save as master_data_api_email_broadcast_save,
)
from app.controllers.dashboard_2OtoritasPersetujuanController import (
    api_otorisasi_kakansar_approve,
    api_otorisasi_kakansar_belum,
    api_otorisasi_kakansar_filter_fields,
    api_otorisasi_kakansar_sudah,
    api_otorisasi_kakansar_undo,
    otorisasi_persetujuan_kepala_kantor,
    otorisasi_persetujuan_kepala_seksi_operasi,
    api_otorisasi_kasiops_belum,
    api_otorisasi_kasiops_approve,
    api_otorisasi_kasiops_sudah,
    api_otorisasi_kasiops_undo,
    api_otorisasi_kasiops_filter_fields,
)
from app.controllers.dashboard_2HomeController import (
    dashboard_tim_siaga,
)
from app.controllers.dashboard_3HomeController import (
    dashboard_kinerja,
)
from app.controllers.dashboard_3AktivitasController import (
    aktifitasku_dashboard,
    aktifitasku_buku_harian,
    aktifitasku_buku_harian_baru_utama,
    aktifitasku_buku_harian_baru_tambahan,
    aktifitasku_buku_harian_baru_penunjang,
    aktifitasku_dupak,
    aktifitasku_skp,
    aktifitasku_jadwal_piket,
    aktifitasku_dinas_luar,
    aktifitasku_update_pendukung,
)
from app.controllers.dashboard_3BenefitController import (
    benefit_tunjangan_kinerja,
    benefit_rekap_uang_makan,
)
from app.controllers.dashboard_3ApprovalController import (
    approval_approved,
    approved_request,
)
from app.controllers.dashboard_3ProfileController import (
    profile,
)
from app.controllers.dashboard_3KirimController import (
    kirim_kritik_saran,
    kirim_forum_media_informasi,
)
from app.controllers.dashboard_3PengajuanController import (
    pengajuan_skp,
    pengajuan_absensi,
)
from app.models.pegawaiModel import Pegawai

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return home()

@main.route('/api/search_pegawai')
def api_search_pegawai():
    return search_buku_telp()

@main.route('/api/piket_siaga')
def api_piket_siaga():
    return get_piket_siaga()

@main.route('/api/pelanggaran_disiplin')
def api_pelanggaran_disiplin():
    return get_pelanggaran_disiplin()

@main.route('/api/login', methods=['POST'])
def api_login():
    return login()

@main.route('/api/logout', methods=['POST'])
def api_logout():
    return logout()

@main.route('/api/pegawai/preview', methods=['GET'])
def preview_pegawai():
    data = Pegawai.query.order_by(Pegawai.NIP.asc()).limit(20).all()
    return jsonify({
        'count': len(data),
        'data': [pegawai.to_dict() for pegawai in data]
    })

# ============================
# ---- Dashboard 1 Routes ----
# ============================
# Dasboard :
@main.route('/dashboard/pelanggaran')
@login_required
def view_dashboard_pelanggaran():
    return dashboard_pelanggaran()

@main.route('/dashboard/pensiun')
@login_required
def view_dashboard_pensiun():
    return dashboard_pensiun()

@main.route('/dashboard/pangkat')
@login_required
def view_dashboard_pangkat():
    return dashboard_pangkat()

@main.route('/dashboard/kgb')
@login_required
def view_dashboard_kgb():
    return dashboard_kgb()

@main.route('/dashboard/trt')
@login_required
def view_dashboard_trt():
    return dashboard_trt()

# Kepegawaian :
@main.route('/kepegawaian/data-pegawai')
@login_required
def view_kepegawaian_data_pegawai():
    return kepegawaian_data_pegawai()

@main.route('/api/pegawai/get')
@login_required
def api_pegawai_get():
    return master_api_pegawai_get()

@main.route('/api/pegawai/save', methods=['POST'])
@login_required
def api_pegawai_save():
    return master_api_pegawai_save()

@main.route('/api/pegawai/delete', methods=['POST'])
@login_required
def api_pegawai_delete():
    return master_api_pegawai_delete()

@main.route('/kepegawaian/cari/data-pegawai')
@login_required
def view_kepegawaian_cari_data_pegawai():
    return kepegawaian_cari_data_pegawai()

@main.route('/api/pegawai/cari')
@login_required
def api_pegawai_cari():
    return master_api_pegawai_cari()

@main.route('/api/pegawai/filter-fields')
@login_required
def api_pegawai_get_filter_fields():
    return master_api_pegawai_get_filter_fields()

@main.route('/kepegawaian/dinas-luar-umum')
@login_required
def view_kepegawaian_dinas_luar_umum():
    return kepegawaian_dinas_luar_umum()

@main.route('/api/sprin-header/save', methods=['POST'])
@login_required
def api_sprin_header_save():
    return master_api_sprin_header_save()

@main.route('/api/dinas-luar/save-peserta', methods=['POST'])
@login_required
def api_dinas_luar_save_peserta():
    return master_api_dinas_luar_save_peserta()

@main.route('/api/dinas-luar/search-pegawai')
@login_required
def api_dinas_luar_search_pegawai():
    return master_api_dinas_luar_search_pegawai()

@main.route('/api/dinas-luar/save', methods=['POST'])
@login_required
def api_dinas_luar_save():
    return master_api_dinas_luar_save()

@main.route('/api/dinas-luar/get')
@login_required
def api_dinas_luar_get():
    return master_api_dinas_luar_get()

@main.route('/api/dinas-luar/delete', methods=['POST'])
@login_required
def api_dinas_luar_delete():
    return master_api_dinas_luar_delete()


@main.route('/kepegawaian/cari/dinas-luar-umum')
@login_required
def view_kepegawaian_cari_dinas_luar_umum():
    return kepegawaian_cari_dinas_luar_umum('DL')


@main.route('/kepegawaian/cari/dinas-luar-operasi')
@login_required
def view_kepegawaian_cari_dinas_luar_operasi():
    return kepegawaian_cari_dinas_luar_umum('OPR')


@main.route('/kepegawaian/cari/dinas-luar-pelatihan')
@login_required
def view_kepegawaian_cari_dinas_luar_pelatihan():
    return kepegawaian_cari_dinas_luar_umum('POT')

@main.route('/api/dinas-luar/cari')
@login_required
def api_dinas_luar_cari():
    return master_api_dinas_luar_cari()

@main.route('/api/dinas-luar/filter-fields')
@login_required
def api_dinas_luar_get_filter_fields():
    return master_api_dinas_luar_get_filter_fields()

@main.route('/kepegawaian/dinas-luar-operasi')
@login_required
def view_kepegawaian_dinas_luar_operasi():
    return kepegawaian_dinas_luar_operasi()

# API: Save Dinas Luar Operasi
@main.route('/api/dinas-luar-operasi/save', methods=['POST'])
@login_required
def api_dinas_luar_operasi_save():
    from app.controllers.dashboard_1KepegawaianController import api_dinas_luar_operasi_save
    return api_dinas_luar_operasi_save()

# API: Get Dinas Luar Operasi by No Surat
@main.route('/api/dinas-luar-operasi/get')
@login_required
def api_dinas_luar_operasi_get():
    from app.controllers.dashboard_1KepegawaianController import api_dinas_luar_operasi_get
    return api_dinas_luar_operasi_get()

# API: Delete Dinas Luar Operasi
@main.route('/api/dinas-luar-operasi/delete', methods=['POST'])
@login_required
def api_dinas_luar_operasi_delete():
    from app.controllers.dashboard_1KepegawaianController import api_dinas_luar_operasi_delete
    return api_dinas_luar_operasi_delete()

@main.route('/api/dinas-luar-operasi/save-peserta', methods=['POST'])
@login_required
def api_dinas_luar_operasi_save_peserta():
    from app.controllers.dashboard_1KepegawaianController import api_dinas_luar_operasi_save_peserta
    return api_dinas_luar_operasi_save_peserta()

@main.route('/kepegawaian/dinas-luar-pelatihan')
@login_required
def view_kepegawaian_dinas_luar_pelatihan():
    return kepegawaian_dinas_luar_pelatihan()

@main.route('/api/dinas-luar-pelatihan/save-peserta', methods=['POST'])
@login_required
def api_dinas_luar_pelatihan_save_peserta():
    from app.controllers.dashboard_1KepegawaianController import api_dinas_luar_pelatihan_save_peserta
    return api_dinas_luar_pelatihan_save_peserta()

@main.route('/api/dinas-luar-pelatihan/get')
@login_required
def api_dinas_luar_pelatihan_get():
    from app.controllers.dashboard_1KepegawaianController import api_dinas_luar_pelatihan_get
    return api_dinas_luar_pelatihan_get()

@main.route('/api/dinas-luar-pelatihan/delete', methods=['POST'])
@login_required
def api_dinas_luar_pelatihan_delete():
    from app.controllers.dashboard_1KepegawaianController import api_dinas_luar_pelatihan_delete
    return api_dinas_luar_pelatihan_delete()

@main.route('/kepegawaian/pegawai-cuti')
@login_required
def view_kepegawaian_pegawai_cuti():
    return kepegawaian_pegawai_cuti()

@main.route('/api/cuti/save', methods=['POST'])
@login_required
def api_cuti_save():
    from app.controllers.dashboard_1KepegawaianController import api_cuti_save
    return api_cuti_save()

@main.route('/api/cuti/get')
@login_required
def api_cuti_get():
    from app.controllers.dashboard_1KepegawaianController import api_cuti_get
    return api_cuti_get()

@main.route('/api/cuti/delete', methods=['POST'])
@login_required
def api_cuti_delete():
    from app.controllers.dashboard_1KepegawaianController import api_cuti_delete
    return api_cuti_delete()

@main.route('/api/cuti/cari')
@login_required
def api_cuti_cari():
    from app.controllers.dashboard_1KepegawaianController import api_cuti_cari
    return api_cuti_cari()

@main.route('/api/cuti/jenis')
@login_required
def api_cuti_get_jenis():
    from app.controllers.dashboard_1KepegawaianController import api_cuti_get_jenis
    return api_cuti_get_jenis()

@main.route('/api/cuti/filter-fields')
@login_required
def api_cuti_get_filter_fields():
    from app.controllers.dashboard_1KepegawaianController import api_cuti_get_filter_fields
    return api_cuti_get_filter_fields()


@main.route('/kepegawaian/pegawai-sakit')
@login_required
def view_kepegawaian_pegawai_sakit():
    return kepegawaian_pegawai_sakit()

@main.route('/kepegawaian/pegawai-tidak-hadir')
@login_required
def view_kepegawaian_pegawai_tidak_hadir():
    return kepegawaian_pegawai_tidak_hadir()

@main.route('/kepegawaian/mutasi-penempatan')
@login_required
def view_kepegawaian_mutasi_penempatan_pegawai():
    return kepegawaian_mutasi_penempatan_pegawai()

@main.route('/api/mutasi/save', methods=['POST'])
@login_required
def api_mutasi_save():
    from app.controllers.dashboard_1KepegawaianController import api_mutasi_save
    return api_mutasi_save()

@main.route('/api/mutasi/get')
@login_required
def api_mutasi_get():
    from app.controllers.dashboard_1KepegawaianController import api_mutasi_get
    return api_mutasi_get()

@main.route('/api/mutasi/delete', methods=['POST'])
@login_required
def api_mutasi_delete():
    from app.controllers.dashboard_1KepegawaianController import api_mutasi_delete
    return api_mutasi_delete()

@main.route('/api/mutasi/cari')
@login_required
def api_mutasi_cari():
    from app.controllers.dashboard_1KepegawaianController import api_mutasi_cari
    return api_mutasi_cari()

@main.route('/api/mutasi/filter-fields')
@login_required
def api_mutasi_get_filter_fields():
    from app.controllers.dashboard_1KepegawaianController import api_mutasi_get_filter_fields
    return api_mutasi_get_filter_fields()

@main.route('/kepegawaian/update-pendukung')
@login_required
def view_kepegawaian_update_pendukung():
    return kepegawaian_update_pendukung()

@main.route('/api/update-pendukung/search')
@login_required
def api_update_pendukung_search():
    from app.controllers.dashboard_1KepegawaianController import api_update_pendukung_search
    return api_update_pendukung_search()

@main.route('/api/update-pendukung/save', methods=['POST'])
@login_required
def api_update_pendukung_save():
    from app.controllers.dashboard_1KepegawaianController import api_update_pendukung_save
    return api_update_pendukung_save()

@main.route('/api/update-pendukung/tingkatan')
@login_required
def api_update_pendukung_get_tingkatan():
    from app.controllers.dashboard_1KepegawaianController import api_update_pendukung_get_tingkatan
    return api_update_pendukung_get_tingkatan()

@main.route('/api/update-pendukung/filter-fields')
@login_required
def api_update_pendukung_get_filter_fields():
    from app.controllers.dashboard_1KepegawaianController import api_update_pendukung_get_filter_fields
    return api_update_pendukung_get_filter_fields()

# Master File :
@main.route('/master/butir-kegiatan')
@login_required
def view_master_butir_kegiatan():
    return master_butir_kegiatan()

@main.route('/api/joblist/list', methods=['GET'])
@login_required
def api_joblist_list():
    return get_joblist_list()

@main.route('/api/joblist/save', methods=['POST'])
@login_required
def api_joblist_save():
    return save_joblist()

@main.route('/master/jabatan')
@login_required
def view_master_jabatan():
    return master_jabatan()

@main.route('/api/jabatan/save', methods=['POST'])
@login_required
def api_jabatan_save():
    return save_jabatan()

@main.route('/master/jam-finger')
@login_required
def view_master_jam_finger():
    return master_jam_finger()

@main.route('/api/jam-finger/save', methods=['POST'])
@login_required
def api_jam_finger_save():
    return save_jam_finger()

@main.route('/master/jam-kerja')
@login_required
def view_master_jam_kerja():
    return master_jam_kerja()

@main.route('/api/jam-kerja/save', methods=['POST'])
@login_required
def api_jam_kerja_save():
    return save_jam_kerja()

@main.route('/master/kalender')
@login_required
def view_master_kalender():
    return master_kalender()

@main.route('/api/kalender/list', methods=['GET'])
@login_required
def api_kalender_list():
    return get_kalender_list()

@main.route('/api/kalender/generate', methods=['POST'])
@login_required
def api_kalender_generate():
    return create_kalender_tahun()

@main.route('/master/pegawai-vip')
@login_required
def view_master_pegawai_vip():
    return master_pegawai_vip()

@main.route('/api/pegawai-vip/list', methods=['GET'])
@login_required
def api_pegawai_vip_list():
    return get_pegawai_vip_list()

@main.route('/api/pegawai-vip/toggle', methods=['POST'])
@login_required
def api_pegawai_vip_toggle():
    return toggle_pegawai_vip()

@main.route('/master/potongan')
@login_required
def view_master_potongan():
    return master_potongan()

@main.route('/api/potongan/save', methods=['POST'])
@login_required
def api_potongan_save():
    return save_potongan()

@main.route('/master/trt')
@login_required
def view_master_trt():
    return master_file_trt()

@main.route('/master/tunkin-class')
@login_required
def view_master_tunkin_class():
    return master_tunkin_class()

@main.route('/api/tunkin-class/detail/<int:class_id>', methods=['GET'])
@login_required
def api_tunkin_class_detail(class_id):
    return get_tunkin_class_detail(class_id)

@main.route('/api/tunkin-class/save', methods=['POST'])
@login_required
def api_tunkin_class_save():
    return save_tunkin_class()

@main.route('/master/unit-kerja')
@login_required
def view_master_unit_kerja():
    return master_unit_kerja()

@main.route('/api/unit-kerja/save', methods=['POST'])
@login_required
def api_unit_kerja_save():
    return save_unit_kerja()

@main.route('/master/user')
@login_required
def view_master_user():
    return master_user()

@main.route('/api/user-account/detail', methods=['GET'])
@login_required
def api_user_account_detail():
    return get_user_account_detail()

@main.route('/api/user-account/save', methods=['POST'])
@login_required
def api_user_account_save():
    return save_user_account()

@main.route('/api/user-account/delete', methods=['POST'])
@login_required
def api_user_account_delete():
    return delete_user_account()

@main.route('/master/uang-makan')
@login_required
def view_master_uang_makan():
    return master_uang_makan()

@main.route('/api/uang-makan/save', methods=['POST'])
@login_required
def api_uang_makan_save():
    return save_uang_makan()

@main.route('/api/tunjangan/list', methods=['GET'])
@login_required
def api_tunjangan_list():
    return get_tunjangan_list()

# Cari Master :
@main.route('/master/cari/jabatan')
@login_required
def view_cari_master_jabatan():
    return cari_master_jabatan()

@main.route('/api/jabatan/list', methods=['GET'])
@login_required
def api_jabatan_list():
    return get_jabatan_list()

@main.route('/master/cari/jam-finger')
@login_required
def view_cari_master_jam_finger():
    return cari_master_jam_finger()

@main.route('/api/jam-finger/list', methods=['GET'])
@login_required
def api_jam_finger_list():
    return get_jam_finger_list()

@main.route('/api/jam-finger/export', methods=['GET'])
@login_required
def api_jam_finger_export():
    return export_jam_finger_excel()

@main.route('/master/cari/jam-kerja')
@login_required
def view_cari_master_jam_kerja():
    return cari_master_jam_kerja()

@main.route('/api/jam-kerja/list', methods=['GET'])
@login_required
def api_jam_kerja_list():
    return get_jam_kerja_list()

@main.route('/master/cari/kalender')
@login_required
def view_cari_master_kalender():
    return cari_master_kalender()

@main.route('/master/cari/potongan')
@login_required
def view_cari_master_potongan():
    return cari_master_potongan()

@main.route('/api/potongan/list', methods=['GET'])
@login_required
def api_potongan_list():
    return get_potongan_list()

@main.route('/master/cari/tunkin-class')
@login_required
def view_cari_master_tunkin_class():
    return cari_master_tunkin_class()

@main.route('/api/tunkin-class/list', methods=['GET'])
@login_required
def api_tunkin_class_list():
    return get_tunkin_class_list()

@main.route('/master/cari/uang-makan')
@login_required
def view_cari_master_uang_makan():
    return cari_master_uang_makan()

@main.route('/api/tunjangan/export', methods=['GET'])
@login_required
def api_tunjangan_export():
    return export_tunjangan_excel()

@main.route('/master/cari/unit-kerja')
@login_required
def view_cari_master_unit_kerja():
    return cari_master_unit_kerja()

@main.route('/api/unit-kerja/list', methods=['GET'])
@login_required
def api_unit_kerja_list():
    return get_unit_kerja_list()

@main.route('/master/cari/user-account')
@login_required
def view_cari_user_account():
    return cari_user_account()

# Tambahkan route:
@main.route('/api/user-account/list', methods=['GET'])
@login_required
def api_user_account_list():
    return get_user_account_list()

# Create :
@main.route('/master/create/kalender')
@login_required
def view_create_kalender():
    return create_kalender()

# Media Informasi :
@main.route('/media-informasi')
@login_required
def view_media_informasi():
    return media_informasi()

@main.route('/api/media-informasi', methods=['POST'])
@login_required
def api_save_media_informasi():
    return save_media_informasi()

@main.route('/api/media-informasi/slide', methods=['POST'])
@login_required
def api_save_media_informasi_slide():
    return save_media_informasi_slide()

@main.route('/api/media-informasi/list', methods=['GET'])
@login_required
def api_get_media_informasi_list():
    return get_media_informasi_list()

@main.route('/api/media-informasi/<int:med_infor_id>', methods=['GET'])
@login_required
def api_get_media_informasi_by_id(med_infor_id):
    return get_media_informasi_by_id(med_infor_id)

@main.route('/api/media-informasi/<int:med_infor_id>', methods=['PUT'])
@login_required
def api_update_media_informasi(med_infor_id):
    return update_media_informasi(med_infor_id)

@main.route('/api/media-informasi/<int:med_infor_id>/nonaktif', methods=['POST'])
@login_required
def api_nonaktifkan_media_informasi(med_infor_id):
    return nonaktifkan_media_informasi(med_infor_id)

@main.route('/media-informasi/detail')
@login_required
def view_media_informasi_detail():
    return media_informasi_detail()

# Laporan Rekap :
@main.route('/laporan/cetak-daftar-lembur-umum')
@login_required
def view_laporan_cetak_daftar_lembur_umum():
    return laporan_cetak_daftar_lembur_umum()

@main.route('/laporan/cetak-daftar-lembur-umum/export', methods=['POST'])
@login_required
def export_laporan_cetak_daftar_lembur_umum():
    return export_rekap_daftar_lembur_umum()

@main.route('/laporan/cetak-daftar-lembur-umum/detail', methods=['POST'])
@login_required
def export_laporan_detail_jam_lembur_umum():
    return export_detail_jam_lembur_umum()

@main.route('/laporan/rekap-absensi-all')
@login_required
def view_laporan_rekap_absensi_all():
    return laporan_rekap_absensi_all()

@main.route('/laporan/rekap-absensi-all/export', methods=['POST'])
@login_required
def export_laporan_rekap_absensi_all():
    return export_rekap_absensi_all()

@main.route('/laporan/rekap-absensi-individu')
@login_required
def view_laporan_rekap_absensi_individu():
    return laporan_rekap_absensi_individu()

@main.route('/laporan/rekap-absensi-individu/export', methods=['POST'])
@login_required
def export_laporan_rekap_absensi_individu():
    return export_rekap_absensi_individu()

@main.route('/api/laporan/search-pegawai')
@login_required
def api_laporan_search_pegawai():
    return search_pegawai_by_name()

@main.route('/laporan/rekap-absensi-log-finger')
@login_required
def view_laporan_rekap_absensi_log_finger():
    return laporan_rekap_absensi_log_finger()

@main.route('/laporan/rekap-absensi-log-finger/export', methods=['POST'])
@login_required
def export_laporan_rekap_absensi_log_finger():
    return export_rekap_absensi_log_finger()

@main.route('/laporan/rekap-clock-exception')
@login_required
def view_laporan_rekap_clock_exception():
    return laporan_rekap_clock_exception()

@main.route('/laporan/rekap-clock-exception/export', methods=['POST'])
@login_required
def export_laporan_rekap_clock_exception():
    return export_rekap_clock_exception()

@main.route('/laporan/rekap-ketidakhadiran-pegawai')
@login_required
def view_laporan_rekap_ketidakhadiran_pegawai():
    return laporan_rekap_ketidakhadiran_pegawai()

@main.route('/laporan/rekap-ketidakhadiran-pegawai/export', methods=['POST'])
@login_required
def export_laporan_rekap_ketidakhadiran_pegawai():
    return export_rekap_ketidakhadiran_pegawai()

@main.route('/laporan/rekap-pelanggaran-disiplin')
@login_required
def view_laporan_rekap_pelanggaran_disiplin():
    return laporan_rekap_pelanggaran_disiplin()

@main.route('/laporan/rekap-pelanggaran-disiplin/export', methods=['POST'])
@login_required
def export_laporan_rekap_pelanggaran_disiplin():
    return export_rekap_pelanggaran_disiplin()

@main.route('/laporan/rekap-uang-makan')
@login_required
def view_laporan_rekap_uang_makan():
    return laporan_rekap_uang_makan()

@main.route('/laporan/rekap-uang-makan/export', methods=['POST'])
@login_required
def export_laporan_rekap_uang_makan():
    return export_rekap_uang_makan()

@main.route('/laporan/rekap-tunjangan-kinerja')
@login_required
def view_laporan_rekap_tunjangan_kinerja():
    return laporan_rekap_tunjangan_kinerja()

@main.route('/laporan/rekap-tunjangan-kinerja/export', methods=['POST'])
@login_required
def export_laporan_rekap_tunjangan_kinerja():
    return export_rekap_tunjangan_kinerja()

# Data Absensi :
@main.route('/data-absensi/non-finger')
@login_required
def view_data_absensi_non_finger():
    return data_absensi_non_finger()

@main.route('/api/absensi-non-finger/search')
@login_required
def api_absensi_non_finger_search():
    return data_absensi_api_non_finger_search()

@main.route('/api/absensi-non-finger/koreksi', methods=['POST'])
@login_required
def api_absensi_non_finger_koreksi():
    return data_absensi_api_non_finger_koreksi()

@main.route('/api/absensi-non-finger/save', methods=['POST'])
@login_required
def api_absensi_non_finger_save():
    return data_absensi_api_non_finger_save()

@main.route('/api/absensi-non-finger/delete', methods=['POST'])
@login_required
def api_absensi_non_finger_delete():
    return data_absensi_api_non_finger_delete()

@main.route('/api/absensi-non-finger/search-pegawai')
@login_required
def api_absensi_non_finger_search_pegawai():
    return data_absensi_api_search_pegawai()

@main.route('/data-absensi/normalisasi-finger')
@login_required
def view_data_absensi_normalisasi_finger():
    return data_absensi_normalisasi_finger()

@main.route('/data-absensi/impor-file')
@login_required
def view_data_absensi_impor_file():
    return data_absensi_impor_file()

@main.route('/api/normalisasi/fields', methods=['GET'])
@login_required
def api_normalisasi_fields():
    return data_absensi_api_normalisasi_fields()

@main.route('/api/normalisasi/import-finger', methods=['GET'])
@login_required
def api_normalisasi_import_finger():
    return data_absensi_api_normalisasi_import()

@main.route('/api/normalisasi/upload-dat', methods=['POST'])
@login_required
def api_normalisasi_upload_dat():
    return data_absensi_api_normalisasi_upload_dat()

@main.route('/api/normalisasi/commit-dat', methods=['POST'])
@login_required
def api_normalisasi_commit_dat():
    return data_absensi_api_normalisasi_commit_dat()

@main.route('/api/normalisasi/process', methods=['POST'])
@login_required
def api_normalisasi_process():
    return data_absensi_api_normalisasi_process()

@main.route('/api/normalisasi/export', methods=['POST'])
@login_required
def api_normalisasi_export():
    return data_absensi_api_normalisasi_export()

@main.route('/api/normalisasi/absensi-view', methods=['GET'])
@login_required
def api_normalisasi_absensi_view():
    return data_absensi_api_normalisasi_absensi_view()

@main.route('/api/normalisasi/closing', methods=['GET'])
@login_required
def api_normalisasi_closing_get():
    return data_absensi_api_closing_get()

@main.route('/api/normalisasi/closing', methods=['POST'])
@login_required
def api_normalisasi_closing_save():
    return data_absensi_api_closing_save()

@main.route('/data-absensi/pegawai-manual')
@login_required
def view_data_absensi_pegawai_manual():
    return data_absensi_pegawai_manual()

@main.route('/api/inject-absensi/pegawai')
@login_required
def api_inject_absensi_pegawai():
    return data_absensi_api_inject_pegawai()

@main.route('/api/inject-absensi/acak-jam', methods=['POST'])
@login_required
def api_inject_absensi_acak_jam():
    return data_absensi_api_acak_jam()

@main.route('/api/inject-absensi/save', methods=['POST'])
@login_required
def api_inject_absensi_save():
    return data_absensi_api_save()

@main.route('/data-absensi/pegawai-lembur-manual')
@login_required
def view_data_absensi_pegawai_lembur_manual():
    return data_absensi_pegawai_lembur_manual()

@main.route('/data-absensi/trace-tunjangan')
@login_required
def view_data_absensi_trace_tunjangan():
    return data_absensi_trace_tunjangan()

@main.route('/api/trace-tunjangan')
@login_required
def api_trace_tunjangan():
    return data_absensi_api_trace_tunjangan()

@main.route('/data-absensi/trace')
@login_required
def view_data_absensi_trace():
    return data_absensi_trace()

@main.route('/api/trace-absensi')
@login_required
def api_trace_absensi():
    return data_absensi_api_trace_absensi()

# Cari Absensi :
@main.route('/data-absensi/cari/non-finger')
@login_required
def view_cari_absensi_non_finger():
    return cari_absensi_non_finger()

@main.route('/api/cari-absensi-non-finger')
@login_required
def api_cari_absensi_non_finger():
    return data_absensi_api_cari_non_finger()

@main.route('/data-absensi/cari/normalisasi-finger')
@login_required
def view_cari_absensi_normalisasi_finger():
    return cari_absensi_normalisasi_finger()

@main.route('/api/cari-absensi-normalisasi-finger')
@login_required
def api_cari_absensi_normalisasi_finger():
    return data_absensi_api_cari_normalisasi_finger()

@main.route('/data-absensi/cari/pegawai-manual')
@login_required
def view_cari_absensi_pegawai_manual():
    return cari_absensi_pegawai_manual()

@main.route('/api/cari-absensi-manual')
@login_required
def api_cari_absensi_manual():
    return data_absensi_api_cari_manual()

@main.route('/api/cari-absensi-manual/delete', methods=['POST'])
@login_required
def api_cari_absensi_manual_delete():
    return data_absensi_api_cari_delete()

@main.route('/api/cari-absensi-manual/update', methods=['POST'])
@login_required
def api_cari_absensi_manual_update():
    return data_absensi_api_cari_update()

@main.route('/data-absensi/cari/pegawai-lembur-manual')
@login_required
def view_cari_absensi_pegawai_lembur_manual():
    return cari_absensi_pegawai_lembur_manual()

@main.route('/api/inject-lembur/pegawai')
@login_required
def api_inject_lembur_pegawai():
    return data_absensi_api_inject_lembur_pegawai()

@main.route('/api/inject-lembur/acak-jam', methods=['POST'])
@login_required
def api_inject_lembur_acak_jam():
    return data_absensi_api_inject_lembur_acak()

@main.route('/api/inject-lembur/save', methods=['POST'])
@login_required
def api_inject_lembur_save():
    return data_absensi_api_inject_lembur_save()

@main.route('/api/cari-lembur-manual')
@login_required
def api_cari_lembur_manual():
    return data_absensi_api_cari_lembur()

@main.route('/api/cari-lembur-manual/delete', methods=['POST'])
@login_required
def api_cari_lembur_manual_delete():
    return data_absensi_api_cari_lembur_delete()

@main.route('/api/cari-lembur-manual/update', methods=['POST'])
@login_required
def api_cari_lembur_manual_update():
    return data_absensi_api_cari_lembur_update()

# ============================
# ---- Dashboard 2 Routes ----
# ============================
# Dashboard Tim Siaga:
@main.route('/siaga/dashboard-tim-siaga')
@login_required
def view_dashboard_tim_siaga():
    return dashboard_tim_siaga()

# Data Siaga:
@main.route('/siaga/absensi-kehadiran')
@login_required
def view_data_siaga_absensi_kehadiran():
    return data_siaga_absensi_kehadiran()

@main.route('/api/absensi-kehadiran/get')
@login_required
def api_absensi_kehadiran_get():
    return data_siaga_api_absensi_kehadiran_get()

@main.route('/api/absensi-kehadiran/update', methods=['POST'])
@login_required
def api_absensi_kehadiran_update():
    return data_siaga_api_absensi_kehadiran_update()

@main.route('/siaga/cetak-daftar-lembur')
@login_required
def view_data_siaga_cetak_daftar_lembur_siaga():
    return data_siaga_cetak_daftar_lembur_siaga()

@main.route('/siaga/cetak-rekap')
@login_required
def view_data_siaga_cetak_rekap_siaga():
    return data_siaga_cetak_rekap_siaga()

@main.route('/siaga/cetak-uang-siaga')
@login_required
def view_data_siaga_cetak_uang_siaga():
    return data_siaga_cetak_uang_siaga()

@main.route('/siaga/jadwal-ulang')
@login_required
def view_data_siaga_jadwal_ulang():
    return data_siaga_jadwal_ulang()

@main.route('/api/rejadwal-siaga/get-jadwal')
@login_required
def api_rejadwal_siaga_get_jadwal():
    from app.controllers.dashboard_2DataSiagaController import api_rejadwal_siaga_get_jadwal
    return api_rejadwal_siaga_get_jadwal()

@main.route('/api/rejadwal-siaga/delete-personil', methods=['POST'])
@login_required
def api_rejadwal_siaga_delete_personil():
    from app.controllers.dashboard_2DataSiagaController import api_rejadwal_siaga_delete_personil
    return api_rejadwal_siaga_delete_personil()

@main.route('/api/rejadwal-siaga/cancel-request', methods=['POST'])
@login_required
def api_rejadwal_siaga_cancel_request():
    from app.controllers.dashboard_2DataSiagaController import api_rejadwal_siaga_cancel_request
    return api_rejadwal_siaga_cancel_request()

@main.route('/api/rejadwal-siaga/rollback', methods=['POST'])
@login_required
def api_rejadwal_siaga_rollback():
    from app.controllers.dashboard_2DataSiagaController import api_rejadwal_siaga_rollback
    return api_rejadwal_siaga_rollback()

@main.route('/api/rejadwal-siaga/fungsional')
@login_required
def api_rejadwal_siaga_get_fungsional():
    from app.controllers.dashboard_2DataSiagaController import api_rejadwal_siaga_get_fungsional
    return api_rejadwal_siaga_get_fungsional()

@main.route('/api/rejadwal-siaga/shift')
@login_required
def api_rejadwal_siaga_get_shift():
    from app.controllers.dashboard_2DataSiagaController import api_rejadwal_siaga_get_shift
    return api_rejadwal_siaga_get_shift()

@main.route('/api/rejadwal-siaga/add-personil', methods=['POST'])
def api_rejadwal_siaga_add_personil():
    from app.controllers.dashboard_2DataSiagaController import api_rejadwal_siaga_add_personil
    return api_rejadwal_siaga_add_personil()

@main.route('/siaga/buat-jadwal-piket')
@login_required
def view_data_siaga_membuat_jadwal_piket_siaga():
    return data_siaga_membuat_jadwal_piket_siaga()

# Master Data:
@main.route('/siaga/master-data/email-broadcast')
@login_required
def view_master_data_email_broadcast():
    return master_data_email_broadcast()

@main.route('/api/email-broadcast/get')
@login_required
def api_email_broadcast_get():
    return master_data_api_email_broadcast_get()

@main.route('/api/email-broadcast/save', methods=['POST'])
@login_required
def api_email_broadcast_save():
    return master_data_api_email_broadcast_save()

@main.route('/siaga/master-data/kgr')
@login_required
def view_master_data_kgr():
    return master_data_kgr()

@main.route('/api/kgr/search-pegawai')
@login_required
def api_kgr_search_pegawai():
    return master_data_api_kgr_search_pegawai()

@main.route('/api/kgr/get-shift')
@login_required
def api_kgr_get_shift():
    return master_data_api_kgr_get_shift()

@main.route('/api/kgr/save', methods=['POST'])
@login_required
def api_kgr_save():
    return master_data_api_kgr_save()

@main.route('/api/kgr/delete', methods=['POST'])
@login_required
def api_kgr_delete():
    return master_data_api_kgr_delete()

@main.route('/api/kgr/get')
@login_required
def api_kgr_get():
    return master_data_api_kgr_get()

@main.route('/api/kgr/save-as', methods=['POST'])
@login_required
def api_kgr_save_as():
    return master_data_api_kgr_save_as()

@main.route('/api/kgr/cari')
@login_required
def api_kgr_cari():
    return master_data_api_kgr_cari()

@main.route('/siaga/master-data/nominal-ut-piket')
@login_required
def view_master_data_nominal_ut_piket():
    return master_data_nominal_ut_piket()

@main.route('/siaga/master-data/tim-siaga')
@login_required
def view_master_data_tim_siaga():
    return master_data_tim_siaga()

@main.route('/api/tim-siaga/search-pegawai')
@login_required
def api_tim_siaga_search_pegawai():
    return master_data_api_search_pegawai_tim()

@main.route('/api/tim-siaga/save', methods=['POST'])
@login_required
def api_tim_siaga_save():
    return master_data_api_tim_siaga_save()

@main.route('/api/tim-siaga/delete', methods=['POST'])
@login_required
def api_tim_siaga_delete():
    return master_data_api_tim_siaga_delete()

@main.route('/api/tim-siaga/get')
@login_required
def api_tim_siaga_get():
    return master_data_api_tim_siaga_get()

@main.route('/api/tim-siaga/save-as', methods=['POST'])
@login_required
def api_tim_siaga_save_as():
    return master_data_api_tim_siaga_save_as()

@main.route('/siaga/master-data/user-account')
@login_required
def view_master_data_user_account():
    return master_data_user_account()

# Cari Data:
@main.route('/siaga/master-data/kgr/cari')
@login_required
def view_cari_data_kgr():
    return master_data_cari_kgr()

@main.route('/api/kgr/get-filter-fields')
@login_required
def api_kgr_get_filter_fields():
    return master_data_api_kgr_get_filter_fields()

@main.route('/siaga/master-data/piket-siaga/cari')
@login_required
def view_cari_data_piket_siaga():
    return master_data_cari_piket_siaga()

@main.route('/siaga/master-data/piket-tim-siaga/cari')
@login_required
def view_cari_data_piket_tim_siaga():
    return master_data_cari_piket_tim_siaga()

@main.route('/siaga/master-data/tim-siaga/cari')
@login_required
def view_cari_data_tim_siaga():
    return master_data_cari_tim_siaga()

# API Cari Tim Siaga:
@main.route('/api/cari-tim-siaga')
@login_required
def api_cari_tim_siaga():
    return master_data_api_cari_tim_siaga()

@main.route('/api/cari-tim-siaga/get')
@login_required
def api_cari_tim_siaga_get():
    return master_data_api_cari_tim_siaga_get()

# Otorisasi Persetujuan:
@main.route('/siaga/otorisasi/kepala-kantor')
@login_required
def view_otorisasi_persetujuan_kepala_kantor():
    return otorisasi_persetujuan_kepala_kantor()

@main.route('/siaga/otorisasi/kepala-seksi-operasi')
@login_required
def view_otorisasi_persetujuan_kepala_seksi_operasi():
    return otorisasi_persetujuan_kepala_seksi_operasi()

@main.route('/api/otorisasi/kasiops/belum')
@login_required
def api_route_otorisasi_kasiops_belum():
    return api_otorisasi_kasiops_belum()

@main.route('/api/otorisasi/kasiops/approve', methods=['POST'])
@login_required
def api_route_otorisasi_kasiops_approve():
    return api_otorisasi_kasiops_approve()

@main.route('/api/otorisasi/kasiops/sudah')
@login_required
def api_route_otorisasi_kasiops_sudah():
    return api_otorisasi_kasiops_sudah()

@main.route('/api/otorisasi/kasiops/undo', methods=['POST'])
@login_required
def api_route_otorisasi_kasiops_undo():
    return api_otorisasi_kasiops_undo()

@main.route('/api/otorisasi/kasiops/filter-fields')
@login_required
def api_route_otorisasi_kasiops_filter_fields():
    return api_otorisasi_kasiops_filter_fields()

@main.route('/api/otorisasi/kakansar/belum')
@login_required
def api_route_otorisasi_kakansar_belum():
    return api_otorisasi_kakansar_belum()

@main.route('/api/otorisasi/kakansar/approve', methods=['POST'])
@login_required
def api_route_otorisasi_kakansar_approve():
    return api_otorisasi_kakansar_approve()

@main.route('/api/otorisasi/kakansar/sudah')
@login_required
def api_route_otorisasi_kakansar_sudah():
    return api_otorisasi_kakansar_sudah()

@main.route('/api/otorisasi/kakansar/undo', methods=['POST'])
@login_required
def api_route_otorisasi_kakansar_undo():
    return api_otorisasi_kakansar_undo()

@main.route('/api/otorisasi/kakansar/filter-fields')
@login_required
def api_route_otorisasi_kakansar_filter_fields():
    return api_otorisasi_kakansar_filter_fields()

@main.route('/api/otorisasi/export/excel')
@login_required
def api_otorisasi_export_excel():
    from app.controllers.dashboard_2OtoritasPersetujuanController import export_otorisasi_excel
    return export_otorisasi_excel()

@main.route('/api/otorisasi/export/pdf')
@login_required
def api_otorisasi_export_pdf():
    from app.controllers.dashboard_2OtoritasPersetujuanController import export_otorisasi_pdf
    return export_otorisasi_pdf()

# ============================
# ---- Dashboard 3 Routes ----
# ============================
# Dashboard Kinerja:
@main.route('/kinerja/dashboard')
@login_required
def view_dashboard_kinerja():
    return dashboard_kinerja()

# Pengajuan:
@main.route('/kinerja/pengajuan/skp')
@login_required
def view_pengajuan_skp():
    return pengajuan_skp()

@main.route('/kinerja/pengajuan/absensi')
@login_required
def view_pengajuan_absensi():
    return pengajuan_absensi()

# Aktifitasku:
@main.route('/kinerja/aktifitasku/dashboard')
@login_required
def view_aktifitasku_dashboard():
    return aktifitasku_dashboard()

@main.route('/kinerja/aktifitasku/buku-harian')
@login_required
def view_aktifitasku_buku_harian():
    return aktifitasku_buku_harian()

@main.route('/kinerja/aktifitasku/buku-harian/baru/utama')
@login_required
def view_aktifitasku_buku_harian_baru_utama():
    return aktifitasku_buku_harian_baru_utama()

@main.route('/kinerja/aktifitasku/buku-harian/baru/tambahan')
@login_required
def view_aktifitasku_buku_harian_baru_tambahan():
    return aktifitasku_buku_harian_baru_tambahan()

@main.route('/kinerja/aktifitasku/buku-harian/baru/penunjang')
@login_required
def view_aktifitasku_buku_harian_baru_penunjang():
    return aktifitasku_buku_harian_baru_penunjang()

@main.route('/kinerja/aktifitasku/dupak')
@login_required
def view_aktifitasku_dupak():
    return aktifitasku_dupak()

@main.route('/kinerja/aktifitasku/skp')
@login_required
def view_aktifitasku_skp():
    return aktifitasku_skp()

@main.route('/kinerja/aktifitasku/jadwal-piket')
@login_required
def view_aktifitasku_jadwal_piket():
    return aktifitasku_jadwal_piket()

@main.route('/kinerja/aktifitasku/dinas-luar')
@login_required
def view_aktifitasku_dinas_luar():
    return aktifitasku_dinas_luar()

@main.route('/kinerja/aktifitasku/update-pendukung')
@login_required
def view_aktifitasku_update_pendukung():
    return aktifitasku_update_pendukung()

# Benefit:
@main.route('/kinerja/benefit/tunjangan-kinerja')
@login_required
def view_benefit_tunjangan_kinerja():
    return benefit_tunjangan_kinerja()

@main.route('/kinerja/benefit/rekap-uang-makan')
@login_required
def view_benefit_rekap_uang_makan():
    return benefit_rekap_uang_makan()

# Approval:
@main.route('/kinerja/approval/need-approval')
@login_required
def view_approved_request():
    return approved_request()

@main.route('/kinerja/approval/has-been-approved')
@login_required
def view_approval_approved():
    return approval_approved()

# Profile:
@main.route('/kinerja/profile')
@login_required
def view_profile():
    return profile()

# Kirim:
@main.route('/kinerja/kirim/kritik-saran')
@login_required
def view_kirim_kritik_saran():
    return kirim_kritik_saran()

@main.route('/kinerja/kirim/forum-media-informasi')
@login_required
def view_kirim_forum_media_informasi():
    return kirim_forum_media_informasi()