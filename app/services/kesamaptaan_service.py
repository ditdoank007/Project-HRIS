"""
Kesamaptaan service:
- employee-only QR attendance
- multiple photo documentation
- final combined PDF
- central HRIS-DATA storage
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
import hashlib
import os
import re
import secrets
import tempfile

import qrcode
from qrcode.image.svg import SvgPathImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
)
from werkzeug.datastructures import FileStorage
from flask import request

from app import db
from app.models.kesamaptaanKegiatanModel import KesamaptaanKegiatan
from app.models.kesamaptaanKehadiranModel import KesamaptaanKehadiran
from app.models.kesamaptaanDokumentasiModel import KesamaptaanDokumentasi
from app.models.pegawaiModel import Pegawai
from config import Config


MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTOS = 8
ALLOWED_MIMES = {"image/jpeg", "image/png"}


def jakarta_now():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Jakarta")).replace(tzinfo=None)


def storage_root():
    return Path(Config.HRIS_DATA_ROOT).resolve()


def _under_root(path):
    root = storage_root()
    candidate = Path(path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path storage tidak valid.")
    return candidate


def relative_dir(kegiatan):
    return (
        Path("KESAMAPTAAN")
        / kegiatan.TANGGAL.strftime("%Y")
        / kegiatan.TANGGAL.strftime("%m")
        / kegiatan.TANGGAL.strftime("%d")
        / f"kesamaptaan-{int(kegiatan.KEGIATAN_ID):03d}"
    )


def photo_relative_path(kegiatan, filename):
    return (relative_dir(kegiatan) / "foto" / filename).as_posix()


def photo_absolute_path(kegiatan, filename):
    return _under_root(storage_root() / photo_relative_path(kegiatan, filename))


def pdf_relative_path(kegiatan):
    return (relative_dir(kegiatan) / "kesamaptaan.pdf").as_posix()


def pdf_absolute_path(kegiatan):
    return _under_root(storage_root() / pdf_relative_path(kegiatan))


def build_qr_svg(token):
    base_url = (
        os.getenv("CALENDAR_PUBLIC_BASE_URL")
        or getattr(Config, "CALENDAR_PUBLIC_BASE_URL", None)
        or "https://calendar.sarsurabaya.id"
    ).rstrip("/")
    scan_url = f"{base_url}/absen-qrcode?token={token}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(scan_url)
    qr.make(fit=True)

    output = BytesIO()
    qr.make_image(image_factory=SvgPathImage).save(output)
    output.seek(0)
    return output.read(), scan_url


def employee_for_nip(nip):
    return (
        Pegawai.query
        .filter(Pegawai.NIP == str(nip or "").strip())
        .filter((Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR != "Y"))
        .first()
    )


def attendance_for(kegiatan_id, nip):
    return (
        KesamaptaanKehadiran.query
        .filter(
            KesamaptaanKehadiran.KEGIATAN_ID == kegiatan_id,
            KesamaptaanKehadiran.NIP == nip,
            KesamaptaanKehadiran.STATUS == "HADIR",
        )
        .first()
    )


def record_employee_attendance(kegiatan, nip):
    if kegiatan.STATUS in ("SELESAI", "BATAL") or kegiatan.QR_ACTIVE != "Y":
        raise ValueError("Absensi Kesamaptaan sudah ditutup.")

    pegawai = employee_for_nip(nip)
    if not pegawai:
        raise ValueError("Anda bukan pegawai aktif Kantor SAR Surabaya.")

    existing = attendance_for(kegiatan.KEGIATAN_ID, pegawai.NIP)
    if existing:
        return existing, pegawai, False

    signature = None
    root_ttd = Path(Config.HRIS_TTD_ROOT).resolve()
    candidates = []
    if pegawai.NIP:
        candidates.append(root_ttd / f"{pegawai.NIP}.png")
    if pegawai.FINGER_ID:
        candidates.append(root_ttd / f"{pegawai.FINGER_ID}.png")
    for candidate in candidates:
        if candidate.is_file():
            signature = candidate
            break

    now = jakarta_now()
    row = KesamaptaanKehadiran(
        KEGIATAN_ID=kegiatan.KEGIATAN_ID,
        NIP=pegawai.NIP,
        NAMA=pegawai.NAMA,
        SIGNATURE_PATH=str(signature) if signature else None,
        SCANNED_DATE=now,
        STATUS="HADIR",
    )
    db.session.add(row)
    db.session.commit()

    # Jika dokumentasi sudah tersedia, perbarui PDF agar daftar hadir
    # selalu mencerminkan scan QR terbaru.
    if documentation_rows(kegiatan.KEGIATAN_ID):
        finalize_pdf(kegiatan)

    return row, pegawai, True


def validate_photo(file_storage: FileStorage):
    if not file_storage or not file_storage.filename:
        raise ValueError("File foto wajib dipilih.")

    filename = file_storage.filename.strip()
    if len(filename) > 255:
        raise ValueError("Nama file foto maksimal 255 karakter.")

    mime = (file_storage.mimetype or "").lower()
    if mime not in ALLOWED_MIMES:
        raise ValueError("Foto hanya boleh JPG/JPEG atau PNG.")

    stream = file_storage.stream
    stream.seek(0)
    content = stream.read(MAX_PHOTO_BYTES + 1)
    stream.seek(0)

    if not content:
        raise ValueError("File foto kosong.")
    if len(content) > MAX_PHOTO_BYTES:
        raise ValueError("Ukuran setiap foto maksimal 10 MB.")

    if mime == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
        raise ValueError("File JPG tidak valid.")
    if mime == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("File PNG tidak valid.")

    return content, hashlib.sha256(content).hexdigest()


def save_photos(kegiatan, files, created_by):
    selected = [f for f in files if f and f.filename]
    if not selected:
        return []
    if len(selected) > MAX_PHOTOS:
        raise ValueError(f"Maksimal {MAX_PHOTOS} foto dokumentasi per kegiatan.")

    target_dir = _under_root(storage_root() / relative_dir(kegiatan) / "foto")
    target_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    start_order = (
        db.session.query(db.func.max(KesamaptaanDokumentasi.SORT_ORDER))
        .filter(KesamaptaanDokumentasi.KEGIATAN_ID == kegiatan.KEGIATAN_ID)
        .scalar()
        or 0
    )

    try:
        for offset, file_storage in enumerate(selected, start=1):
            content, sha256 = validate_photo(file_storage)
            ext = ".jpg" if (file_storage.mimetype or "").lower() == "image/jpeg" else ".png"
            safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(file_storage.filename).stem).strip("-")[:80]
            safe_stem = safe_stem or "foto"
            filename = f"{start_order + offset:03d}-{safe_stem}{ext}"
            target = photo_absolute_path(kegiatan, filename)

            fd, temp_path = tempfile.mkstemp(prefix=".photo-", suffix=".tmp", dir=target_dir)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, target)
            except Exception:
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass
                raise

            row = KesamaptaanDokumentasi(
                KEGIATAN_ID=kegiatan.KEGIATAN_ID,
                ORIGINAL_FILENAME=file_storage.filename.strip(),
                STORAGE_PATH=photo_relative_path(kegiatan, filename),
                MIME_TYPE=file_storage.mimetype,
                FILE_SIZE=len(content),
                SHA256=sha256,
                SORT_ORDER=start_order + offset,
                CREATED_BY=created_by,
                CREATED_DATE=jakarta_now(),
            )
            db.session.add(row)
            saved.append(target)

        db.session.commit()
        return saved
    except Exception:
        db.session.rollback()
        for target in saved:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        raise


def attendance_rows(kegiatan_id):
    return (
        KesamaptaanKehadiran.query
        .filter(
            KesamaptaanKehadiran.KEGIATAN_ID == kegiatan_id,
            KesamaptaanKehadiran.STATUS == "HADIR",
        )
        .order_by(
            KesamaptaanKehadiran.SCANNED_DATE.asc(),
            KesamaptaanKehadiran.NAMA.asc(),
        )
        .all()
    )


def documentation_rows(kegiatan_id):
    return (
        KesamaptaanDokumentasi.query
        .filter(KesamaptaanDokumentasi.KEGIATAN_ID == kegiatan_id)
        .order_by(KesamaptaanDokumentasi.SORT_ORDER.asc())
        .all()
    )


def _signature_path(row):
    if not row.SIGNATURE_PATH:
        return None
    path = Path(row.SIGNATURE_PATH).resolve()
    root = Path(Config.HRIS_TTD_ROOT).resolve()
    if path != root and root not in path.parents:
        return None
    return path if path.is_file() else None


def generate_final_pdf(kegiatan):
    rows = attendance_rows(kegiatan.KEGIATAN_ID)
    photos = documentation_rows(kegiatan.KEGIATAN_ID)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Kesamaptaan Pegawai Kantor SAR Surabaya",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "KesamaptaanTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=1,
        spaceAfter=6,
    )
    subtitle = ParagraphStyle(
        "KesamaptaanSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.HexColor("#4b5563"),
    )
    heading = ParagraphStyle(
        "KesamaptaanHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=1,
        spaceAfter=8,
    )
    normal = ParagraphStyle(
        "KesamaptaanNormal",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )

    hari_tanggal = f"{kegiatan.HARI}, {kegiatan.TANGGAL.strftime('%d-%m-%Y')}"
    jam = kegiatan.JAM.strftime("%H:%M") + " WIB"

    story = [
        Paragraph("KESAMAPTAAN PEGAWAI KANTOR SAR SURABAYA", title),
        Paragraph(f"<b>Hari, Tanggal:</b> {hari_tanggal}", subtitle),
        Paragraph(f"<b>Jam:</b> {jam}", subtitle),
        Spacer(1, 6 * mm),
        Paragraph("FOTO DOKUMENTASI", heading),
    ]

    if photos:
        cells = []
        for index, photo in enumerate(photos, start=1):
            path = _under_root(storage_root() / photo.STORAGE_PATH)
            if not path.is_file():
                continue

            image = Image(
                str(path),
                width=82 * mm,
                height=55 * mm,
                kind="proportional",
            )
            cell = Table(
                [
                    [Paragraph(f"Foto {index}", normal)],
                    [image],
                ],
                colWidths=[82 * mm],
                rowHeights=[None, 55 * mm],
            )
            cells.append(cell)

            if len(cells) == 2:
                story.append(Table(
                    [cells],
                    colWidths=[86 * mm, 86 * mm],
                    rowHeights=[62 * mm],
                ))
                cells = []
                story.append(Spacer(1, 4 * mm))

        if cells:
            while len(cells) < 2:
                cells.append("")
            story.append(Table(
                [cells],
                colWidths=[86 * mm, 86 * mm],
                rowHeights=[62 * mm],
            ))
    else:
        story.append(Paragraph("Belum ada foto dokumentasi yang diunggah.", normal))

    story.append(PageBreak())
    story.extend([
        Paragraph("DAFTAR HADIR KESAMAPTAAN PEGAWAI KANTOR SAR SURABAYA", title),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>Hari:</b> {kegiatan.HARI}", subtitle),
        Paragraph(f"<b>Tanggal:</b> {kegiatan.TANGGAL.strftime('%d-%m-%Y')}", subtitle),
        Paragraph(f"<b>Jam:</b> {jam}", subtitle),
        Spacer(1, 7 * mm),
    ])

    data = [["No.", "Nama", "Tanda Tangan"]]
    for index, row in enumerate(rows, start=1):
        signature = _signature_path(row)
        if signature:
            sign = Image(str(signature), width=35 * mm, height=13 * mm, kind="proportional")
        else:
            sign = Paragraph("__________________", normal)
        data.append([
            str(index),
            Paragraph(str(row.NAMA or "-"), normal),
            sign,
        ])

    if len(data) == 1:
        data.append(["-", Paragraph("Belum ada pegawai yang tercatat hadir.", normal), "__________________"])

    table = Table(
        data,
        colWidths=[14 * mm, 105 * mm, 55 * mm],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef5")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"Dicetak otomatis oleh HRIS Reborn · Jumlah hadir: {len(rows)} pegawai",
        ParagraphStyle("KesamaptaanFooter", parent=normal, fontSize=8, textColor=colors.grey),
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def finalize_pdf(kegiatan):
    content = generate_final_pdf(kegiatan)
    target = pdf_absolute_path(kegiatan)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(prefix=".kesamaptaan-", suffix=".pdf.tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    except Exception:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise

    kegiatan.PDF_PATH = pdf_relative_path(kegiatan)
    kegiatan.PDF_SHA256 = hashlib.sha256(content).hexdigest()
    kegiatan.UPDATE_DATE = jakarta_now()
    db.session.commit()
    return target
