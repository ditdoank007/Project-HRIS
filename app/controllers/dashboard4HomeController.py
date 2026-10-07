from flask import render_template
from app.utils.authorization import has_form_access, is_administrator


AGENDA_FORM_IDS = (
    "AGENDA_RAPAT",
    "AGENDA_DISPOSISI",
    "AGENDA_BUKU_TAMU",
    "SUMDA_KESAMAPTAAN",
    "REKAM_MEDIS",
)


def dashboard4():
    return render_template("pages/dashboard_4/dashboard4.html")


def has_any_agenda_access():
    if is_administrator():
        return True
    return any(has_form_access(form_id) for form_id in AGENDA_FORM_IDS)
