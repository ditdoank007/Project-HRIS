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
