import hashlib
import os
import tempfile
from flask import current_app
from werkzeug.datastructures import FileStorage


NOTULEN_MAX_BYTES = 5 * 1024 * 1024
NOTULEN_MIME = "application/pdf"
NOTULEN_MAGIC = b"%PDF-"


def storage_root():
    root = current_app.config.get("HRIS_DATA_ROOT") or "/mnt/hris-data"
    return os.path.realpath(root)


def _ensure_under_root(path):
    root = storage_root()
    candidate = os.path.realpath(path)
    if candidate != root and not candidate.startswith(root + os.sep):
        raise ValueError("Path storage tidak valid.")
    return candidate


def notulen_relative_path(start_date, event_id):
    return os.path.join(
        "RAPAT",
        start_date.strftime("%Y"),
        start_date.strftime("%m"),
        start_date.strftime("%d"),
        f"rapat-{int(event_id):03d}",
        "notulen.pdf",
    )


def notulen_absolute_path(start_date, event_id):
    relative = notulen_relative_path(start_date, event_id)
    return _ensure_under_root(os.path.join(storage_root(), relative))


def validate_notulen(file_storage: FileStorage):
    if not file_storage or not file_storage.filename:
        raise ValueError("File Notulen PDF wajib dipilih.")

    filename = file_storage.filename.strip()
    if len(filename) > 255:
        raise ValueError("Nama file Notulen maksimal 255 karakter.")
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Notulen hanya boleh berupa file PDF.")

    if (file_storage.mimetype or "").lower() != NOTULEN_MIME:
        raise ValueError("MIME type harus application/pdf.")

    stream = file_storage.stream
    stream.seek(0)
    content = stream.read(NOTULEN_MAX_BYTES + 1)
    stream.seek(0)

    if len(content) > NOTULEN_MAX_BYTES:
        raise ValueError("Ukuran Notulen maksimal 5 MB.")

    if not content.startswith(NOTULEN_MAGIC):
        raise ValueError("File bukan PDF valid (magic bytes %PDF- tidak ditemukan).")

    if len(content) < len(NOTULEN_MAGIC):
        raise ValueError("File PDF tidak valid.")

    return content, hashlib.sha256(content).hexdigest()


def save_notulen(file_storage, start_date, event_id):
    content, sha256 = validate_notulen(file_storage)
    target = notulen_absolute_path(start_date, event_id)
    target_dir = os.path.dirname(target)
    os.makedirs(target_dir, mode=0o750, exist_ok=True)

    old_content = None
    if os.path.isfile(target):
        with open(target, "rb") as old_file:
            old_content = old_file.read()

    fd, temp_path = tempfile.mkstemp(prefix=".notulen-", suffix=".tmp", dir=target_dir)
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
        "content": content,
        "sha256": sha256,
        "size": len(content),
        "filename": file_storage.filename.strip(),
        "mime_type": NOTULEN_MIME,
        "relative_path": notulen_relative_path(start_date, event_id),
        "absolute_path": target,
        "replaced": old_content is not None,
        "old_content": old_content,
    }


def restore_previous_notulen(saved):
    target = saved["absolute_path"]
    old_content = saved.get("old_content")
    if old_content is None:
        try:
            os.unlink(target)
        except FileNotFoundError:
            pass
        return

    directory = os.path.dirname(target)
    fd, temp_path = tempfile.mkstemp(prefix=".notulen-restore-", suffix=".tmp", dir=directory)
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
