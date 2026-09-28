"""
Business services for Agenda Rapat:
- QR attendance
- employee and non-employee attendance
- attendance ordering
- guest signature storage
- Daftar Hadir PDF
- employee signature lookup
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from html import escape
import os
import base64
import re
import secrets
import uuid
from zoneinfo import ZoneInfo

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
)

from flask import request

from app import db
from app.models.agendaRapatAttendanceModel import AgendaRapatAttendance
from app.models.agendaRapatMetaModel import AgendaRapatMeta
from app.models.calendarEventModel import CalendarEvent
from app.models.calendarParticipantModel import CalendarParticipant
from app.models.pegawaiModel import Pegawai
from config import Config


def jakarta_now():
    return datetime.now(ZoneInfo("Asia/Jakarta")).replace(tzinfo=None)


def normalize_display_name(value):
    value = re.sub(r"\s+", " ", str(value or "").strip())
    if not value:
        return ""

    parts = [part.strip() for part in value.split(",")]
    name_part = " ".join(
        "-".join(
            piece[:1].upper() + piece[1:].lower()
            for piece in token.split("-")
            if piece
        )
        for token in parts[0].split()
    )

    suffixes = [
        re.sub(r"\s+", " ", part).strip()
        for part in parts[1:]
        if part.strip()
    ]

    if suffixes:
        return ", ".join([name_part, *suffixes])

    return name_part

def get_or_create_meta(event, organizer_nip, created_by):
    meta = AgendaRapatMeta.query.filter_by(EVENT_ID=event.EVENT_ID).first()
    if meta:
        return meta

    meta = AgendaRapatMeta(
        EVENT_ID=event.EVENT_ID,
        ORGANIZER_NIP=organizer_nip,
        QR_TOKEN=secrets.token_urlsafe(32),
        QR_ACTIVE="Y",
        CREATED_BY=created_by,
        CREATED_DATE=jakarta_now(),
    )
    db.session.add(meta)
    db.session.flush()
    return meta


def get_meta(event_id):
    return AgendaRapatMeta.query.filter_by(EVENT_ID=event_id).first()


def _employee_for_nip(nip):
    return (
        Pegawai.query
        .filter(Pegawai.NIP == str(nip).strip())
        .filter((Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR != "Y"))
        .first()
    )


def _role_priority(pegawai):
    if not pegawai:
        return 60

    jabatan = str(pegawai.JABATAN or "").strip().lower()
    eselon = str(pegawai.ESELON or "").strip().lower()
    text_value = f"{jabatan} {eselon}"

    if "kepala kantor" in text_value or "kakansar" in text_value:
        return 10

    if (
        "kasubbag umum" in text_value
        or "kepala subbagian umum" in text_value
        or ("kasubbag" in text_value and "umum" in text_value)
    ):
        return 20

    if (
        "kasie operasi" in text_value
        or "kasi operasi" in text_value
        or "kepala seksi operasi" in text_value
    ):
        return 30

    if (
        "kasie sumber daya" in text_value
        or "kasi sumber daya" in text_value
        or "kepala seksi sumber daya" in text_value
    ):
        return 40

    return 50


def attendance_rows(event_id):
    raw_rows = (
        AgendaRapatAttendance.query
        .filter(
            AgendaRapatAttendance.EVENT_ID == event_id,
            AgendaRapatAttendance.STATUS == "HADIR",
        )
        .order_by(AgendaRapatAttendance.SCANNED_DATE.asc())
        .all()
    )

    employee_nips = [row.NIP for row in raw_rows if row.ATTENDEE_TYPE == "PEGAWAI" and row.NIP]
    employees = {}
    if employee_nips:
        employees = {
            p.NIP: p
            for p in Pegawai.query.filter(Pegawai.NIP.in_(employee_nips)).all()
        }

    rows = []
    for attendance in raw_rows:
        pegawai = employees.get(attendance.NIP) if attendance.ATTENDEE_TYPE == "PEGAWAI" else None
        if attendance.ATTENDEE_TYPE == "PEGAWAI" and not pegawai:
            continue

        display_name = normalize_display_name(
            pegawai.NAMA if pegawai else (attendance.NAME or attendance.NAME_RAW or "-")
        )

        identity = (
            _employee_identity(pegawai)
            if pegawai
            else (attendance.NIP or "-")
        )

        rows.append({
            "attendance": attendance,
            "pegawai": pegawai,
            "display_name": display_name,
            "identity": identity,
            "email": (
                pegawai.MAIL
                if pegawai and pegawai.MAIL
                else attendance.EMAIL
            ),
            "signature_path": (
                _signature_path(pegawai)
                if pegawai
                else _guest_signature_path(attendance)
            ),
            "priority": _role_priority(pegawai),
        })

    rows.sort(
        key=lambda item: (
            item["priority"],
            item["attendance"].SCANNED_DATE,
            item["display_name"].lower(),
        )
    )
    return rows


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


def _ensure_qr_open(event):
    meta = get_meta(event.EVENT_ID)
    if not meta or meta.QR_ACTIVE != "Y":
        raise ValueError("QR absensi rapat sudah tidak aktif.")
    if event.STATUS in ("SELESAI", "BATAL"):
        raise ValueError("Rapat sudah ditutup atau dibatalkan.")
    return meta


def record_employee_attendance(event, nip, method="QR"):
    pegawai = _employee_for_nip(nip)
    if not pegawai:
        raise ValueError("Data pegawai tidak ditemukan atau pegawai sudah tidak aktif.")

    _ensure_qr_open(event)

    existing = (
        AgendaRapatAttendance.query
        .filter(
            AgendaRapatAttendance.EVENT_ID == event.EVENT_ID,
            AgendaRapatAttendance.ATTENDEE_TYPE == "PEGAWAI",
            AgendaRapatAttendance.NIP == pegawai.NIP,
        )
        .first()
    )
    if existing:
        return existing, pegawai, False

    now = jakarta_now()
    row = AgendaRapatAttendance(
        EVENT_ID=event.EVENT_ID,
        ATTENDEE_TYPE="PEGAWAI",
        ATTENDANCE_KEY=f"EMP:{pegawai.NIP}",
        NIP=pegawai.NIP,
        NAME=pegawai.NAMA,
        NAME_RAW=pegawai.NAMA,
        EMAIL=pegawai.MAIL,
        SCANNED_DATE=now,
        METHOD=method,
        STATUS="HADIR",
    )
    db.session.add(row)
    db.session.flush()

    participant = CalendarParticipant.query.filter_by(
        EVENT_ID=event.EVENT_ID,
        NIP=pegawai.NIP,
    ).first()
    if not participant:
        db.session.add(
            CalendarParticipant(
                EVENT_ID=event.EVENT_ID,
                NIP=pegawai.NIP,
                ROLE="HADIR",
                STATUS="ATTENDED",
                CREATED_DATE=now,
            )
        )
    else:
        participant.STATUS = "ATTENDED"

    db.session.commit()
    return row, pegawai, True


def _save_guest_signature(event, attendance_key, signature_data):
    if not signature_data:
        raise ValueError("Tanda tangan wajib diisi.")

    if not str(signature_data).startswith("data:image/png;base64,"):
        raise ValueError("Format tanda tangan harus PNG.")

    encoded = str(signature_data).split(",", 1)[1]
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception:
        raise ValueError("Data tanda tangan tidak valid.")

    if len(raw) == 0 or len(raw) > 512 * 1024:
        raise ValueError("Ukuran tanda tangan tidak valid.")

    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("File tanda tangan bukan PNG yang valid.")

    if not event.START_DATE:
        raise ValueError("Tanggal rapat tidak valid.")

    safe_key = re.sub(r"[^A-Za-z0-9_-]", "", attendance_key)[:60] or uuid.uuid4().hex
    relative = (
        Path("RAPAT")
        / event.START_DATE.strftime("%Y")
        / event.START_DATE.strftime("%m")
        / event.START_DATE.strftime("%d")
        / f"rapat-{event.EVENT_ID}"
        / "signatures"
        / f"guest-{safe_key}.png"
    )
    root = Path(Config.HRIS_DATA_ROOT).resolve()
    target = (root / relative).resolve()

    if root != target and root not in target.parents:
        raise ValueError("Path signature tidak valid.")

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_bytes(raw)
    temp.replace(target)
    return relative.as_posix()


def record_guest_attendance(
    event,
    name,
    email,
    signature_data,
    attendance_key=None,
    nip_or_finger=None,
    method="QR_GUEST",
):
    _ensure_qr_open(event)

    name_raw = re.sub(r"\s+", " ", str(name or "").strip())
    email = str(email or "").strip()
    if not name_raw:
        raise ValueError("Nama lengkap wajib diisi.")
    if len(name_raw) > 150:
        raise ValueError("Nama lengkap terlalu panjang.")
    if not email or len(email) > 255 or "@" not in email:
        raise ValueError("Email wajib diisi dengan format yang valid.")

    attendance_key = str(attendance_key or uuid.uuid4().hex).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", attendance_key):
        raise ValueError("Attendance key tidak valid.")

    existing = (
        AgendaRapatAttendance.query
        .filter(
            AgendaRapatAttendance.EVENT_ID == event.EVENT_ID,
            AgendaRapatAttendance.ATTENDEE_TYPE == "NON_PEGAWAI",
            AgendaRapatAttendance.ATTENDANCE_KEY == attendance_key,
        )
        .first()
    )
    if existing:
        return existing, False

    nip_or_finger = str(nip_or_finger or "").strip() or None
    signature_path = _save_guest_signature(
        event,
        attendance_key,
        signature_data,
    )

    now = jakarta_now()
    row = AgendaRapatAttendance(
        EVENT_ID=event.EVENT_ID,
        ATTENDEE_TYPE="NON_PEGAWAI",
        ATTENDANCE_KEY=attendance_key,
        NIP=nip_or_finger,
        NAME=normalize_display_name(name_raw),
        NAME_RAW=name_raw,
        EMAIL=email,
        SIGNATURE_PATH=signature_path,
        SCANNED_DATE=now,
        METHOD=method,
        STATUS="HADIR",
    )
    db.session.add(row)
    db.session.commit()
    return row, True


def record_attendance(event, nip, method="QR"):
    """Backward-compatible employee attendance wrapper."""
    return record_employee_attendance(event, nip, method)


def _employee_identity(pegawai):
    nip = (pegawai.NIP or "").strip()
    finger_id = (pegawai.FINGER_ID or "").strip()
    return nip or finger_id or "-"


def _signature_path(pegawai):
    root = Path(Config.HRIS_TTD_ROOT)
    candidates = []
    nip = (pegawai.NIP or "").strip()
    finger_id = (pegawai.FINGER_ID or "").strip()

    if nip:
        candidates.append(root / f"{nip}.png")
    if finger_id:
        candidates.append(root / f"{finger_id}.png")

    for path in candidates:
        if path.is_file():
            return path
    return None


def _guest_signature_path(attendance):
    if not attendance.SIGNATURE_PATH:
        return None

    root = Path(Config.HRIS_DATA_ROOT).resolve()
    target = (root / attendance.SIGNATURE_PATH).resolve()
    if root != target and root not in target.parents:
        return None
    return target if target.is_file() else None


def generate_daftar_hadir_pdf(event):
    rows = attendance_rows(event.EVENT_ID)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Daftar Hadir - {event.TITLE}",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "AttendanceTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        alignment=1,
        spaceAfter=10,
    )
    normal = ParagraphStyle(
        "AttendanceNormal",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )

    meta = get_meta(event.EVENT_ID)
    organizer = None
    if meta:
        organizer = Pegawai.query.filter(Pegawai.NIP == meta.ORGANIZER_NIP).first()

    story = [
        Paragraph("DAFTAR HADIR RAPAT", title),
        Paragraph(f"<b>Judul Rapat:</b> {escape(event.TITLE or '-')}", normal),
        Paragraph(
            f"<b>Hari / Tanggal:</b> {event.START_DATE.strftime('%A, %d-%m-%Y') if event.START_DATE else '-'}",
            normal,
        ),
        Paragraph(
            f"<b>Waktu:</b> {event.START_DATE.strftime('%H:%M') if event.START_DATE else '-'}"
            f" - {event.END_DATE.strftime('%H:%M') if event.END_DATE else '-'} WIB",
            normal,
        ),
        Paragraph(f"<b>Tempat:</b> {escape(event.LOCATION or '-')}", normal),
        Paragraph(
            f"<b>Pimpinan Rapat:</b> {escape(organizer.NAMA if organizer else (meta.ORGANIZER_NIP if meta else '-'))}",
            normal,
        ),
        Spacer(1, 7 * mm),
    ]

    data = [["No.", "Nama", "NIP", "Email", "Tanda Tangan"]]

    for index, item in enumerate(rows, start=1):
        signature = item["signature_path"]
        if signature:
            image = Image(str(signature), width=27 * mm, height=12 * mm)
            image.hAlign = "CENTER"
            signature_cell = image
        else:
            signature_cell = Paragraph("__________________", normal)

        data.append([
            str(index),
            Paragraph(escape(item["display_name"] or "-"), normal),
            Paragraph(escape(item["identity"] or "-"), normal),
            Paragraph(escape(item["email"] or "-"), normal),
            signature_cell,
        ])

    if len(data) == 1:
        data.append([
            "-",
            Paragraph("Belum ada peserta yang tercatat hadir.", normal),
            "-",
            "-",
            Paragraph("__________________", normal),
        ])

    table = Table(
        data,
        colWidths=[10 * mm, 48 * mm, 40 * mm, 50 * mm, 35 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef5")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (4, 0), (4, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    story.append(table)
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            f"Dicetak dari HRIS Reborn · Jumlah hadir: {len(rows)} orang",
            ParagraphStyle("Footer", parent=normal, fontSize=8, textColor=colors.grey),
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer
