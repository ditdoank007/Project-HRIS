#!/usr/bin/env python3
"""Migrate matched legacy Dinas Luar SPRIN PDFs into HRIS-DATA.

Safety rules:
- Source PDFs are COPIED, never moved or deleted.
- Only exact NamaFile matches in DINAS_LUAR are eligible.
- One NamaFile with many participant rows is one SPRIN document.
- Metadata conflicts, unsupported Jenis, and missing DB matches are skipped.
- Destination collisions get a deterministic GUID suffix.
- Database NamaFile is updated only after the destination PDF is copied and
  checksum-verified.
- The database update is transactional per SPRIN document.
- Default mode is dry-run. Use --apply to perform copy + DB update.

The legacy staging folder therefore remains an immutable source archive.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

import pymysql
from dotenv import dotenv_values


JENIS_FOLDER = {
    "DL": "UMUM",
    "OP": "OPERASI",
    "OPR": "OPERASI",
    "SD": "SUMBER-DAYA",
    "POT": "SUMBER-DAYA",
}


def normalize_keterangan(value: str, max_length: int = 72) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    text = text[:max_length].strip("-")
    return text or "dinas-luar"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_db_rows(env_path: Path) -> tuple[dict, list[dict]]:
    env = dotenv_values(env_path)
    required = ["DB_HOST", "DB_PORT", "DB_USER", "DB_NAME"]
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise RuntimeError("Variabel .env tidak lengkap: " + ", ".join(missing))

    password = env.get("DB_PASSWORD") or env.get("DB_PASS") or ""
    connection = pymysql.connect(
        host=env["DB_HOST"],
        port=int(env["DB_PORT"]),
        user=env["DB_USER"],
        password=password,
        database=env["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    GUIDSprin,
                    Nosurat,
                    TglAwalSurat,
                    TglAkhirSurat,
                    NamaFile,
                    KeteranganDinasLuar,
                    Jenis
                FROM DINAS_LUAR
                WHERE NamaFile IS NOT NULL
                  AND TRIM(NamaFile) <> ''
                """
            )
            return dict(env), list(cursor.fetchall())
    finally:
        connection.close()


def destination_for(row: dict) -> tuple[str, str, str]:
    jenis = str(row.get("Jenis") or "").strip().upper()
    folder = JENIS_FOLDER.get(jenis)
    if not folder:
        return "", "", "UNSUPPORTED_JENIS"

    tgl = row.get("TglAwalSurat")
    if not isinstance(tgl, date):
        return "", "", "MISSING_TGL_AWAL_SURAT"

    slug = normalize_keterangan(row.get("KeteranganDinasLuar") or "")
    filename = f"{tgl:%Y-%m}-{folder.lower()}-{slug}.pdf"
    relative = os.path.join(
        "DINAS LUAR", folder, f"{tgl:%Y}", f"{tgl:%m}", filename
    )
    return relative, filename, "MATCH"


def metadata_signature(row: dict) -> tuple[str, ...]:
    keys = (
        "GUIDSprin",
        "Nosurat",
        "TglAwalSurat",
        "TglAkhirSurat",
        "KeteranganDinasLuar",
        "Jenis",
    )
    return tuple(str(row.get(key) or "").strip() for key in keys)


def unique_destination(
    relative: str,
    filename: str,
    row: dict,
    used: dict[str, str],
) -> tuple[str, str, str]:
    key = relative.lower()
    if key not in used:
        used[key] = str(row.get("NamaFile") or "")
        return relative, filename, ""

    guid = re.sub(r"[^0-9a-zA-Z-]", "", str(row.get("GUIDSprin") or ""))
    suffix = guid[-8:] if guid else "document"
    stem = Path(filename).stem
    candidate = f"{stem}-{suffix}.pdf"
    candidate_relative = str(Path(relative).with_name(candidate))

    if candidate_relative.lower() in used:
        suffix = guid[-36:] if guid else "document"
        candidate = f"{stem}-{suffix}.pdf"
        candidate_relative = str(Path(relative).with_name(candidate))

    if candidate_relative.lower() in used:
        raise RuntimeError(f"Tidak dapat membuat nama tujuan unik: {relative}")

    used[candidate_relative.lower()] = str(row.get("NamaFile") or "")
    return candidate_relative, candidate, f"COLLISION_SUFFIX:{suffix}"


def copy_verified(source: Path, destination: Path) -> tuple[str, bool]:
    source_hash = sha256_file(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".migration-tmp")

    if destination.exists():
        existing_hash = sha256_file(destination)
        if existing_hash == source_hash:
            return source_hash, True
        raise RuntimeError(
            f"Tujuan sudah ada tetapi checksum berbeda: {destination}"
        )

    if temp.exists():
        temp.unlink()

    shutil.copy2(source, temp)
    copied_hash = sha256_file(temp)
    if copied_hash != source_hash:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum gagal setelah copy: {source.name}")

    os.replace(temp, destination)
    return source_hash, False


def update_db(env: dict, old_name: str, new_name: str) -> int:
    password = env.get("DB_PASSWORD") or env.get("DB_PASS") or ""
    connection = pymysql.connect(
        host=env["DB_HOST"],
        port=int(env["DB_PORT"]),
        user=env["DB_USER"],
        password=password,
        database=env["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE DINAS_LUAR
                SET NamaFile = %s
                WHERE LOWER(NamaFile) = LOWER(%s)
                """,
                (new_name, old_name),
            )
            affected = cursor.rowcount
        connection.commit()
        return affected
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrasi PDF Dinas Luar legacy -> HRIS-DATA"
    )
    parser.add_argument(
        "--source",
        default="/mnt/hris-data/DINAS LUAR/00-SPRIN-DINAS-LUAR-HRIS-2013",
        help="Folder staging PDF legacy",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path .env HRIS",
    )
    parser.add_argument(
        "--output",
        default="/tmp/dinas-luar-migration-apply.csv",
        help="CSV audit hasil migrasi",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Benar-benar copy PDF dan update DINAS_LUAR.NamaFile",
    )
    args = parser.parse_args()

    source = Path(args.source)
    env_path = Path(args.env)
    if not source.is_dir():
        print(f"ERROR: source folder tidak ditemukan: {source}", file=sys.stderr)
        return 2
    if not env_path.is_file():
        print(f"ERROR: .env tidak ditemukan: {env_path}", file=sys.stderr)
        return 2

    print("=== DINAS LUAR PDF MIGRATION ===")
    print(f"Source : {source}")
    print(f"Mode   : {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Audit  : {args.output}")
    print("Sumber legacy TIDAK akan dihapus.")
    print()

    env, rows = load_db_rows(env_path)
    by_filename: dict[str, list[dict]] = {}
    for row in rows:
        name = os.path.basename(str(row.get("NamaFile") or "").strip())
        if name:
            by_filename.setdefault(name.lower(), []).append(row)

    pdfs = sorted(
        path for path in source.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    print(f"PDF sumber: {len(pdfs):,}")
    print(f"Database rows dengan NamaFile: {len(rows):,}")
    print()

    fields = [
        "status", "source_filename", "guid_sprin", "no_surat",
        "tgl_awal_surat", "tgl_akhir_surat", "jenis", "keterangan",
        "destination", "destination_filename", "db_match_count",
        "db_rows_updated", "sha256", "notes",
    ]
    result_rows = []
    counters = Counter()
    used_destinations: dict[str, str] = {}

    for path in pdfs:
        name = path.name
        matches = by_filename.get(name.lower(), {})

        base = {
            "status": "",
            "source_filename": name,
            "guid_sprin": "",
            "no_surat": "",
            "tgl_awal_surat": "",
            "tgl_akhir_surat": "",
            "jenis": "",
            "keterangan": "",
            "destination": "",
            "destination_filename": "",
            "db_match_count": len(matches),
            "db_rows_updated": 0,
            "sha256": "",
            "notes": "",
        }

        if not matches:
            base["status"] = "SKIP_NOT_FOUND"
            base["notes"] = "NamaFile tidak ditemukan di DINAS_LUAR"
            counters[base["status"]] += 1
            result_rows.append(base)
            continue

        signatures = {metadata_signature(item) for item in matches}
        row = matches[0]
        for key, target in (
            ("GUIDSprin", "guid_sprin"),
            ("Nosurat", "no_surat"),
            ("TglAwalSurat", "tgl_awal_surat"),
            ("TglAkhirSurat", "tgl_akhir_surat"),
            ("Jenis", "jenis"),
            ("KeteranganDinasLuar", "keterangan"),
        ):
            base[target] = row.get(key) or ""

        if len(signatures) > 1:
            base["status"] = "SKIP_DB_CONFLICT"
            base["notes"] = "Metadata SPRIN berbeda untuk NamaFile yang sama"
            counters[base["status"]] += 1
            result_rows.append(base)
            continue

        relative, filename, status = destination_for(row)
        if status != "MATCH":
            base["status"] = f"SKIP_{status}"
            base["notes"] = "Data belum cukup untuk menentukan tujuan"
            counters[base["status"]] += 1
            result_rows.append(base)
            continue

        relative, filename, collision_note = unique_destination(
            relative, filename, row, used_destinations
        )
        destination = Path(env.get("HRIS_DATA_ROOT") or "/mnt/hris-data") / relative
        base["destination"] = relative
        base["destination_filename"] = filename

        try:
            if not args.apply:
                base["status"] = "READY"
                base["notes"] = collision_note or "Siap dimigrasikan"
                counters["READY"] += 1
            else:
                sha256, already_exists = copy_verified(path, destination)
                affected = update_db(env, name, filename)
                base["status"] = "MIGRATED_EXISTING" if already_exists else "MIGRATED"
                base["db_rows_updated"] = affected
                base["sha256"] = sha256
                base["notes"] = collision_note or ""
                counters[base["status"]] += 1
        except Exception as exc:
            base["status"] = "ERROR"
            base["notes"] = str(exc)
            counters["ERROR"] += 1

        result_rows.append(base)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result_rows)

    print("=== HASIL ===")
    for key in [
        "READY", "MIGRATED", "MIGRATED_EXISTING", "ERROR",
        "SKIP_NOT_FOUND", "SKIP_DB_CONFLICT",
        "SKIP_UNSUPPORTED_JENIS", "SKIP_MISSING_TGL_AWAL_SURAT",
    ]:
        print(f"{key:30s}: {counters[key]:,}")
    print()
    print(f"Audit CSV: {output}")
    print("Sumber staging tetap dipertahankan.")
    if not args.apply:
        print("Belum ada file yang dicopy dan belum ada database yang diubah.")
    return 1 if counters["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
