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
