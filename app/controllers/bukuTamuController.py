import base64
import io
import os
import re
import secrets
from datetime import datetime, timedelta

import qrcode
from flask import jsonify, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
)

from app import db
from config import Config
from app.models.bukuTamuModel import BukuTamu, BukuTamuEntry
from app.models.unitKerjaModel import MfUnitKerja
from app.models.pegawaiModel import Pegawai


def _now():
    return datetime.now()


def _calendar_public_url(token):
    base = (getattr(Config, "CALENDAR_PUBLIC_BASE_URL", None) or "https://calendar.sarsurabaya.id").rstrip("/")
    return f"{base}/buku-tamu?token={token}"


def _active_units():
    rows = MfUnitKerja.query.order_by(
        MfUnitKerja.URUT_REPORT.asc(),
        MfUnitKerja.NAMA_UNIT_KERJA.asc()
    ).all()
    active = [x for x in rows if str(x.IS_AKTIF or "").strip().upper() in {"Y", "1", "TRUE"}]
    return active or rows


def _find_book(book_id):
    return BukuTamu.query.get(int(book_id))


def _book_payload(book):
    return {
        "id": book.ID,
        "judul": book.JUDUL,
        "unit_kerja_id": book.ID_UNIT_KERJA,
        "unit_kerja": book.UNIT_KERJA_NAME,
        "qr_token": book.QR_TOKEN,
        "qr_url": _calendar_public_url(book.QR_TOKEN),
        "qr_active": book.QR_ACTIVE == "Y",
    }


def buku_tamu():
    now = _now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    books = BukuTamu.query.order_by(BukuTamu.UNIT_KERJA_NAME.asc(), BukuTamu.JUDUL.asc()).all()

    month_count = BukuTamuEntry.query.filter(
        BukuTamuEntry.SCANNED_DATE >= month_start,
        BukuTamuEntry.SCANNED_DATE < next_month,
    ).count()
    year_count = BukuTamuEntry.query.filter(
        BukuTamuEntry.SCANNED_DATE >= year_start,
        BukuTamuEntry.SCANNED_DATE < year_start.replace(year=year_start.year + 1),
    ).count()
    today_count = BukuTamuEntry.query.filter(
        BukuTamuEntry.SCANNED_DATE >= now.replace(hour=0, minute=0, second=0, microsecond=0),
        BukuTamuEntry.SCANNED_DATE < now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
    ).count()

    return render_template(
        "pages/dashboard_1/Buku Tamu.html",
        books=books,
        month_count=month_count,
        year_count=year_count,
        today_count=today_count,
        active_books=sum(1 for x in books if x.QR_ACTIVE == "Y"),
        month_label=now.strftime("%B %Y"),
        year=now.year,
    )


def buku_tamu_buat():
    return render_template("pages/dashboard_1/Buku Tamu Buat.html", units=_active_units())


def buku_tamu_rekap():
    now = _now()
    return render_template(
        "pages/dashboard_1/Buku Tamu Rekap.html",
        units=_active_units(),
        year=now.year,
        month=now.month,
    )


def api_buku_tamu_save():
    payload = request.get_json(silent=True) or {}
    judul = str(payload.get("judul") or "").strip()
    unit_id = str(payload.get("unit_kerja_id") or "").strip()
    if not judul:
        return jsonify({"status": "error", "message": "Judul Buku Tamu wajib diisi."}), 400
    if not unit_id:
        return jsonify({"status": "error", "message": "Unit Kerja wajib dipilih."}), 400

    unit = MfUnitKerja.query.filter(MfUnitKerja.UNIT_KERJA_ID == unit_id).first()
    if not unit:
        return jsonify({"status": "error", "message": "Unit Kerja tidak ditemukan."}), 404

    token = secrets.token_urlsafe(32)
    while BukuTamu.query.filter_by(QR_TOKEN=token).first():
        token = secrets.token_urlsafe(32)

    now = _now()
    row = BukuTamu(
        JUDUL=judul[:150],
        ID_UNIT_KERJA=unit_id,
        UNIT_KERJA_NAME=(unit.NAMA_UNIT_KERJA or "").strip()[:100],
        QR_TOKEN=token,
        QR_ACTIVE="Y",
        CREATED_BY=request.headers.get("X-User-NIP") or "system",
        CREATED_DATE=now,
        UPDATE_DATE=now,
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"status": "success", "data": _book_payload(row)})


def api_buku_tamu_list():
    rows = BukuTamu.query.order_by(BukuTamu.UNIT_KERJA_NAME.asc(), BukuTamu.JUDUL.asc()).all()
    return jsonify({"status": "success", "data": [_book_payload(x) for x in rows]})


def api_buku_tamu_qr(book_id):
    book = _find_book(book_id)
    if not book:
        return jsonify({"status": "error", "message": "Buku Tamu tidak ditemukan."}), 404

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(_calendar_public_url(book.QR_TOKEN))
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return send_file(output, mimetype="image/png", max_age=0)


def api_buku_tamu_preview(book_id):
    book = _find_book(book_id)
    if not book:
        return jsonify({"status": "error", "message": "Buku Tamu tidak ditemukan."}), 404
    return jsonify({"status": "success", "data": _book_payload(book)})


def api_buku_tamu_rekap():
    try:
        year = int(request.args.get("year") or _now().year)
        month = int(request.args.get("month") or _now().month)
    except ValueError:
        return jsonify({"status": "error", "message": "Periode tidak valid."}), 400

    unit_id = str(request.args.get("unit_kerja_id") or "").strip()
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

    query = db.session.query(BukuTamuEntry, BukuTamu).join(
        BukuTamu, BukuTamu.ID == BukuTamuEntry.BUKU_TAMU_ID
    ).filter(
        BukuTamuEntry.SCANNED_DATE >= start,
        BukuTamuEntry.SCANNED_DATE < end,
    )
    if unit_id:
        query = query.filter(BukuTamu.ID_UNIT_KERJA == unit_id)

    rows = query.order_by(BukuTamuEntry.SCANNED_DATE.asc(), BukuTamuEntry.ID.asc()).all()
    data = []
    for entry, book in rows:
        data.append({
            "id": entry.ID,
            "tanggal": entry.SCANNED_DATE.strftime("%d-%m-%Y"),
            "jam": entry.SCANNED_DATE.strftime("%H:%M"),
            "nama": entry.NAMA_LENGKAP,
            "instansi": entry.INSTANSI,
            "no_hp": entry.NO_HP,
            "keperluan": entry.KEPERLUAN,
            "keterangan": entry.KETERANGAN or "",
            "pegawai": entry.PEGAWAI_NAMA or "",
            "unit_kerja": book.UNIT_KERJA_NAME,
            "judul": book.JUDUL,
        })
    return jsonify({"status": "success", "data": data, "total": len(data)})


def _safe_filename(value):
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "unit"


def _signature_absolute(path):
    if not path:
        return None
    return os.path.join(getattr(Config, "HRIS_DATA_ROOT", "/mnt/hris-data"), path)


def export_buku_tamu_pdf():
    try:
        year = int(request.args.get("year") or _now().year)
        month = int(request.args.get("month") or _now().month)
    except ValueError:
        return jsonify({"status": "error", "message": "Periode tidak valid."}), 400

    unit_id = str(request.args.get("unit_kerja_id") or "").strip()
    if not unit_id:
        return jsonify({"status": "error", "message": "Unit Kerja wajib dipilih untuk ekspor PDF."}), 400

    unit = MfUnitKerja.query.filter(MfUnitKerja.UNIT_KERJA_ID == unit_id).first()
    if not unit:
        return jsonify({"status": "error", "message": "Unit Kerja tidak ditemukan."}), 404

    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    rows = db.session.query(BukuTamuEntry, BukuTamu).join(
        BukuTamu, BukuTamu.ID == BukuTamuEntry.BUKU_TAMU_ID
    ).filter(
        BukuTamuEntry.SCANNED_DATE >= start,
        BukuTamuEntry.SCANNED_DATE < end,
        BukuTamu.ID_UNIT_KERJA == unit_id,
    ).order_by(BukuTamuEntry.SCANNED_DATE.asc(), BukuTamuEntry.ID.asc()).all()

    safe_unit = _safe_filename(unit.NAMA_UNIT_KERJA or unit_id)
    filename = f"buku-tamu-{safe_unit}-{year}-{month:02d}.pdf"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=8*mm,
        leftMargin=8*mm,
        topMargin=8*mm,
        bottomMargin=8*mm,
        title=f"Buku Tamu {unit.NAMA_UNIT_KERJA} {year}-{month:02d}",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="BTTitle", parent=styles["Title"], alignment=TA_CENTER,
        fontSize=16, leading=19, spaceAfter=3*mm,
    ))
    styles.add(ParagraphStyle(
        name="BTSub", parent=styles["Normal"], alignment=TA_CENTER,
        fontSize=9, leading=11, textColor=colors.HexColor("#4b5563"), spaceAfter=5*mm,
    ))
    styles.add(ParagraphStyle(
        name="BTCell", parent=styles["Normal"], fontSize=6.8, leading=8,
    ))

    story = [
        Paragraph("BUKU TAMU", styles["BTTitle"]),
        Paragraph(
            f"{unit.NAMA_UNIT_KERJA} · Periode {month:02d}-{year}",
            styles["BTSub"]
        ),
    ]

    header = ["No", "Tanggal", "Jam", "Nama Lengkap", "Instansi / Organisasi",
              "No. HP", "Keperluan", "Keterangan", "Bertemu Pegawai"]
    table_data = [header]
    for i, (entry, _book) in enumerate(rows, 1):
        table_data.append([
            str(i),
            entry.SCANNED_DATE.strftime("%d-%m-%Y"),
            entry.SCANNED_DATE.strftime("%H:%M"),
            Paragraph(entry.NAMA_LENGKAP or "-", styles["BTCell"]),
            Paragraph(entry.INSTANSI or "-", styles["BTCell"]),
            Paragraph(entry.NO_HP or "-", styles["BTCell"]),
            Paragraph(entry.KEPERLUAN or "-", styles["BTCell"]),
            Paragraph(entry.KETERANGAN or "-", styles["BTCell"]),
            Paragraph(entry.PEGAWAI_NAMA or "-", styles["BTCell"]),
        ])

    col_widths = [8*mm, 23*mm, 15*mm, 34*mm, 40*mm, 25*mm, 45*mm, 42*mm, 38*mm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f97316")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff7ed")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        f"Total tamu: {len(rows)} · Dicetak {datetime.now().strftime('%d-%m-%Y %H:%M')} WIB",
        styles["BTSub"]
    ))
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename, max_age=0)


def api_buku_tamu_pegawai_search():
    q = str(request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"status": "success", "data": []})
    rows = Pegawai.query.filter(
        (Pegawai.NAMA.ilike(f"%{q}%")) | (Pegawai.NIP.ilike(f"%{q}%"))
    ).filter(
        (Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR != "Y")
    ).order_by(Pegawai.NAMA.asc()).limit(15).all()
    return jsonify({
        "status": "success",
        "data": [{"nip": x.NIP, "nama": x.NAMA, "jabatan": x.JABATAN, "unit_kerja": x.UNIT_KERJA} for x in rows]
    })


def _internal_book(token):
    return BukuTamu.query.filter(
        BukuTamu.QR_TOKEN == token,
        BukuTamu.QR_ACTIVE == "Y",
    ).first()


def _validate_public_payload(payload):
    fields = {
        "nama": "Nama Lengkap",
        "instansi": "Instansi / Organisasi",
        "no_hp": "No. Handphone",
        "keperluan": "Keperluan",
    }
    for key, label in fields.items():
        if not str(payload.get(key) or "").strip():
            return f"{label} wajib diisi."
    return None


def _save_signature(token, signature_data):
    if not signature_data or not signature_data.startswith("data:image/png;base64,"):
        raise ValueError("Tanda tangan tidak valid.")
    raw = base64.b64decode(signature_data.split(",", 1)[1], validate=True)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Ukuran tanda tangan terlalu besar.")
    safe_token = re.sub(r"[^A-Za-z0-9_-]", "", token)
    rel = f"TAMU/{datetime.now():%Y/%m/%d}/{safe_token}.png"
    absolute = os.path.join(getattr(Config, "HRIS_DATA_ROOT", "/mnt/hris-data"), rel)
    os.makedirs(os.path.dirname(absolute), exist_ok=True)
    with open(absolute, "wb") as fh:
        fh.write(raw)
    return rel


def _require_calendar_internal():
    expected = getattr(Config, "CALENDAR_INTERNAL_API_KEY", None)
    supplied = request.headers.get("X-Calendar-Internal-Key")
    if not expected or supplied != expected:
        return jsonify({"status": "error", "message": "Unauthorized."}), 401
    return None


def api_buku_tamu_internal_info():
    unauthorized = _require_calendar_internal()
    if unauthorized:
        return unauthorized
    token = str(request.args.get("token") or "").strip()
    book = _internal_book(token)
    if not book:
        return jsonify({"status": "error", "message": "QR Buku Tamu tidak valid atau sudah dinonaktifkan."}), 404
    return jsonify({"status": "success", "data": {
        "judul": book.JUDUL,
        "unit_kerja": book.UNIT_KERJA_NAME,
        "qr_active": True,
    }})


def api_buku_tamu_internal_pegawai():
    unauthorized = _require_calendar_internal()
    if unauthorized:
        return unauthorized
    q = str(request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"status": "success", "data": []})
    rows = Pegawai.query.filter(
        (Pegawai.NAMA.ilike(f"%{q}%")) | (Pegawai.NIP.ilike(f"%{q}%"))
    ).filter(
        (Pegawai.IS_KELUAR.is_(None)) | (Pegawai.IS_KELUAR != "Y")
    ).order_by(Pegawai.NAMA.asc()).limit(15).all()
    return jsonify({"status": "success", "data": [
        {"nip": x.NIP, "nama": x.NAMA, "jabatan": x.JABATAN, "unit_kerja": x.UNIT_KERJA}
        for x in rows
    ]})


def api_buku_tamu_internal_submit():
    unauthorized = _require_calendar_internal()
    if unauthorized:
        return unauthorized
    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token") or "").strip()
    book = _internal_book(token)
    if not book:
        return jsonify({"status": "error", "message": "QR Buku Tamu tidak valid atau sudah dinonaktifkan."}), 404

    error = _validate_public_payload(payload)
    if error:
        return jsonify({"status": "error", "message": error}), 400

    try:
        signature_path = _save_signature(token, str(payload.get("signature_data") or ""))
        nip = str(payload.get("pegawai_nip") or "").strip() or None
        nama_pegawai = str(payload.get("pegawai_nama") or "").strip() or None
        keterangan = str(payload.get("keterangan") or "").strip()[:255] or None
        if nip and not nama_pegawai:
            pegawai = Pegawai.query.filter_by(NIP=nip).first()
            nama_pegawai = pegawai.NAMA if pegawai else None

        now = _now()
        entry = BukuTamuEntry(
            BUKU_TAMU_ID=book.ID,
            SCANNED_DATE=now,
            NAMA_LENGKAP=str(payload["nama"]).strip()[:150],
            INSTANSI=str(payload["instansi"]).strip()[:150],
            NO_HP=str(payload["no_hp"]).strip()[:50],
            KEPERLUAN=str(payload["keperluan"]).strip()[:255],
            KETERANGAN=keterangan,
            PEGAWAI_NIP=nip,
            PEGAWAI_NAMA=nama_pegawai,
            TANDA_TANGAN_PATH=signature_path,
            CREATED_IP=request.headers.get("X-Forwarded-For", request.remote_addr),
            USER_AGENT=(request.headers.get("User-Agent") or "")[:500],
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({"status": "success", "message": "Terima kasih. Buku Tamu berhasil disimpan."})
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menyimpan Buku Tamu."}), 500
