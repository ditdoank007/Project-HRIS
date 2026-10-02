"""Storage helper for Dinas Luar SPRIN documents on HRIS-DATA NFS."""

import os
import re
import tempfile
import unicodedata

from flask import current_app
from werkzeug.datastructures import FileStorage


DINAS_LUAR_MAX_BYTES = 10 * 1024 * 1024
DINAS_LUAR_MAGIC = b"%PDF-"

JENIS_FOLDER = {
    "DL": "UMUM",
    "OP": "OPERASI",
    "OPR": "OPERASI",
    "SD": "SUMBER-DAYA",
    "POT": "SUMBER-DAYA",
}


def storage_root():
    root = current_app.config.get("HRIS_DATA_ROOT") or "/mnt/hris-data"
    return os.path.realpath(root)


def _ensure_under_root(path):
    root = storage_root()
    candidate = os.path.realpath(path)
    if candidate != root and not candidate.startswith(root + os.sep):
        raise ValueError("Path storage tidak valid.")
    return candidate


def normalize_keterangan_filename(value, max_length=72):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    text = text[:max_length].strip("-")
    return text or "dinas-luar"


def dinas_luar_folder(jenis):
    return JENIS_FOLDER.get(str(jenis or "").strip().upper(), "UMUM")


def dinas_luar_relative_path(tanggal_surat, jenis, keterangan):
    folder = dinas_luar_folder(jenis)
    filename = (
        f"{tanggal_surat:%Y-%m}-"
        f"{folder.lower()}-"
        f"{normalize_keterangan_filename(keterangan)}.pdf"
    )
    return os.path.join(
        "DINAS LUAR",
        folder,
        tanggal_surat.strftime("%Y"),
        tanggal_surat.strftime("%m"),
        filename,
    )


def dinas_luar_absolute_path(tanggal_surat, jenis, keterangan):
    return _ensure_under_root(
        os.path.join(
            storage_root(),
            dinas_luar_relative_path(tanggal_surat, jenis, keterangan),
        )
    )


def dinas_luar_absolute_path_by_filename(tanggal_surat, jenis, filename):
    folder = dinas_luar_folder(jenis)
    safe_name = os.path.basename(str(filename or "").strip())
    return _ensure_under_root(
        os.path.join(
            storage_root(),
            "DINAS LUAR",
            folder,
            tanggal_surat.strftime("%Y"),
            tanggal_surat.strftime("%m"),
            safe_name,
        )
    )


def validate_dinas_luar_pdf(file_storage: FileStorage):
    if not file_storage or not file_storage.filename:
        raise ValueError("File SPRIN PDF wajib dipilih.")

    filename = file_storage.filename.strip()
    if len(filename) > 255:
        raise ValueError("Nama file SPRIN maksimal 255 karakter.")
    if not filename.lower().endswith(".pdf"):
        raise ValueError("File SPRIN hanya boleh berupa PDF.")

    stream = file_storage.stream
    stream.seek(0)
    content = stream.read(DINAS_LUAR_MAX_BYTES + 1)
    stream.seek(0)

    if len(content) > DINAS_LUAR_MAX_BYTES:
        raise ValueError("Ukuran SPRIN maksimal 10 MB.")

    if not content.startswith(DINAS_LUAR_MAGIC):
        raise ValueError("File SPRIN bukan PDF valid.")

    return content


def save_dinas_luar_pdf(file_storage, tanggal_surat, jenis, keterangan):
    content = validate_dinas_luar_pdf(file_storage)
    target = dinas_luar_absolute_path(tanggal_surat, jenis, keterangan)
    target_dir = os.path.dirname(target)
    os.makedirs(target_dir, mode=0o750, exist_ok=True)

    old_content = None
    if os.path.isfile(target):
        with open(target, "rb") as old_file:
            old_content = old_file.read()

    fd, temp_path = tempfile.mkstemp(
        prefix=".dinas-luar-",
        suffix=".tmp",
        dir=target_dir,
    )

    try:
        with os.fdopen(fd, "wb") as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, target)
    except Exception:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise

    return {
        "filename": os.path.basename(target),
        "relative_path": dinas_luar_relative_path(
            tanggal_surat, jenis, keterangan
        ),
        "absolute_path": target,
        "old_content": old_content,
    }


def restore_dinas_luar_pdf(saved):
    target = saved["absolute_path"]
    old_content = saved.get("old_content")

    if old_content is None:
        try:
            os.unlink(target)
        except FileNotFoundError:
            pass
        return

    directory = os.path.dirname(target)
    fd, temp_path = tempfile.mkstemp(
        prefix=".dinas-luar-restore-",
        suffix=".tmp",
        dir=directory,
    )
    try:
        with os.fdopen(fd, "wb") as temp_file:
            temp_file.write(old_content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, target)
    finally:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
