# app/utils/decorators.py
from functools import wraps
from flask import session, redirect, url_for

def login_required(view_func):
    """
    Decorator untuk melindungi route admin/dashboard.
    Jika session belum login, redirect ke home page.
    """
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('main.index'))

        # SYSADMIN bootstrap selalu diperbolehkan.
        if session.get('sysadmin') is True:
            return view_func(*args, **kwargs)

        # Semua pegawai yang berhasil login diperbolehkan masuk HRIS.
        #
        # USER_ACCOUNT hanya digunakan untuk:
        # - Admin
        # - Operator
        # - Hak akses menu/form
        #
        # Pegawai biasa tetap dapat membuka Data Pribadi.

        return view_func(*args, **kwargs)
    return wrapped_view
def admin_required(view_func):
    """
    Decorator untuk route yang hanya boleh diakses
    oleh Administrator HRIS (INIT_LEVEL = 0).
    """
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('main.index'))

        from app.utils.authorization import is_administrator

        if not is_administrator():
            return ('Forbidden', 403)

        return view_func(*args, **kwargs)

    return wrapped_view

def form_access_required(form_id):
    """
    Decorator untuk route yang membutuhkan hak akses FormID HRIS.

    Administrator:
        selalu diperbolehkan.

    Operator:
        harus mempunyai HAK_AKSES_FORM dengan IS_AKSES='Y'.

    Pegawai biasa:
        ditolak dengan HTTP 403.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('main.index'))

            from app.utils.authorization import has_form_access, is_administrator

            if not (is_administrator() or has_form_access(form_id)):
                return ('Forbidden', 403)

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator
