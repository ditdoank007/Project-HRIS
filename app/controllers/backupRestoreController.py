# app/controllers/backupRestoreController.py
from datetime import datetime
from pathlib import Path

from flask import jsonify, redirect, render_template, request, url_for

from app.services.backupRestoreService import (
    create_full_mariadb_backup,
    list_mariadb_backups,
    mssql_job_config,
    restore_mariadb_backup,
    run_mssql_import,
    save_mssql_backup,
    save_mssql_job,
)
from app.utils.authorization import is_administrator, has_form_access, can_modify


BACKUP_RESTORE_FORM_ID = "BackupRestore.aspx"

def _backup_restore_read_json():
    if not has_form_access(BACKUP_RESTORE_FORM_ID):
        return jsonify({"ok": False, "message": "Anda tidak memiliki hak akses Backup / Restore."}), 403
    return None

def _backup_restore_modify_json():
    if not has_form_access(BACKUP_RESTORE_FORM_ID):
        return jsonify({"ok": False, "message": "Anda tidak memiliki hak akses Backup / Restore."}), 403
    if not can_modify(BACKUP_RESTORE_FORM_ID):
        return jsonify({"ok": False, "message": "Hak akses Backup / Restore Anda adalah Read Only."}), 403
    return None

def _admin_json():
    if not is_administrator():
        return jsonify({"ok": False, "message": "Akses khusus Administrator."}), 403
    return None


def backup_restore_home():
    """Legacy entry point; redirect to the dedicated MariaDB backup page."""
    return redirect(url_for("main.view_backup_mariadb"))

def backup_mariadb_home():
    denied = _backup_restore_read_json()
    if denied:
        return denied
    return render_template("pages/dashboard_1/Backup MariaDB.html", can_modify=can_modify(BACKUP_RESTORE_FORM_ID))

def restore_mariadb_home():
    denied = _backup_restore_read_json()
    if denied:
        return denied
    return render_template("pages/dashboard_1/Restore MariaDB.html", can_modify=can_modify(BACKUP_RESTORE_FORM_ID))

def import_mssql_home():
    denied = _backup_restore_read_json()
    if denied:
        return denied
    return render_template("pages/dashboard_1/Impor MSSQL 2013.html", can_modify=can_modify(BACKUP_RESTORE_FORM_ID))


def api_backup_mariadb():
    denied = _backup_restore_modify_json()
    if denied:
        return denied
    try:
        result = create_full_mariadb_backup()
        return jsonify({"ok": True, "message": "Full backup MariaDB berhasil dibuat.", "data": result})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


def api_backup_mariadb_list():
    denied = _backup_restore_read_json()
    if denied:
        return denied
    return jsonify({"ok": True, "data": list_mariadb_backups()})


def api_restore_mariadb():
    denied = _backup_restore_modify_json()
    if denied:
        return denied

    filename = (request.form.get("filename") or "").strip()
    confirmation = (request.form.get("confirmation") or "").strip().upper()
    if confirmation != "RESTORE HRIS":
        return jsonify({"ok": False, "message": "Konfirmasi restore harus diisi: RESTORE HRIS."}), 400

    try:
        result = restore_mariadb_backup(filename)
        return jsonify({"ok": True, "message": "Restore MariaDB berhasil.", "data": result})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


def api_import_mssql_upload():
    denied = _backup_restore_modify_json()
    if denied:
        return denied

    upload = request.files.get("backup_file")
    start_date = (request.form.get("start_date") or "").strip()
    end_date = (request.form.get("end_date") or "").strip()

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "message": "Periode tanggal tidak valid."}), 400

    if start > end:
        return jsonify({"ok": False, "message": "Tanggal awal tidak boleh lebih besar dari tanggal akhir."}), 400
    if not upload or not upload.filename:
        return jsonify({"ok": False, "message": "File .bak belum dipilih."}), 400

    try:
        saved = save_mssql_backup(upload)
        job = mssql_job_config(Path(saved["path"]), start.isoformat(), end.isoformat())
        job_path = save_mssql_job(job)
        return jsonify({
            "ok": True,
            "message": "Backup MSSQL tersimpan dan siap divalidasi.",
            "data": {**saved, "job_file": str(job_path)},
        })
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


def api_import_mssql_preview():
    denied = _backup_restore_read_json()
    if denied:
        return denied

    backup_path = (request.form.get("backup_path") or "").strip()
    start_date = (request.form.get("start_date") or "").strip()
    end_date = (request.form.get("end_date") or "").strip()

    job = {
        "backup_path": backup_path,
        "start_date": start_date,
        "end_date": end_date,
    }
    try:
        return jsonify({"ok": True, "data": run_mssql_import(job, preview=True)})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


def api_import_mssql_execute():
    denied = _backup_restore_modify_json()
    if denied:
        return denied

    backup_path = (request.form.get("backup_path") or "").strip()
    start_date = (request.form.get("start_date") or "").strip()
    end_date = (request.form.get("end_date") or "").strip()
    confirmation = (request.form.get("confirmation") or "").strip().upper()

    if confirmation != "IMPOR MSSQL HRIS 2013":
        return jsonify({"ok": False, "message": "Konfirmasi impor harus diisi: IMPOR MSSQL HRIS 2013."}), 400

    job = {
        "backup_path": backup_path,
        "start_date": start_date,
        "end_date": end_date,
    }
    try:
        return jsonify({"ok": True, "data": run_mssql_import(job, preview=False)})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500
