#!/usr/bin/env python3
"""Dry-run mapper for legacy HRIS 2013 Dinas Luar SPRIN PDFs.

This script is intentionally read-only:
- It scans legacy PDF files.
- It reads DINAS_LUAR from HRIS-DB.
- It matches PDFs by exact NamaFile.
- It calculates the HRIS Reborn destination path.
- It NEVER copies, renames, moves, or updates database rows.

The resulting CSV is the approval artifact for the later migration step.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
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

FILENAME_RE = re.compile(
    r"^(?P<stem>DL_(?P<year>\\d{4})-(?P<month>\\d{2})_[0-9a-fA-F-]{36})\\.pdf$",
    re.IGNORECASE,
)


def normalize_keterangan(value: str, max_length: int = 72) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    text = text[:max_length].strip("-")
    return text or "dinas-luar"


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
        "DINAS LUAR",
        folder,
        f"{tgl:%Y}",
        f"{tgl:%m}",
        filename,
    )
    return relative, filename, "MATCH"


def load_db_rows(env_path: Path) -> list[dict]:
    env = dotenv_values(env_path)

    required = ["DB_HOST", "DB_PORT", "DB_USER", "DB_NAME"]
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise RuntimeError(
            "Variabel .env tidak lengkap: " + ", ".join(missing)
        )

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
            return list(cursor.fetchall())
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run mapping PDF Dinas Luar HRIS 2013 -> HRIS Reborn"
    )
    parser.add_argument(
        "--source",
        default="/mnt/hris-data/DINAS LUAR/00-SPRIN-DINAS-LUAR-HRIS-2013",
        help="Folder sumber PDF legacy",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path .env HRIS",
    )
    parser.add_argument(
        "--output",
        default="/tmp/dinas-luar-migration-dry-run.csv",
        help="CSV hasil dry-run",
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

    print("=== DINAS LUAR PDF MIGRATION DRY-RUN ===")
    print(f"Source : {source}")
    print(f"Output : {args.output}")
    print("Mode   : READ-ONLY (tidak ada copy/move/update database)")
    print()

    print("Membaca DINAS_LUAR dari database...")
    rows = load_db_rows(env_path)
    print(f"Database rows dengan NamaFile: {len(rows):,}")

    by_filename: dict[str, list[dict]] = {}
    for row in rows:
        name = os.path.basename(str(row.get("NamaFile") or "").strip())
        if name:
            by_filename.setdefault(name.lower(), []).append(row)

    pdfs = sorted(
        path for path in source.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    print(f"PDF sumber di folder staging: {len(pdfs):,}")
    print()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "status",
        "source_filename",
        "guid_sprin",
        "no_surat",
        "tgl_awal_surat",
        "tgl_akhir_surat",
        "jenis",
        "keterangan",
        "destination",
        "destination_filename",
        "db_match_count",
        "notes",
    ]

    counters = Counter()
    destination_seen: dict[str, str] = {}
    result_rows: list[dict] = []

    for path in pdfs:
        name = path.name
        matches = by_filename.get(name.lower(), [])

        if not matches:
            counters["NOT_FOUND"] += 1
            result_rows.append({
                "status": "NOT_FOUND",
                "source_filename": name,
                "guid_sprin": "",
                "no_surat": "",
                "tgl_awal_surat": "",
                "tgl_akhir_surat": "",
                "jenis": "",
                "keterangan": "",
                "destination": "",
                "destination_filename": "",
                "db_match_count": 0,
                "notes": "NamaFile tidak ditemukan di DINAS_LUAR",
            })
            continue

        if len(matches) > 1:
            counters["DB_DUPLICATE"] += 1
            row = matches[0]
            result_rows.append({
                "status": "DB_DUPLICATE",
                "source_filename": name,
                "guid_sprin": row.get("GUIDSprin") or "",
                "no_surat": row.get("Nosurat") or "",
                "tgl_awal_surat": row.get("TglAwalSurat") or "",
                "tgl_akhir_surat": row.get("TglAkhirSurat") or "",
                "jenis": row.get("Jenis") or "",
                "keterangan": row.get("KeteranganDinasLuar") or "",
                "destination": "",
                "destination_filename": "",
                "db_match_count": len(matches),
                "notes": "NamaFile muncul pada lebih dari satu row",
            })
            continue

        row = matches[0]
        destination, destination_filename, status = destination_for(row)

        if status != "MATCH":
            counters[status] += 1
            result_rows.append({
                "status": status,
                "source_filename": name,
                "guid_sprin": row.get("GUIDSprin") or "",
                "no_surat": row.get("Nosurat") or "",
                "tgl_awal_surat": row.get("TglAwalSurat") or "",
                "tgl_akhir_surat": row.get("TglAkhirSurat") or "",
                "jenis": row.get("Jenis") or "",
                "keterangan": row.get("KeteranganDinasLuar") or "",
                "destination": "",
                "destination_filename": "",
                "db_match_count": 1,
                "notes": "Data belum cukup untuk menentukan tujuan",
            })
            continue

        key = destination.lower()
        if key in destination_seen and destination_seen[key] != name:
            counters["DESTINATION_COLLISION"] += 1
            result_rows.append({
                "status": "DESTINATION_COLLISION",
                "source_filename": name,
                "guid_sprin": row.get("GUIDSprin") or "",
                "no_surat": row.get("Nosurat") or "",
                "tgl_awal_surat": row.get("TglAwalSurat") or "",
                "tgl_akhir_surat": row.get("TglAkhirSurat") or "",
                "jenis": row.get("Jenis") or "",
                "keterangan": row.get("KeteranganDinasLuar") or "",
                "destination": destination,
                "destination_filename": destination_filename,
                "db_match_count": 1,
                "notes": f"Tujuan sama dengan {destination_seen[key]}",
            })
            continue

        destination_seen[key] = name
        counters["MATCH"] += 1
        result_rows.append({
            "status": "MATCH",
            "source_filename": name,
            "guid_sprin": row.get("GUIDSprin") or "",
            "no_surat": row.get("Nosurat") or "",
            "tgl_awal_surat": row.get("TglAwalSurat") or "",
            "tgl_akhir_surat": row.get("TglAkhirSurat") or "",
            "jenis": row.get("Jenis") or "",
            "keterangan": row.get("KeteranganDinasLuar") or "",
            "destination": destination,
            "destination_filename": destination_filename,
            "db_match_count": 1,
            "notes": "",
        })

    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result_rows)

    print("=== HASIL ===")
    for key in [
        "MATCH",
        "NOT_FOUND",
        "DB_DUPLICATE",
        "DESTINATION_COLLISION",
        "UNSUPPORTED_JENIS",
        "MISSING_TGL_AWAL_SURAT",
    ]:
        print(f"{key:24s}: {counters[key]:,}")

    print()
    print("Per Jenis untuk file MATCH:")
    jenis_counts = Counter(
        row["jenis"]
        for row in result_rows
        if row["status"] == "MATCH"
    )
    for jenis, count in sorted(jenis_counts.items()):
        print(f"  {jenis or '(kosong)':20s}: {count:,}")

    print()
    print(f"CSV dry-run: {output}")
    print("Tidak ada file sumber yang dipindahkan/diubah.")
    print("Tidak ada perubahan database.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
