# app/controllers/dashboard_1DisposisiController.py
from flask import render_template


def agenda_disposisi():
    """
    UI prototype Agenda Disposisi.

    Tahap ini hanya menyiapkan antarmuka.
    Integrasi database, pegawai, dokumen, dan rekap absensi
    akan dikerjakan setelah workflow Disposisi disepakati.
    """
    return render_template("pages/dashboard_1/Agenda Disposisi.html")
