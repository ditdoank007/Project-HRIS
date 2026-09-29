from datetime import datetime

from app import db


class KesamaptaanKehadiran(db.Model):
    __tablename__ = "KESAMAPTAAN_KEHADIRAN"

    KEHADIRAN_ID = db.Column("KEHADIRAN_ID", db.BigInteger, primary_key=True, autoincrement=True)
    KEGIATAN_ID = db.Column("KEGIATAN_ID", db.BigInteger, nullable=False)
    NIP = db.Column("NIP", db.String(50, collation="utf8mb4_unicode_ci"), nullable=False)
    NAMA = db.Column("NAMA", db.String(150), nullable=False)
    SIGNATURE_PATH = db.Column("SIGNATURE_PATH", db.String(500), nullable=True)
    SCANNED_DATE = db.Column("SCANNED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
    STATUS = db.Column("STATUS", db.String(20), nullable=False, default="HADIR")
