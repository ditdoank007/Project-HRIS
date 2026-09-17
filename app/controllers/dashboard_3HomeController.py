# controllers/dashboard_3HomeController.py
from flask import render_template, request


def dashboard_kinerja():
    """Render halaman Dashboard Pribadi (halaman utama dashboard_3)."""
    return render_template('pages/dashboard_3/Dashboard_Kinerja.html')