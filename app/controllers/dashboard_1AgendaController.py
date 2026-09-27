# app/controllers/dashboard_1AgendaController.py
from flask import render_template


def agenda_rapat():
    """
    UI prototype Agenda Rapat.

    Tahap ini hanya menyiapkan antarmuka.
    Penyimpanan, QR attendance, notulen, conflict check,
    dan sinkronisasi Calendar akan diimplementasikan setelah
    desain UI disepakati.
    """
    return render_template("pages/dashboard_1/Agenda Rapat.html")
