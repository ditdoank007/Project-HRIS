# app/routes/routes.py

from flask import Blueprint, jsonify, render_template, redirect, url_for
from app.utils.decorators import login_required, admin_required, form_access_required
from app.controllers.homeController import (
    get_pelanggaran_disiplin,
    get_piket_siaga,
    home,
    search_buku_telp,
    search_pegawai_autocomplete,
)
from app.controllers.loginController import login, logout, sso_callback
from app.controllers.absenOnlineController import (
    status_absen_online,
    punch_absen_online,
)
from app.controllers.dashboard_1HomeController import (
    dashboard_kgb, dashboard_pangkat, dashboard_pelanggaran, dashboard_pensiun, dashboard_trt,
    api_calendar_pelanggaran_internal)
from app.controllers.dashboard_1MasterFileController import (
    get_google_calendar_config, save_google_calendar_config,
    test_google_calendar_connection,
    create_kalender_tahun, export_jam_finger_excel, export_tunjangan_excel, get_jabatan_list, get_jam_finger_list, get_jam_kerja_list, get_joblist_list, get_kalender_list, save_kalender_changes,
    get_pegawai_vip_list, get_potongan_list, get_potongan_detail, get_tunjangan_list, get_unit_kerja_detail, get_tunkin_class_detail, get_tunkin_class_list,
    delete_user_account, get_unit_kerja_list, get_user_account_detail, get_user_account_list, master_butir_kegiatan, master_jabatan, master_jam_finger, master_jam_kerja,
    master_kalender, master_pegawai_vip, master_potongan, master_trt as master_file_trt, master_tunkin_class,
    master_unit_kerja, toggle_unit_kerja, master_user, master_uang_makan, cari_master_pegawai_vip, cari_master_jabatan, cari_master_jam_finger, cari_master_jam_kerja,
    cari_master_kalender, cari_master_potongan, cari_master_tunkin_class, cari_master_uang_makan, cari_master_unit_kerja,
    cari_user_account, create_kalender, save_jabatan, save_jam_kerja, save_joblist, save_potongan, save_tunkin_class, save_uang_makan, save_unit_kerja, save_user_account,
    toggle_pegawai_vip, save_pegawai_vip, save_jam_finger, update_potongan, delete_potongan, update_unit_kerja,
    get_jam_kerja_by_id, update_jam_kerja, delete_jam_kerja,
    get_auth_config, save_auth_config, api_user_account_pegawai_search,
    get_jam_finger_by_id, update_jam_finger, delete_jam_finger,
    get_jabatan_by_id, get_jabatan_structure, update_jabatan, delete_jabatan,
)
from app.controllers.dashboard_1InfografisController import dashboard_infografis
from app.controllers.dashboard_1StrukturOrganisasiController import dashboard_struktur_organisasi, api_calendar_struktur_organisasi_internal
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
    api_pegawai_bdip as master_api_pegawai_bdip,
    api_dinas_luar_search_pegawai as master_api_dinas_luar_search_pegawai,
    api_dinas_luar_save as master_api_dinas_luar_save,
    api_dinas_luar_get as master_api_dinas_luar_get,
    api_dinas_luar_delete as master_api_dinas_luar_delete,
    api_dinas_luar_pdf,
    api_sprin_header_save as master_api_sprin_header_save,
    api_dinas_luar_save_peserta as master_api_dinas_luar_save_peserta,
    api_dinas_luar_cari as master_api_dinas_luar_cari,
    api_dinas_luar_get_filter_fields as master_api_dinas_luar_get_filter_fields,
    api_sakit_get_jenis as master_api_sakit_get_jenis,
    api_sakit_cari as master_api_sakit_cari,
    api_ijin_cari as master_api_ijin_cari,
)
from app.controllers.backupRestoreController import (
    backup_restore_home,
    backup_mariadb_home,
    restore_mariadb_home,
    import_mssql_home,
    api_backup_mariadb,
    api_backup_mariadb_list,
    api_restore_mariadb,
    api_import_mssql_upload,
    api_import_mssql_preview,
    api_import_mssql_execute,
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
    export_rekap_absensi_all_pdf,
    export_rekap_absensi_individu,
    export_rekap_absensi_log_finger,
    export_rekap_clock_exception,
    export_rekap_clock_exception_pdf,
    preview_rekap_clock_exception,
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

from app.controllers.calendarController import (
    api_calendar_personal,
    api_calendar_personal_sync_token,
    api_calendar_sync_token_internal,
    api_calendar_employee_profile_internal,
    api_calendar_infografis_internal,
    api_calendar_my_agenda,
    api_calendar_conflict,
    api_calendar_create_event,
    api_calendar_feed,
    api_calendar_user_agenda,
    api_calendar_category,
    api_calendar_agenda_rapat_internal,
    api_calendar_my_agenda_internal,
    api_calendar_agenda_rapat_notulen_internal,
)

from app.controllers.benefitController import (
    api_calendar_benefit_tunjangan_kinerja_internal,
    api_calendar_benefit_uang_makan_internal,
    api_calendar_benefit_uang_siaga_internal,
)
from app.controllers.uangSiagaV2Controller import (
    api_calendar_benefit_uang_siaga_v2_internal,
)

from app.controllers.calendarAttendanceController import (
    api_calendar_rapat_attendance_info,
    api_calendar_rapat_employee_attendance,
    api_calendar_rapat_guest_attendance,
)

from app.controllers.dashboard_1AgendaController import (
    agenda_rapat, api_agenda_rapat_list, api_agenda_rapat_save,
    api_agenda_rapat_detail, api_agenda_rapat_update,
    api_agenda_rapat_cancel, api_agenda_rapat_complete, api_agenda_rapat_qr,
    api_agenda_rapat_scan, api_agenda_rapat_attendance, api_agenda_rapat_daftar_hadir_pdf,
    api_pegawai_agenda_search, api_agenda_rapat_notulen_upload,
    api_agenda_rapat_notulen_download,
)
from app.controllers.kesamaptaanController import (
    kesamaptaan, api_kesamaptaan_list, api_kesamaptaan_save,
    api_kesamaptaan_detail, api_kesamaptaan_update, api_kesamaptaan_cancel,
    api_kesamaptaan_complete, api_kesamaptaan_qr, api_kesamaptaan_attendance,
    api_kesamaptaan_photos, api_kesamaptaan_pdf, api_kesamaptaan_signature,
    api_kesamaptaan_internal_info, api_kesamaptaan_internal_employee_attendance,
    api_kesamaptaan_internal_agenda, api_kesamaptaan_internal_pdf,
)
from app.controllers.dashboard_1DisposisiController import (
    agenda_disposisi, api_agenda_disposisi_list, api_agenda_disposisi_save,
    api_agenda_disposisi_detail, api_agenda_disposisi_cancel,
)
from app.controllers.rekamMedisKegiatanController import (
    rekam_medis_pegawai, rekam_medis_non_pegawai,
    api_rekam_medis_kegiatan_pegawai_list, api_rekam_medis_kegiatan_non_pegawai_list,
    api_rekam_medis_kegiatan_pegawai_save, api_rekam_medis_kegiatan_non_pegawai_save,
    api_rekam_medis_kegiatan_pegawai_detail, api_rekam_medis_kegiatan_non_pegawai_detail,
    api_rekam_medis_kegiatan_pegawai_update, api_rekam_medis_kegiatan_non_pegawai_update,
    api_rekam_medis_kegiatan_pegawai_cancel, api_rekam_medis_kegiatan_non_pegawai_cancel,
    api_rekam_medis_kegiatan_pegawai_complete, api_rekam_medis_kegiatan_non_pegawai_complete,
    api_rekam_medis_kegiatan_pegawai_qr, api_rekam_medis_kegiatan_non_pegawai_qr,
    api_rekam_medis_scan, api_rekam_medis_petugas_search,
    api_calendar_rekam_medis_info, api_calendar_rekam_medis_employee,
    api_calendar_rekam_medis_guest,
    api_rekam_medis_kegiatan_pegawai_peserta_detail,
    api_rekam_medis_kegiatan_non_pegawai_peserta_detail,
    api_rekam_medis_kegiatan_pegawai_peserta_save,
    api_rekam_medis_kegiatan_non_pegawai_peserta_save,
    api_rekam_medis_kegiatan_pegawai_export_excel,
    api_rekam_medis_kegiatan_pegawai_export_pdf,
)
from app.controllers.rekamMedisController import (
    rekam_medis, api_rekam_medis_search_pegawai, api_rekam_medis_save,
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
    api_absensi_non_finger_edit as data_absensi_api_non_finger_edit,
    api_search_pegawai_non_finger as data_absensi_api_search_pegawai,
    api_cari_absensi_non_finger as data_absensi_api_cari_non_finger,
    api_normalisasi_get_fields as data_absensi_api_normalisasi_fields,
    api_normalisasi_import_finger as data_absensi_api_normalisasi_import,
    api_normalisasi_process as data_absensi_api_normalisasi_process,
    api_normalisasi_legacy_test as data_absensi_api_normalisasi_legacy_test,
    api_normalisasi_upload_dat as data_absensi_api_normalisasi_upload_dat,
    api_normalisasi_commit_dat as data_absensi_api_normalisasi_commit_dat,
    api_normalisasi_export as data_absensi_api_normalisasi_export,
    api_normalisasi_download_excel as data_absensi_api_normalisasi_download_excel,
    api_normalisasi_download_pdf as data_absensi_api_normalisasi_download_pdf,
    api_normalisasi_absensi_view as data_absensi_api_normalisasi_absensi_view,
    api_closing_get as data_absensi_api_closing_get,
    api_closing_save as data_absensi_api_closing_save,
    api_cari_absensi_normalisasi_finger as data_absensi_api_cari_normalisasi_finger,
)
from app.controllers.dashboard_2DataSiagaController import (
    data_siaga_absensi_kehadiran, data_siaga_cetak_daftar_lembur_siaga, data_siaga_cetak_rekap_siaga,
    data_siaga_cetak_uang_siaga, data_siaga_jadwal_ulang, data_siaga_membuat_jadwal_piket_siaga,
    data_siaga_view_jadwal,
    api_absensi_kehadiran_get as data_siaga_api_absensi_kehadiran_get,
    api_absensi_kehadiran_update as data_siaga_api_absensi_kehadiran_update,
    api_absensi_kehadiran_export_pdf as data_siaga_api_absensi_kehadiran_export_pdf,
    api_absensi_kehadiran_save_pdf as data_siaga_api_absensi_kehadiran_save_pdf,
    api_absensi_kehadiran_internal_pdf as data_siaga_api_absensi_kehadiran_internal_pdf,
    api_pembuatan_jadwal_siaga_save as data_siaga_api_pembuatan_jadwal_siaga_save,
    api_siaga_view_jadwal_edit as data_siaga_api_view_jadwal_edit,
    api_siaga_view_jadwal_lengkapi_shift2 as data_siaga_api_view_jadwal_lengkapi_shift2,
    api_siaga_view_jadwal_get as data_siaga_api_view_jadwal_get,
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
    api_jabatan_siaga_get as master_data_api_jabatan_siaga_get,
    api_jabatan_siaga_save as master_data_api_jabatan_siaga_save,
    api_jabatan_siaga_deactivate as master_data_api_jabatan_siaga_deactivate
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
from app.controllers.dashboard4HomeController import dashboard4, has_any_agenda_access
from app.controllers.dashboard_3PengajuanController import (
    pengajuan_skp,
    pengajuan_absensi,
)
from app.models.pegawaiModel import Pegawai
from app.controllers.dashboard_1MasterFileController import get_uang_makan_detail, update_uang_makan, delete_uang_makan

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return home()

@main.route('/api/search_pegawai')
def api_search_pegawai():
    return search_pegawai_autocomplete()

@main.route('/api/piket_siaga')
def api_piket_siaga():
    return get_piket_siaga()

@main.route('/api/pelanggaran_disiplin')
def api_pelanggaran_disiplin():
    return get_pelanggaran_disiplin()

@main.route('/api/login', methods=['POST'])
def api_login():
    return login()

@main.route('/api/login/sso', methods=['GET'])
def api_login_sso():
    return sso_callback()

@main.route('/api/logout', methods=['POST'])
def api_logout():
    return logout()


@main.route('/api/absen-online/status', methods=['GET'])
def api_absen_online_status():
    return status_absen_online()


@main.route('/api/absen-online/punch', methods=['POST'])
def api_absen_online_punch():
    return punch_absen_online()

@main.route('/api/pegawai/preview', methods=['GET'])
def preview_pegawai():
    data = Pegawai.query.order_by(Pegawai.NIP.asc()).limit(20).all()
    return jsonify({
        'count': len(data),
        'data': [pegawai.to_dict() for pegawai in data]
    })


# ============================================================
# BACKUP / RESTORE
# Administrator only
# ============================================================

@main.route('/backup-restore')
@login_required
def view_backup_restore():
    return backup_restore_home()

@main.route('/backup-restore/backup-mariadb')
@login_required
def view_backup_mariadb():
    return backup_mariadb_home()

@main.route('/backup-restore/restore-mariadb')
@login_required
def view_restore_mariadb():
    return restore_mariadb_home()

@main.route('/backup-restore/import-mssql-2013')
@login_required
def view_import_mssql_2013():
    return import_mssql_home()


@main.route('/api/backup-mariadb', methods=['POST'])
@login_required
def api_backup_mariadb_route():
    return api_backup_mariadb()


@main.route('/api/backup-mariadb/list', methods=['GET'])
@login_required
def api_backup_mariadb_list_route():
    return api_backup_mariadb_list()


@main.route('/api/restore-mariadb', methods=['POST'])
@login_required
def api_restore_mariadb_route():
    return api_restore_mariadb()


@main.route('/api/import-mssql-2013/upload', methods=['POST'])
@login_required
def api_import_mssql_upload_route():
    return api_import_mssql_upload()


@main.route('/api/import-mssql-2013/preview', methods=['POST'])
@login_required
def api_import_mssql_preview_route():
    return api_import_mssql_preview()


@main.route('/api/import-mssql-2013/execute', methods=['POST'])
@login_required
def api_import_mssql_execute_route():
    return api_import_mssql_execute()


# ============================
# ---- Dashboard 1 Routes ----
# ============================
# Dasboard :
@main.route('/dashboard/infografis')
@login_required
def view_dashboard_infografis():
    return dashboard_infografis()

@main.route('/dashboard/struktur-organisasi')
@login_required
def view_dashboard_struktur_organisasi():
    return dashboard_struktur_organisasi()

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

@main.route('/api/pegawai/bdip')
@login_required
def api_pegawai_bdip():
    return master_api_pegawai_bdip()

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


@main.route('/api/dinas-luar/pdf')
@login_required
def api_dinas_luar_pdf_route():
    return api_dinas_luar_pdf()


@main.route('/api/internal/calendar/dinas-luar/pdf')
def api_calendar_dinas_luar_pdf_internal_route():
    return api_dinas_luar_pdf()


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
    return master_api_dinas_luar_save('OP')

# API: Get Dinas Luar Operasi by No Surat
@main.route('/api/dinas-luar-operasi/get')
@login_required
def api_dinas_luar_operasi_get():
    return master_api_dinas_luar_get('OP')

# API: Delete Dinas Luar Operasi
@main.route('/api/dinas-luar-operasi/delete', methods=['POST'])
@login_required
def api_dinas_luar_operasi_delete():
    return master_api_dinas_luar_delete('OP')

@main.route('/api/dinas-luar-operasi/save-peserta', methods=['POST'])
@login_required
def api_dinas_luar_operasi_save_peserta():
    from app.controllers.dashboard_1KepegawaianController import api_dinas_luar_operasi_save_peserta as save_operation_participants
    return save_operation_participants()

@main.route('/kepegawaian/dinas-luar-pelatihan')
@login_required
def view_kepegawaian_dinas_luar_pelatihan():
    return kepegawaian_dinas_luar_pelatihan()

@main.route('/api/dinas-luar-pelatihan/save-peserta', methods=['POST'])
@login_required
def api_dinas_luar_pelatihan_save_peserta():
    return master_api_dinas_luar_save('PL')

@main.route('/api/dinas-luar-pelatihan/get')
@login_required
def api_dinas_luar_pelatihan_get():
    return master_api_dinas_luar_get('PL')

@main.route('/api/dinas-luar-pelatihan/delete', methods=['POST'])
@login_required
def api_dinas_luar_pelatihan_delete():
    return master_api_dinas_luar_delete('PL')

@main.route('/kepegawaian/pegawai-cuti')
@login_required
def view_kepegawaian_pegawai_cuti():
    return kepegawaian_pegawai_cuti()

@main.route('/kepegawaian/cari/pegawai-cuti')
@login_required
def view_kepegawaian_cari_pegawai_cuti():
    from app.controllers.dashboard_1KepegawaianController import (
        kepegawaian_cari_pegawai_cuti
    )
    return kepegawaian_cari_pegawai_cuti()


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


@main.route('/api/sakit/jenis')
@login_required
def api_sakit_get_jenis():
    return master_api_sakit_get_jenis()


@main.route('/api/sakit/cari')
@login_required
def api_sakit_cari():
    return master_api_sakit_cari()


@main.route('/kepegawaian/pegawai-tidak-hadir')
@login_required
def view_kepegawaian_pegawai_tidak_hadir():
    return kepegawaian_pegawai_tidak_hadir()


@main.route('/api/ijin/cari')
@login_required
def api_ijin_cari():
    return master_api_ijin_cari()


@main.route('/kepegawaian/mutasi-penempatan')
@login_required
def view_kepegawaian_mutasi_penempatan_pegawai():
    return kepegawaian_mutasi_penempatan_pegawai()

@main.route('/api/mutasi/unit-kerja')
@login_required
def api_mutasi_unit_kerja():
    from app.controllers.dashboard_1KepegawaianController import api_mutasi_unit_kerja
    return api_mutasi_unit_kerja()


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

@main.route('/api/update-pendukung/autocomplete')
@login_required
def api_update_pendukung_autocomplete():
    from app.controllers.dashboard_1KepegawaianController import api_update_pendukung_autocomplete
    return api_update_pendukung_autocomplete()


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

@main.route('/api/jabatan/detail', methods=['GET'])
@login_required
def api_jabatan_detail():
    return get_jabatan_by_id()

@main.route('/api/jabatan/structure', methods=['GET'])
@login_required
def api_jabatan_structure():
    return get_jabatan_structure()


@main.route('/api/jabatan/update', methods=['POST'])
@login_required
def api_jabatan_update():
    return update_jabatan()

@main.route('/api/jabatan/delete', methods=['POST'])
@login_required
def api_jabatan_delete():
    return delete_jabatan()

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

@main.route('/api/calendar/google-config', methods=['GET'])
@login_required
def api_google_calendar_config():
    return get_google_calendar_config()


@main.route('/api/calendar/google-config', methods=['POST'])
@login_required
def api_google_calendar_config_save():
    return save_google_calendar_config()

@main.route('/api/calendar/google-test', methods=['POST'])
@login_required
def api_google_calendar_test():
    return test_google_calendar_connection()


@main.route('/api/kalender/list', methods=['GET'])
@login_required
def api_kalender_list():
    return get_kalender_list()

@main.route('/api/kalender/generate', methods=['POST'])
@login_required
def api_kalender_generate():
    return create_kalender_tahun()


@main.route('/api/kalender/save', methods=['POST'])
@login_required
def api_kalender_save():
    return save_kalender_changes()

@main.route('/master/pegawai-vip')
@login_required
def view_master_pegawai_vip():
    return master_pegawai_vip()

@main.route('/master/pegawai-vip/cari')
@login_required
def view_cari_master_pegawai_vip():
    return cari_master_pegawai_vip()

@main.route('/api/pegawai-vip/list', methods=['GET'])
@login_required
def api_pegawai_vip_list():
    return get_pegawai_vip_list()

@main.route('/api/pegawai-vip/toggle', methods=['POST'])
@login_required
def api_pegawai_vip_toggle():
    return toggle_pegawai_vip()

@main.route('/api/pegawai-vip/save', methods=['POST'])
@login_required
def api_pegawai_vip_save():
    return save_pegawai_vip()



@main.route('/master/potongan')
@login_required
def view_master_potongan():
    return master_potongan()

@main.route('/api/potongan/save', methods=['POST'])
@login_required
def api_potongan_save():
    return save_potongan()

@main.route('/api/potongan/detail/<int:potongan_id>', methods=['GET'])
@login_required
def api_potongan_detail(potongan_id):
    return get_potongan_detail(potongan_id)

@main.route('/api/potongan/update/<int:potongan_id>', methods=['POST'])
@login_required
def api_potongan_update(potongan_id):
    return update_potongan(potongan_id)

@main.route('/api/potongan/delete/<int:potongan_id>', methods=['POST'])
@login_required
def api_potongan_delete(potongan_id):
    return delete_potongan(potongan_id)

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

@main.route('/api/unit-kerja/detail/<path:unit_kerja_id>', methods=['GET'])
@login_required
def api_unit_kerja_detail(unit_kerja_id):
    return get_unit_kerja_detail(unit_kerja_id)

@main.route('/api/unit-kerja/update/<path:unit_kerja_id>', methods=['POST'])
@login_required
def api_unit_kerja_update(unit_kerja_id):
    return update_unit_kerja(unit_kerja_id)

@main.route('/api/unit-kerja/toggle', methods=['POST'])
@login_required
def api_unit_kerja_toggle():
    return toggle_unit_kerja()


@main.route('/master/user')
@login_required
def view_master_user():
    return master_user()


@main.route('/master/login')
@admin_required
def view_master_login():
    return render_template(
        'pages/dashboard_1/Master Login.html'
    )


@main.route('/api/auth-config', methods=['GET'])
@admin_required
def api_auth_config():
    return get_auth_config()


@main.route('/api/auth-config/save', methods=['POST'])
@admin_required
def api_auth_config_save():
    return save_auth_config()

@main.route('/api/user-account/pegawai-search', methods=['GET'])
@login_required
def api_user_account_pegawai_search_route():
    return api_user_account_pegawai_search()

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

@main.route('/api/uang-makan/detail', methods=['GET'])
@login_required
def api_uang_makan_detail():
    return get_uang_makan_detail()

@main.route('/api/uang-makan/update', methods=['POST'])
@login_required
def api_uang_makan_update():
    return update_uang_makan()

@main.route('/api/uang-makan/delete', methods=['POST'])
@login_required
def api_uang_makan_delete():
    return delete_uang_makan()

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


@main.route('/api/jam-finger/detail', methods=['GET'])
@login_required
def api_jam_finger_detail():
    return get_jam_finger_by_id()


@main.route('/api/jam-finger/update', methods=['POST'])
@login_required
def api_jam_finger_update():
    return update_jam_finger()


@main.route('/api/jam-finger/delete', methods=['POST'])
@login_required
def api_jam_finger_delete():
    return delete_jam_finger()

@main.route('/master/cari/jam-kerja')
@login_required
def view_cari_master_jam_kerja():
    return cari_master_jam_kerja()

@main.route('/api/jam-kerja/list', methods=['GET'])
@login_required
def api_jam_kerja_list():
    return get_jam_kerja_list()

@main.route('/api/jam-kerja/detail', methods=['GET'])
@login_required
def api_jam_kerja_detail():
    return get_jam_kerja_by_id()

@main.route('/api/jam-kerja/update', methods=['POST'])
@login_required
def api_jam_kerja_update():
    return update_jam_kerja()

@main.route('/api/jam-kerja/delete', methods=['POST'])
@login_required
def api_jam_kerja_delete():
    return delete_jam_kerja()

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
@form_access_required('InpPengumuman.aspx')
def view_media_informasi():
    return media_informasi()

@main.route('/api/media-informasi', methods=['POST'])
@form_access_required('InpPengumuman.aspx')
def api_save_media_informasi():
    return save_media_informasi()

@main.route('/api/media-informasi/slide', methods=['POST'])
@form_access_required('InpPengumuman.aspx')
def api_save_media_informasi_slide():
    return save_media_informasi_slide()

@main.route('/api/media-informasi/list', methods=['GET'])
@form_access_required('InpPengumuman.aspx')
def api_get_media_informasi_list():
    return get_media_informasi_list()

@main.route('/api/media-informasi/<int:med_infor_id>', methods=['GET'])
@form_access_required('InpPengumuman.aspx')
def api_get_media_informasi_by_id(med_infor_id):
    return get_media_informasi_by_id(med_infor_id)

@main.route('/api/media-informasi/<int:med_infor_id>', methods=['PUT'])
@form_access_required('InpPengumuman.aspx')
def api_update_media_informasi(med_infor_id):
    return update_media_informasi(med_infor_id)

@main.route('/api/media-informasi/<int:med_infor_id>/nonaktif', methods=['POST'])
@form_access_required('InpPengumuman.aspx')
def api_nonaktifkan_media_informasi(med_infor_id):
    return nonaktifkan_media_informasi(med_infor_id)

@main.route('/media-informasi/detail')
@form_access_required('InpPengumuman.aspx')
def view_media_informasi_detail():
    return media_informasi_detail()

# Laporan Rekap :
@main.route('/laporan/cetak-daftar-lembur-umum')
@form_access_required('DaftarLembur.aspx')
def view_laporan_cetak_daftar_lembur_umum():
    return laporan_cetak_daftar_lembur_umum()

@main.route('/laporan/cetak-daftar-lembur-umum/export', methods=['POST'])
@form_access_required('DaftarLembur.aspx')
def export_laporan_cetak_daftar_lembur_umum():
    return export_rekap_daftar_lembur_umum()

@main.route('/laporan/cetak-daftar-lembur-umum/detail', methods=['POST'])
@form_access_required('DaftarLembur.aspx')
def export_laporan_detail_jam_lembur_umum():
    return export_detail_jam_lembur_umum()

@main.route('/laporan/rekap-absensi-all')
@form_access_required('RAbsensiAll.aspx')
def view_laporan_rekap_absensi_all():
    return laporan_rekap_absensi_all()

@main.route('/laporan/rekap-absensi-all/preview', methods=['POST'])
@form_access_required('RAbsensiAll.aspx')
def preview_laporan_rekap_absensi_all():
    return preview_rekap_absensi_all()

@main.route('/laporan/rekap-absensi-all/export', methods=['POST'])
@form_access_required('RAbsensiAll.aspx')
def export_laporan_rekap_absensi_all():
    return export_rekap_absensi_all()


@main.route(
    '/laporan/rekap-absensi-all/export-pdf',
    methods=['POST']
)
@form_access_required('RAbsensiAll.aspx')
def export_laporan_rekap_absensi_all_pdf():
    return export_rekap_absensi_all_pdf()

@main.route('/laporan/rekap-absensi-individu')
@form_access_required('RAbsensiPerson.aspx')
def view_laporan_rekap_absensi_individu():
    return laporan_rekap_absensi_individu()

@main.route('/laporan/rekap-absensi-individu/export', methods=['POST'])
@form_access_required('RAbsensiPerson.aspx')
def export_laporan_rekap_absensi_individu():
    return export_rekap_absensi_individu()

@main.route('/api/laporan/search-pegawai')
@form_access_required('RAbsensiPerson.aspx')
def api_laporan_search_pegawai():
    return search_pegawai_by_name()

@main.route('/api/laporan/rekap-uang-makan/search-pegawai')
@form_access_required('RekapUM.aspx')
def api_rekap_uang_makan_search_pegawai():
    return search_pegawai_by_name()

@main.route('/laporan/rekap-absensi-log-finger')
@form_access_required('RTimerecorder.aspx')
def view_laporan_rekap_absensi_log_finger():
    return laporan_rekap_absensi_log_finger()

@main.route('/laporan/rekap-absensi-log-finger/export', methods=['POST'])
@form_access_required('RTimerecorder.aspx')
def export_laporan_rekap_absensi_log_finger():
    return export_rekap_absensi_log_finger()

@main.route('/laporan/rekap-clock-exception')
@form_access_required('RDailyabsensi.aspx')
def view_laporan_rekap_clock_exception():
    return laporan_rekap_clock_exception()


@main.route(
    '/laporan/rekap-clock-exception/preview',
    methods=['POST']
)
@form_access_required('RDailyabsensi.aspx')
def preview_laporan_rekap_clock_exception():
    return preview_rekap_clock_exception()

@main.route('/laporan/rekap-clock-exception/export', methods=['POST'])
@form_access_required('RDailyabsensi.aspx')
def export_laporan_rekap_clock_exception():
    return export_rekap_clock_exception()

@main.route('/laporan/rekap-clock-exception/export-pdf', methods=['POST'])
@form_access_required('RDailyabsensi.aspx')
def export_laporan_rekap_clock_exception_pdf():
    return export_rekap_clock_exception_pdf()

@main.route('/laporan/rekap-ketidakhadiran-pegawai')
@form_access_required('Rekapsprint.aspx')
def view_laporan_rekap_ketidakhadiran_pegawai():
    return laporan_rekap_ketidakhadiran_pegawai()

@main.route('/laporan/rekap-ketidakhadiran-pegawai/export', methods=['POST'])
@form_access_required('Rekapsprint.aspx')
def export_laporan_rekap_ketidakhadiran_pegawai():
    return export_rekap_ketidakhadiran_pegawai()

@main.route('/laporan/rekap-pelanggaran-disiplin')
@form_access_required('RPelanggaranDis.aspx')
def view_laporan_rekap_pelanggaran_disiplin():
    return laporan_rekap_pelanggaran_disiplin()

@main.route('/laporan/rekap-pelanggaran-disiplin/export', methods=['POST'])
@form_access_required('RPelanggaranDis.aspx')
def export_laporan_rekap_pelanggaran_disiplin():
    return export_rekap_pelanggaran_disiplin()

@main.route('/laporan/rekap-uang-makan')
@form_access_required('RekapUM.aspx')
def view_laporan_rekap_uang_makan():
    return laporan_rekap_uang_makan()

@main.route('/laporan/rekap-uang-makan/preview', methods=['POST'])
@form_access_required('RekapUM.aspx')
def preview_laporan_rekap_uang_makan():
    return export_rekap_uang_makan(preview=True)


@main.route('/laporan/rekap-uang-makan/export', methods=['POST'])
@form_access_required('RekapUM.aspx')
def export_laporan_rekap_uang_makan():
    return export_rekap_uang_makan()


@main.route('/laporan/rekap-uang-makan/export/pdf', methods=['POST'])
@form_access_required('RekapUM.aspx')
def export_laporan_rekap_uang_makan_pdf():
    return export_rekap_uang_makan(pdf=True)

@main.route('/laporan/rekap-tunjangan-kinerja')
@form_access_required('RRincianBayar.aspx')
def view_laporan_rekap_tunjangan_kinerja():
    return laporan_rekap_tunjangan_kinerja()

@main.route('/laporan/rekap-tunjangan-kinerja/export', methods=['POST'])
@form_access_required('RRincianBayar.aspx')
def export_laporan_rekap_tunjangan_kinerja():
    return export_rekap_tunjangan_kinerja()

# Data Absensi :
@main.route('/data-absensi/non-finger')
@form_access_required('Absensimanual.aspx')
def view_data_absensi_non_finger():
    return data_absensi_non_finger()

@main.route('/api/absensi-non-finger/search')
@form_access_required('Absensimanual.aspx')
def api_absensi_non_finger_search():
    return data_absensi_api_non_finger_search()

@main.route('/api/absensi-non-finger/koreksi', methods=['POST'])
@form_access_required('Absensimanual.aspx')
def api_absensi_non_finger_koreksi():
    return data_absensi_api_non_finger_koreksi()

@main.route('/api/absensi-non-finger/save', methods=['POST'])
@form_access_required('Absensimanual.aspx')
def api_absensi_non_finger_save():
    return data_absensi_api_non_finger_save()

@main.route('/api/absensi-non-finger/delete', methods=['POST'])
@form_access_required('Absensimanual.aspx')
def api_absensi_non_finger_delete():
    return data_absensi_api_non_finger_delete()

@main.route('/api/absensi-non-finger/edit', methods=['POST'])
@form_access_required('Absensimanual.aspx')
def api_absensi_non_finger_edit():
    return data_absensi_api_non_finger_edit()

@main.route('/api/absensi-non-finger/search-pegawai')
@form_access_required('Absensimanual.aspx')
def api_absensi_non_finger_search_pegawai():
    return data_absensi_api_search_pegawai()

@main.route('/data-absensi/normalisasi-finger')
@form_access_required('AbsensiFP.aspx')
def view_data_absensi_normalisasi_finger():
    return data_absensi_normalisasi_finger()

@main.route('/data-absensi/impor-file')
@form_access_required('MFLoadFinger.aspx')
def view_data_absensi_impor_file():
    return data_absensi_impor_file()

@main.route('/api/normalisasi/fields', methods=['GET'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_fields():
    return data_absensi_api_normalisasi_fields()

@main.route('/api/normalisasi/import-finger', methods=['GET'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_import_finger():
    return data_absensi_api_normalisasi_import()

@main.route('/api/normalisasi/upload-dat', methods=['POST'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_upload_dat():
    return data_absensi_api_normalisasi_upload_dat()

@main.route('/api/normalisasi/commit-dat', methods=['POST'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_commit_dat():
    return data_absensi_api_normalisasi_commit_dat()

@main.route('/api/normalisasi/process', methods=['POST'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_process():
    return data_absensi_api_normalisasi_process()

@main.route('/api/normalisasi/legacy-test', methods=['POST'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_legacy_test():
    return data_absensi_api_normalisasi_legacy_test()

@main.route('/api/normalisasi/export', methods=['POST'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_export():
    return data_absensi_api_normalisasi_export()

@main.route('/api/normalisasi/download-excel', methods=['GET'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_download_excel():
    return data_absensi_api_normalisasi_download_excel()

@main.route('/api/normalisasi/download-pdf', methods=['GET'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_download_pdf():
    return data_absensi_api_normalisasi_download_pdf()

@main.route('/api/normalisasi/absensi-view', methods=['GET'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_absensi_view():
    return data_absensi_api_normalisasi_absensi_view()

@main.route('/api/normalisasi/closing', methods=['GET'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_closing_get():
    return data_absensi_api_closing_get()

@main.route('/api/normalisasi/closing', methods=['POST'])
@form_access_required('AbsensiFP.aspx')
def api_normalisasi_closing_save():
    return data_absensi_api_closing_save()

@main.route('/data-absensi/pegawai-manual')
@form_access_required('InjectAbsensi.aspx')
def view_data_absensi_pegawai_manual():
    return data_absensi_pegawai_manual()

@main.route('/api/inject-absensi/pegawai')
@form_access_required('InjectAbsensi.aspx')
def api_inject_absensi_pegawai():
    return data_absensi_api_inject_pegawai()

@main.route('/api/inject-absensi/acak-jam', methods=['POST'])
@form_access_required('InjectAbsensi.aspx')
def api_inject_absensi_acak_jam():
    return data_absensi_api_acak_jam()

@main.route('/api/inject-absensi/save', methods=['POST'])
@form_access_required('InjectAbsensi.aspx')
def api_inject_absensi_save():
    return data_absensi_api_save()

@main.route('/data-absensi/pegawai-lembur-manual')
@form_access_required('InjectLembur.aspx')
def view_data_absensi_pegawai_lembur_manual():
    return data_absensi_pegawai_lembur_manual()

@main.route('/data-absensi/trace-tunjangan')
@form_access_required('TraceTunKin.aspx')
def view_data_absensi_trace_tunjangan():
    return data_absensi_trace_tunjangan()

@main.route('/api/trace-tunjangan')
@form_access_required('TraceTunKin.aspx')
def api_trace_tunjangan():
    return data_absensi_api_trace_tunjangan()

@main.route('/data-absensi/trace')
@form_access_required('TraceAbsensi.aspx')
def view_data_absensi_trace():
    return data_absensi_trace()

@main.route('/api/trace-absensi')
@form_access_required('TraceAbsensi.aspx')
def api_trace_absensi():
    return data_absensi_api_trace_absensi()

# Cari Absensi :
@main.route('/data-absensi/cari/non-finger')
@form_access_required('Absensimanual.aspx')
def view_cari_absensi_non_finger():
    return cari_absensi_non_finger()

@main.route('/api/cari-absensi-non-finger')
@form_access_required('Absensimanual.aspx')
def api_cari_absensi_non_finger():
    return data_absensi_api_cari_non_finger()

@main.route('/data-absensi/cari/normalisasi-finger')
@form_access_required('AbsensiFP.aspx')
def view_cari_absensi_normalisasi_finger():
    return cari_absensi_normalisasi_finger()

@main.route('/api/cari-absensi-normalisasi-finger')
@form_access_required('AbsensiFP.aspx')
def api_cari_absensi_normalisasi_finger():
    return data_absensi_api_cari_normalisasi_finger()

@main.route('/data-absensi/cari/pegawai-manual')
@form_access_required('Absensimanual.aspx')
def view_cari_absensi_pegawai_manual():
    return cari_absensi_pegawai_manual()

@main.route('/api/cari-absensi-manual')
@form_access_required('Absensimanual.aspx')
def api_cari_absensi_manual():
    return data_absensi_api_cari_manual()

@main.route('/api/cari-absensi-manual/delete', methods=['POST'])
@form_access_required('Absensimanual.aspx')
def api_cari_absensi_manual_delete():
    return data_absensi_api_cari_delete()

@main.route('/api/cari-absensi-manual/update', methods=['POST'])
@form_access_required('Absensimanual.aspx')
def api_cari_absensi_manual_update():
    return data_absensi_api_cari_update()

@main.route('/data-absensi/cari/pegawai-lembur-manual')
@form_access_required('InjectLembur.aspx')
def view_cari_absensi_pegawai_lembur_manual():
    return cari_absensi_pegawai_lembur_manual()

@main.route('/api/inject-lembur/pegawai')
@form_access_required('InjectLembur.aspx')
def api_inject_lembur_pegawai():
    return data_absensi_api_inject_lembur_pegawai()

@main.route('/api/inject-lembur/acak-jam', methods=['POST'])
@form_access_required('InjectLembur.aspx')
def api_inject_lembur_acak_jam():
    return data_absensi_api_inject_lembur_acak()

@main.route('/api/inject-lembur/save', methods=['POST'])
@form_access_required('InjectLembur.aspx')
def api_inject_lembur_save():
    return data_absensi_api_inject_lembur_save()

@main.route('/api/cari-lembur-manual')
@form_access_required('InjectLembur.aspx')
def api_cari_lembur_manual():
    return data_absensi_api_cari_lembur()

@main.route('/api/cari-lembur-manual/delete', methods=['POST'])
@form_access_required('InjectLembur.aspx')
def api_cari_lembur_manual_delete():
    return data_absensi_api_cari_lembur_delete()

@main.route('/api/cari-lembur-manual/update', methods=['POST'])
@form_access_required('InjectLembur.aspx')
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

@main.route('/api/absensi-kehadiran/save-pdf')
@login_required
def api_absensi_kehadiran_save_pdf():
    return data_siaga_api_absensi_kehadiran_save_pdf()

@main.route('/api/absensi-kehadiran/export-pdf')
@login_required
def api_absensi_kehadiran_export_pdf():
    return data_siaga_api_absensi_kehadiran_export_pdf()

@main.route('/api/internal/calendar/piket-siaga/pdf')
def api_internal_calendar_piket_siaga_pdf():
    return data_siaga_api_absensi_kehadiran_internal_pdf()

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
@login_required
def api_rejadwal_siaga_add_personil():
    from app.controllers.dashboard_2DataSiagaController import api_rejadwal_siaga_add_personil
    return api_rejadwal_siaga_add_personil()

@main.route('/siaga/view-jadwal')
@login_required
def view_data_siaga_view_jadwal():
    return data_siaga_view_jadwal()


@main.route('/siaga/buat-jadwal-piket')
@login_required
def view_data_siaga_membuat_jadwal_piket_siaga():
    return data_siaga_membuat_jadwal_piket_siaga()


@main.route('/api/siaga/pembuatan-jadwal/save', methods=['POST'])
@login_required
def api_pembuatan_jadwal_siaga_save():
    return data_siaga_api_pembuatan_jadwal_siaga_save()


@main.route('/api/siaga/view-jadwal')
@login_required
def api_siaga_view_jadwal_get():
    return data_siaga_api_view_jadwal_get()



@main.route(
    '/api/siaga/view-jadwal/lengkapi-shift2',
    methods=['POST']
)
@login_required
def api_siaga_view_jadwal_lengkapi_shift2():
    return data_siaga_api_view_jadwal_lengkapi_shift2()

@main.route('/api/siaga/view-jadwal/edit', methods=['POST'])
@login_required
def api_siaga_view_jadwal_edit():
    return data_siaga_api_view_jadwal_edit()

@main.route('/api/siaga/master-jabatan-aktif')
@login_required
def api_siaga_master_jabatan_aktif():
    from app.controllers.dashboard_2DataSiagaController import (
        api_siaga_master_jabatan_aktif
    )
    return api_siaga_master_jabatan_aktif()


@main.route('/api/siaga/master-unit-aktif')
@login_required
def api_siaga_master_unit_aktif():
    from app.controllers.dashboard_2DataSiagaController import (
        api_siaga_master_unit_aktif
    )
    return api_siaga_master_unit_aktif()


# ============================================================
# MASTER JABATAN SIAGA
# ============================================================

@main.route('/siaga/master-data/jabatan-siaga')
@login_required
def view_master_data_jabatan_siaga():
    from app.controllers.dashboard_2MasterDataController import (
        master_data_jabatan_siaga
    )
    return master_data_jabatan_siaga()


@main.route('/api/master-data/jabatan-siaga')
@login_required
def api_master_jabatan_siaga_get():
    return master_data_api_jabatan_siaga_get()


@main.route(
    '/api/master-data/jabatan-siaga/save',
    methods=['POST']
)
@login_required
def api_master_jabatan_siaga_save():
    return master_data_api_jabatan_siaga_save()


@main.route(
    '/api/master-data/jabatan-siaga/deactivate',
    methods=['POST']
)
@login_required
def api_master_jabatan_siaga_deactivate():
    return master_data_api_jabatan_siaga_deactivate()


@main.route(
    '/api/master-data/jabatan-siaga/activate',
    methods=['POST']
)
@login_required
def api_master_jabatan_siaga_activate():
    from app.controllers.dashboard_2MasterDataController import (
        api_jabatan_siaga_activate
    )
    return api_jabatan_siaga_activate()


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


# ============================================================
# DASHBOARD 4 - AGENDA
# ============================================================

@main.route('/dashboard4')
@login_required
def dashboard4_home():
    if not has_any_agenda_access():
        return ('Forbidden', 403)
    return dashboard4()

# ============================================================
# AGENDA RAPAT
# UI prototype — backend akan disambungkan pada tahap berikutnya.
# ============================================================

@main.route('/rekam-medis/pegawai')
@login_required
@form_access_required('REKAM_MEDIS')
def view_rekam_medis_pegawai():
    return rekam_medis_pegawai()


@main.route('/api/rekam-medis/petugas/search')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_petugas_search_route():
    return api_rekam_medis_petugas_search()

@main.route('/rekam-medis/scan/<token>')
@login_required
def rekam_medis_scan_route(token):
    return api_rekam_medis_scan(token)


@main.route('/rekam-medis/non-pegawai')
@login_required
@form_access_required('REKAM_MEDIS')
def view_rekam_medis_non_pegawai():
    return rekam_medis_non_pegawai()

@main.route('/api/rekam-medis/kegiatan/pegawai')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_list_route():
    return api_rekam_medis_kegiatan_pegawai_list()

@main.route('/api/rekam-medis/kegiatan/non-pegawai')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_non_pegawai_list_route():
    return api_rekam_medis_kegiatan_non_pegawai_list()

@main.route('/api/rekam-medis/kegiatan/pegawai/save', methods=['POST'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_save_route():
    return api_rekam_medis_kegiatan_pegawai_save()

@main.route('/api/rekam-medis/kegiatan/non-pegawai/save', methods=['POST'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_non_pegawai_save_route():
    return api_rekam_medis_kegiatan_non_pegawai_save()

@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_detail_route(kegiatan_id):
    return api_rekam_medis_kegiatan_pegawai_detail(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/non-pegawai/<int:kegiatan_id>')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_non_pegawai_detail_route(kegiatan_id):
    return api_rekam_medis_kegiatan_non_pegawai_detail(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>/qr')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_qr_route(kegiatan_id):
    return api_rekam_medis_kegiatan_pegawai_qr(kegiatan_id)


@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>', methods=['PUT'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_update_route(kegiatan_id):
    return api_rekam_medis_kegiatan_pegawai_update(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/non-pegawai/<int:kegiatan_id>', methods=['PUT'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_non_pegawai_update_route(kegiatan_id):
    return api_rekam_medis_kegiatan_non_pegawai_update(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>/cancel', methods=['POST'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_cancel_route(kegiatan_id):
    return api_rekam_medis_kegiatan_pegawai_cancel(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>/complete', methods=['POST'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_complete_route(kegiatan_id):
    return api_rekam_medis_kegiatan_pegawai_complete(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/non-pegawai/<int:kegiatan_id>/cancel', methods=['POST'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_non_pegawai_cancel_route(kegiatan_id):
    return api_rekam_medis_kegiatan_non_pegawai_cancel(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/non-pegawai/<int:kegiatan_id>/complete', methods=['POST'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_non_pegawai_complete_route(kegiatan_id):
    return api_rekam_medis_kegiatan_non_pegawai_complete(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>/peserta/<int:peserta_id>')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_peserta_detail_route(kegiatan_id, peserta_id):
    return api_rekam_medis_kegiatan_pegawai_peserta_detail(kegiatan_id, peserta_id)

@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>/peserta/<int:peserta_id>/save', methods=['POST'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_peserta_save_route(kegiatan_id, peserta_id):
    return api_rekam_medis_kegiatan_pegawai_peserta_save(kegiatan_id, peserta_id)

@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>/export/excel')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_export_excel_route(kegiatan_id):
    return api_rekam_medis_kegiatan_pegawai_export_excel(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/pegawai/<int:kegiatan_id>/export/pdf')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_pegawai_export_pdf_route(kegiatan_id):
    return api_rekam_medis_kegiatan_pegawai_export_pdf(kegiatan_id)

@main.route('/api/rekam-medis/kegiatan/non-pegawai/<int:kegiatan_id>/qr')
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_kegiatan_non_pegawai_qr_route(kegiatan_id):
    return api_rekam_medis_kegiatan_non_pegawai_qr(kegiatan_id)

@main.route('/rekam-medis')
@login_required
@form_access_required('REKAM_MEDIS')
def view_rekam_medis():
    return redirect(url_for('main.view_rekam_medis_pegawai'))


@main.route('/api/rekam-medis/search-pegawai', methods=['GET'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_search_pegawai_route():
    return api_rekam_medis_search_pegawai()


@main.route('/api/rekam-medis', methods=['POST'])
@login_required
@form_access_required('REKAM_MEDIS')
def api_rekam_medis_save_route():
    return api_rekam_medis_save()


@main.route('/agenda/rapat')
@login_required
@form_access_required('AGENDA_RAPAT')
def view_agenda_rapat():
    return agenda_rapat()


@main.route('/agenda/disposisi')
@login_required
@form_access_required('AGENDA_DISPOSISI')
def view_agenda_disposisi():
    return agenda_disposisi()


# ============================================================
# AGENDA LIVE API
# ============================================================

@main.route('/api/agenda/rapat', methods=['GET'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_route():
    return api_agenda_rapat_list()


@main.route('/api/agenda/rapat', methods=['POST'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_save_route():
    return api_agenda_rapat_save()


@main.route('/api/agenda/rapat/<int:event_id>', methods=['PUT'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_update_route(event_id):
    return api_agenda_rapat_update(event_id)


@main.route('/api/agenda/rapat/<int:event_id>', methods=['GET'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_detail_route(event_id):
    return api_agenda_rapat_detail(event_id)


@main.route('/api/agenda/rapat/<int:event_id>/cancel', methods=['POST'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_cancel_route(event_id):
    return api_agenda_rapat_cancel(event_id)


@main.route('/api/agenda/rapat/<int:event_id>/complete', methods=['POST'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_complete_route(event_id):
    return api_agenda_rapat_complete(event_id)


@main.route('/api/agenda/rapat/<int:event_id>/qr', methods=['GET'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_qr_route(event_id):
    return api_agenda_rapat_qr(event_id)


@main.route('/api/agenda/rapat/<int:event_id>/attendance', methods=['GET'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_attendance_route(event_id):
    return api_agenda_rapat_attendance(event_id)


@main.route('/api/agenda/rapat/<int:event_id>/daftar-hadir', methods=['GET'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_daftar_hadir_pdf_route(event_id):
    return api_agenda_rapat_daftar_hadir_pdf(event_id)


@main.route('/rapat/scan/<token>', methods=['GET'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_scan_route(token):
    return api_agenda_rapat_scan(token)


@main.route('/api/agenda/rapat/<int:event_id>/notulen', methods=['POST'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_notulen_upload_route(event_id):
    return api_agenda_rapat_notulen_upload(event_id)


@main.route('/api/agenda/rapat/<int:event_id>/notulen', methods=['GET'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_rapat_notulen_download_route(event_id):
    return api_agenda_rapat_notulen_download(event_id)


@main.route('/api/agenda/pegawai/search', methods=['GET'])
@login_required
@form_access_required('AGENDA_RAPAT')
def api_agenda_pegawai_search_route():
    return api_pegawai_agenda_search()


@main.route('/api/agenda/disposisi', methods=['GET'])
@login_required
@form_access_required('AGENDA_DISPOSISI')
def api_agenda_disposisi_list_route():
    return api_agenda_disposisi_list()


@main.route('/api/agenda/disposisi', methods=['POST'])
@login_required
@form_access_required('AGENDA_DISPOSISI')
def api_agenda_disposisi_save_route():
    return api_agenda_disposisi_save()


@main.route('/api/agenda/disposisi/<int:agenda_id>', methods=['GET'])
@login_required
@form_access_required('AGENDA_DISPOSISI')
def api_agenda_disposisi_detail_route(agenda_id):
    return api_agenda_disposisi_detail(agenda_id)


@main.route('/api/agenda/disposisi/<int:agenda_id>/cancel', methods=['POST'])
@login_required
@form_access_required('AGENDA_DISPOSISI')
def api_agenda_disposisi_cancel_route(agenda_id):
    return api_agenda_disposisi_cancel(agenda_id)


# ============================================================
# KESAMAPTAAN
# ============================================================

@main.route('/kesamaptaan')
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def view_kesamaptaan():
    return kesamaptaan()


@main.route('/api/kesamaptaan', methods=['GET'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_list_route():
    return api_kesamaptaan_list()


@main.route('/api/kesamaptaan', methods=['POST'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_save_route():
    return api_kesamaptaan_save()


@main.route('/api/kesamaptaan/<int:kegiatan_id>', methods=['GET'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_detail_route(kegiatan_id):
    return api_kesamaptaan_detail(kegiatan_id)


@main.route('/api/kesamaptaan/<int:kegiatan_id>', methods=['PUT'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_update_route(kegiatan_id):
    return api_kesamaptaan_update(kegiatan_id)


@main.route('/api/kesamaptaan/<int:kegiatan_id>/cancel', methods=['POST'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_cancel_route(kegiatan_id):
    return api_kesamaptaan_cancel(kegiatan_id)


@main.route('/api/kesamaptaan/<int:kegiatan_id>/complete', methods=['POST'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_complete_route(kegiatan_id):
    return api_kesamaptaan_complete(kegiatan_id)


@main.route('/api/kesamaptaan/<int:kegiatan_id>/qr', methods=['GET'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_qr_route(kegiatan_id):
    return api_kesamaptaan_qr(kegiatan_id)


@main.route('/api/kesamaptaan/<int:kegiatan_id>/attendance', methods=['GET'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_attendance_route(kegiatan_id):
    return api_kesamaptaan_attendance(kegiatan_id)


@main.route('/api/kesamaptaan/<int:kegiatan_id>/photos', methods=['POST'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_photos_route(kegiatan_id):
    return api_kesamaptaan_photos(kegiatan_id)


@main.route('/api/kesamaptaan/<int:kegiatan_id>/signature/<path:nip>', methods=['GET'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_signature_route(kegiatan_id, nip):
    return api_kesamaptaan_signature(kegiatan_id, nip)


@main.route('/api/kesamaptaan/<int:kegiatan_id>/pdf', methods=['GET'])
@login_required
@form_access_required('SUMDA_KESAMAPTAAN')
def api_kesamaptaan_pdf_route(kegiatan_id):
    return api_kesamaptaan_pdf(kegiatan_id)


@main.route('/api/internal/calendar/kesamaptaan/agenda', methods=['GET'])
def api_calendar_kesamaptaan_agenda_route():
    return api_kesamaptaan_internal_agenda()


@main.route('/api/internal/calendar/kesamaptaan/<int:kegiatan_id>/pdf', methods=['GET'])
def api_calendar_kesamaptaan_pdf_route(kegiatan_id):
    return api_kesamaptaan_internal_pdf(kegiatan_id)


@main.route('/api/internal/calendar/kesamaptaan/attendance-info', methods=['GET'])
def api_calendar_kesamaptaan_attendance_info_route():
    return api_kesamaptaan_internal_info()


@main.route('/api/internal/calendar/kesamaptaan/attendance/employee', methods=['POST'])
def api_calendar_kesamaptaan_employee_attendance_route():
    return api_kesamaptaan_internal_employee_attendance()


# ============================================================
# HRIS REBORN CALENDAR API
#
# Agenda Personal
# Event
# ICS Mobile Sync
#
# ============================================================


@main.route(
    '/api/calendar/personal/sync-token',
    methods=['GET']
)
@login_required
def api_calendar_personal_sync_token_route():

    return api_calendar_personal_sync_token()


@main.route(
    '/api/calendar/personal',
    methods=['GET']
)
@login_required
def api_calendar_personal_route():

    return api_calendar_personal()


@main.route(
    '/api/internal/calendar/sync-token',
    methods=['GET']
)
def api_calendar_sync_token_internal_route():

    return api_calendar_sync_token_internal()


@main.route(
    '/api/internal/calendar/employee-profile',
    methods=['GET']
)
def api_calendar_employee_profile_internal_route():

    return api_calendar_employee_profile_internal()


@main.route(
    '/api/internal/calendar/benefit/tunjangan-kinerja',
    methods=['GET']
)
def api_calendar_benefit_tunjangan_kinerja_internal_route():
    return api_calendar_benefit_tunjangan_kinerja_internal()


@main.route(
    '/api/internal/calendar/benefit/uang-makan',
    methods=['GET']
)
def api_calendar_benefit_uang_makan_internal_route():
    return api_calendar_benefit_uang_makan_internal()


@main.route(
    '/api/internal/calendar/benefit/uang-siaga',
    methods=['GET']
)
def api_calendar_benefit_uang_siaga_internal_route():
    return api_calendar_benefit_uang_siaga_internal()


@main.route(
    '/api/internal/calendar/benefit/uang-siaga-v2',
    methods=['GET']
)
def api_calendar_benefit_uang_siaga_v2_internal_route():
    return api_calendar_benefit_uang_siaga_v2_internal()


@main.route(
    '/api/internal/calendar/pelanggaran',
    methods=['GET']
)
def api_calendar_pelanggaran_internal_route():
    return api_calendar_pelanggaran_internal()


@main.route(
    '/api/internal/calendar/struktur-organisasi',
    methods=['GET']
)
def api_calendar_struktur_organisasi_internal_route():
    return api_calendar_struktur_organisasi_internal()


@main.route(
    '/api/internal/calendar/infografis',
    methods=['GET']
)
def api_calendar_infografis_internal_route():
    return api_calendar_infografis_internal()

@main.route(
    '/api/internal/calendar/personal',
    methods=['GET']
)
def api_calendar_personal_internal_route():

    from app.controllers.calendarController import (
        api_calendar_personal_internal
    )

    return api_calendar_personal_internal()


@main.route(
    '/api/internal/calendar/agenda/rekam-medis/attendance-info',
    methods=['GET']
)
def api_calendar_rekam_medis_info_route():
    return api_calendar_rekam_medis_info()


@main.route(
    '/api/internal/calendar/agenda/rekam-medis/attendance/employee',
    methods=['POST']
)
def api_calendar_rekam_medis_employee_route():
    return api_calendar_rekam_medis_employee()


@main.route(
    '/api/internal/calendar/agenda/rekam-medis/attendance/guest',
    methods=['POST']
)
def api_calendar_rekam_medis_guest_route():
    return api_calendar_rekam_medis_guest()


@main.route(
    '/api/internal/calendar/agenda/rapat/attendance-info',
    methods=['GET']
)
def api_calendar_rapat_attendance_info_route():
    return api_calendar_rapat_attendance_info()


@main.route(
    '/api/internal/calendar/agenda/rapat/attendance/employee',
    methods=['POST']
)
def api_calendar_rapat_employee_attendance_route():
    return api_calendar_rapat_employee_attendance()


@main.route(
    '/api/internal/calendar/agenda/rapat/attendance/guest',
    methods=['POST']
)
def api_calendar_rapat_guest_attendance_route():
    return api_calendar_rapat_guest_attendance()


@main.route(
    '/api/internal/calendar/agenda/rapat',
    methods=['GET']
)
def api_calendar_agenda_rapat_internal_route():

    return api_calendar_agenda_rapat_internal()


@main.route(
    '/api/internal/calendar/my-agenda',
    methods=['GET']
)
def api_calendar_my_agenda_internal_route():

    return api_calendar_my_agenda_internal()


@main.route(
    '/api/internal/calendar/agenda/rapat/<int:event_id>/notulen',
    methods=['GET']
)
def api_calendar_agenda_rapat_notulen_internal_route(event_id):

    return api_calendar_agenda_rapat_notulen_internal(event_id)


@main.route(
    '/api/calendar/my-agenda',
    methods=['GET']
)
@login_required
def api_calendar_my_agenda_route():

    return api_calendar_my_agenda()



@main.route(
    '/api/calendar/event',
    methods=['POST']
)
@login_required
def api_calendar_create_event_route():

    return api_calendar_create_event()



@main.route(
    '/api/calendar/feed/<token>.ics',
    methods=['GET']
)
def api_calendar_feed_route(token):

    return api_calendar_feed(token)



# ============================================================
# CALENDAR CATEGORY API
# ============================================================


@main.route(
    '/api/calendar/category',
    methods=['GET']
)
@login_required
def api_calendar_category_route():

    return api_calendar_category()



# ============================================================
# HRIS REBORN CALENDAR USER AGENDA
#
# Personal agenda lookup
# Conflict checking foundation
#
# ============================================================


@main.route(
    '/api/calendar/user/<nip>',
    methods=['GET']
)
@login_required
def api_calendar_user_route(nip):

    return api_calendar_user_agenda(
        nip
    )



# ============================================================
# HRIS REBORN CALENDAR CONFLICT API
# ============================================================


@main.route(
    '/api/calendar/conflict/<nip>',
    methods=['GET']
)
@login_required
def api_calendar_conflict_route(nip):

    return api_calendar_conflict(
        nip
    )


# ============================================================
# MASTER KALENDER V2 API
# Khusus UI Master Kalender baru
# ============================================================

@main.route(
    '/api/calendar/master',
    methods=['GET']
)
@login_required
def api_calendar_master_v2():

    return get_kalender_list()

