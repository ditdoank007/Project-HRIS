from datetime import datetime

from app import db


class AgendaRapatAttendance(db.Model):
    __tablename__ = "AGENDA_RAPAT_KEHADIRAN"

    ATTENDANCE_ID = db.Column("ATTENDANCE_ID", db.BigInteger, primary_key=True, autoincrement=True)
    EVENT_ID = db.Column("EVENT_ID", db.BigInteger, nullable=False)
    ATTENDEE_TYPE = db.Column("ATTENDEE_TYPE", db.String(20), nullable=False, default="PEGAWAI")
    ATTENDANCE_KEY = db.Column("ATTENDANCE_KEY", db.String(100), nullable=True)
    NIP = db.Column("NIP", db.String(50, collation="utf8mb4_unicode_ci"), nullable=True)
    NAME = db.Column("NAME", db.String(150), nullable=True)
    NAME_RAW = db.Column("NAME_RAW", db.String(150), nullable=True)
    EMAIL = db.Column("EMAIL", db.String(255), nullable=True)
    SIGNATURE_PATH = db.Column("SIGNATURE_PATH", db.String(500), nullable=True)
    SCANNED_DATE = db.Column("SCANNED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
    METHOD = db.Column("METHOD", db.String(30), nullable=False, default="QR")
    STATUS = db.Column("STATUS", db.String(20), nullable=False, default="HADIR")
