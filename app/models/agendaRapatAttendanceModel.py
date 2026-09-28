from datetime import datetime

from app import db


class AgendaRapatAttendance(db.Model):
    __tablename__ = "AGENDA_RAPAT_KEHADIRAN"

    ATTENDANCE_ID = db.Column("ATTENDANCE_ID", db.BigInteger, primary_key=True, autoincrement=True)
    EVENT_ID = db.Column("EVENT_ID", db.BigInteger, nullable=False)
    NIP = db.Column("NIP", db.String(50), nullable=False)
    SCANNED_DATE = db.Column("SCANNED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
    METHOD = db.Column("METHOD", db.String(30), nullable=False, default="QR")
    STATUS = db.Column("STATUS", db.String(20), nullable=False, default="HADIR")
