# app/services/backupRestoreService.py
import gzip
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename


def _root():
    root = Path(os.getenv("HRIS_BACKUP_ROOT", "/mnt/hris-data/BACKUP_DB"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _db_env():
    env = os.environ.copy()
    if current_app.config.get("DB_PASSWORD"):
        env["MYSQL_PWD"] = current_app.config["DB_PASSWORD"]
    return env


def _run(cmd, *, stdin=None, timeout=None):
    return subprocess.run(
        cmd,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_db_env(),
        timeout=timeout,
        check=False,
    )


def create_full_mariadb_backup():
    db = current_app.config["DB_NAME"]
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"HRIS_FULL_{stamp}.sql.gz"
    path = _root() / filename
    tmp = path.with_suffix(".sql.gz.tmp")

    cmd = [
        os.getenv("MARIADB_DUMP_BIN", "mariadb-dump"),
        "--single-transaction",
        "--routines",
        "--events",
        "--triggers",
        "--hex-blob",
        "--databases",
        db,
    ]

    with gzip.open(tmp, "wb", compresslevel=6) as gz:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_db_env(),
        )
        assert proc.stdout is not None
        shutil.copyfileobj(proc.stdout, gz)
        stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        rc = proc.wait()

    if rc != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(stderr.strip() or "mariadb-dump gagal.")

    tmp.replace(path)
    return {"filename": filename, "path": str(path), "size": path.stat().st_size}


def list_mariadb_backups():
    rows = []
    for path in sorted(_root().glob("HRIS_FULL_*.sql.gz"), reverse=True):
        rows.append({
            "filename": path.name,
            "size": path.stat().st_size,
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        })
    return rows


def restore_mariadb_backup(filename):
    filename = secure_filename(filename)
    if not filename or not filename.startswith("HRIS_FULL_") or not filename.endswith(".sql.gz"):
        raise ValueError("File backup MariaDB tidak valid.")

    path = _root() / filename
    if not path.is_file():
        raise FileNotFoundError("File backup tidak ditemukan.")

    db = current_app.config["DB_NAME"]

    # Logical full restore: the dump contains the database definition.
    proc = subprocess.Popen(
        [os.getenv("MARIADB_CLIENT_BIN", "mariadb")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        env=_db_env(),
    )

    assert proc.stdin is not None
    with gzip.open(path, "rb") as src:
        shutil.copyfileobj(src, proc.stdin)
    proc.stdin.close()

    stdout = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
    stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
    rc = proc.wait()

    if rc != 0:
        raise RuntimeError(stderr.strip() or stdout.strip() or "Restore MariaDB gagal.")

    return {"filename": filename, "database": db, "status": "RESTORED"}


def save_mssql_backup(upload):
    original = secure_filename(upload.filename or "")
    if not original.lower().endswith(".bak"):
        raise ValueError("File harus berformat .bak.")

    root = Path(os.getenv("HRIS_MSSQL_IMPORT_ROOT", "/mnt/hris-data/MSSQL_IMPORT"))
    root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stamp}_{original}"
    path = root / filename
    upload.save(path)

    return {
        "filename": filename,
        "original_filename": original,
        "path": str(path),
        "size": path.stat().st_size,
    }


def mssql_job_config(path, start_date, end_date):
    return {
        "backup_path": str(path),
        "start_date": start_date,
        "end_date": end_date,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "INSERT_ONLY",
        "status": "UPLOADED",
    }


def save_mssql_job(job):
    root = Path(os.getenv("HRIS_MSSQL_IMPORT_ROOT", "/mnt/hris-data/MSSQL_IMPORT"))
    root.mkdir(parents=True, exist_ok=True)
    job_path = root / (Path(job["backup_path"]).stem + ".json")
    job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job_path


def run_mssql_import(job, preview=False):
    script = os.getenv("HRIS_MSSQL_IMPORT_SCRIPT", "").strip()
    if not script:
        raise RuntimeError(
            "HRIS_MSSQL_IMPORT_SCRIPT belum dikonfigurasi. "
            "Upload dan periode sudah tersimpan; engine MSSQL belum dijalankan."
        )

    cmd = [
        os.getenv("PYTHON_BIN", "python3"),
        script,
        "--bak", job["backup_path"],
        "--start-date", job["start_date"],
        "--end-date", job["end_date"],
        "--mode", "preview" if preview else "import",
    ]

    proc = _run(cmd, timeout=int(os.getenv("HRIS_MSSQL_IMPORT_TIMEOUT", "7200")))
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "Import MSSQL gagal.")

    return {
        "status": "PREVIEW" if preview else "IMPORTED",
        "output": proc.stdout[-12000:],
    }
