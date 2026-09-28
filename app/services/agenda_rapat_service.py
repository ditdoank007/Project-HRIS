"""
Business services for Agenda Rapat:
- QR attendance
- attendance listing
- Daftar Hadir PDF
- employee signature lookup
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from html import escape
import secrets

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
        CREATED_DATE=datetime.utcnow(),
    )
    db.session.add(meta)
    db.session.flush()
    return meta


def get_meta(event_id):
    return AgendaRapatMeta.query.filter_by(EVENT_ID=event_id).first()


def attendance_rows(event_id):
    rows = (
        db.session.query(AgendaRapatAttendance, Pegawai)
        .join(Pegawai, Pegawai.NIP == AgendaRapatAttendance.NIP)
        .filter(AgendaRapatAttendance.EVENT_ID == event_id)
        .filter(AgendaRapatAttendance.STATUS == "HADIR")
        .order_by(AgendaRapatAttendance.SCANNED_DATE.asc(), Pegawai.NAMA.asc())
        .all()
    )
    return [
        {
            "attendance": attendance,
            "pegawai": pegawai,
        }
        for attendance, pegawai in rows
    ]


def build_qr_svg(token):
    base_url = (Config.HRIS_PUBLIC_BASE_URL or request.host_url).rstrip("/")
    scan_url = f"{base_url}/rapat/scan/{token}"

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


def record_attendance(event, nip, method="QR"):
    pegawai = (
        Pegawai.query
        .filter(Pegawai.NIP == nip)
        .filter((Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR != "Y"))
        .first()
    )
    if not pegawai:
        raise ValueError("Data pegawai tidak ditemukan atau pegawai sudah tidak aktif.")

    meta = get_meta(event.EVENT_ID)
    if not meta or meta.QR_ACTIVE != "Y":
        raise ValueError("QR absensi rapat sudah tidak aktif.")

    existing = AgendaRapatAttendance.query.filter_by(
        EVENT_ID=event.EVENT_ID,
        NIP=nip,
    ).first()

    if existing:
        return existing, pegawai, False

    row = AgendaRapatAttendance(
        EVENT_ID=event.EVENT_ID,
        NIP=nip,
        SCANNED_DATE=datetime.utcnow(),
        METHOD=method,
        STATUS="HADIR",
    )
    db.session.add(row)
    db.session.flush()

    # Pegawai yang scan otomatis menjadi peserta aktual.
    participant = CalendarParticipant.query.filter_by(
        EVENT_ID=event.EVENT_ID,
        NIP=nip,
    ).first()
    if not participant:
        db.session.add(
            CalendarParticipant(
                EVENT_ID=event.EVENT_ID,
                NIP=nip,
                ROLE="HADIR",
                STATUS="ATTENDED",
                CREATED_DATE=datetime.utcnow(),
            )
        )
    else:
        participant.STATUS = "ATTENDED"

    db.session.commit()
    return row, pegawai, True


def _employee_identity(pegawai):
    """
    Identitas yang ditampilkan pada Daftar Hadir.
    PNS menggunakan NIP; pegawai non-PNS menggunakan FingerID
    (sesuai aturan HRIS: NIP = FingerID untuk non-PNS).
    """
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


def generate_daftar_hadir_pdf(event):
    rows = attendance_rows(event.EVENT_ID)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
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
        fontSize=9,
        leading=12,
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

    data = [["No", "Nama Pegawai", "NIP / FingerID", "Tanda Tangan"]]

    for index, item in enumerate(rows, start=1):
        pegawai = item["pegawai"]
        signature = _signature_path(pegawai)
        if signature:
            image = Image(str(signature), width=30 * mm, height=12 * mm)
            image.hAlign = "CENTER"
            signature_cell = image
        else:
            signature_cell = Paragraph("__________________", normal)

        data.append([
            str(index),
            Paragraph(escape(pegawai.NAMA or "-"), normal),
            Paragraph(escape(_employee_identity(pegawai)), normal),
            signature_cell,
        ])

    if len(data) == 1:
        data.append([
            "-",
            Paragraph("Belum ada pegawai yang tercatat hadir.", normal),
            "-",
            Paragraph("__________________", normal),
        ])

    table = Table(
        data,
        colWidths=[12 * mm, 62 * mm, 50 * mm, 48 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef5")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
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
