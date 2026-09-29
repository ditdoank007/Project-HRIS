from datetime import datetime

from app import db


class KesamaptaanKegiatan(db.Model):
    __tablename__ = "KESAMAPTAAN_KEGIATAN"

    KEGIATAN_ID = db.Column("KEGIATAN_ID", db.BigInteger, primary_key=True, autoincrement=True)
    JUDUL = db.Column("JUDUL", db.String(200), nullable=False)
    HARI = db.Column("HARI", db.String(20), nullable=False)
    TANGGAL = db.Column("TANGGAL", db.Date, nullable=False)
    JAM = db.Column("JAM", db.Time, nullable=False)
    QR_TOKEN = db.Column("QR_TOKEN", db.String(120), nullable=False, unique=True)
    QR_ACTIVE = db.Column("QR_ACTIVE", db.String(1), nullable=False, default="Y")
    STATUS = db.Column("STATUS", db.String(20), nullable=False, default="TERJADWAL")
    PDF_PATH = db.Column("PDF_PATH", db.String(500), nullable=True)
    PDF_SHA256 = db.Column("PDF_SHA256", db.String(64), nullable=True)
    CREATED_BY = db.Column("CREATED_BY", db.String(50), nullable=False)
    CREATED_DATE = db.Column("CREATED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
    UPDATE_BY = db.Column("UPDATE_BY", db.String(50), nullable=True)
    UPDATE_DATE = db.Column("UPDATE_DATE", db.DateTime, nullable=True)
