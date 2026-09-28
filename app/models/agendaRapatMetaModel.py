from datetime import datetime

from app import db


class AgendaRapatMeta(db.Model):
    __tablename__ = "AGENDA_RAPAT_META"

    EVENT_ID = db.Column("EVENT_ID", db.BigInteger, primary_key=True)
    ORGANIZER_NIP = db.Column("ORGANIZER_NIP", db.String(50, collation="utf8mb4_unicode_ci"), nullable=False)
    QR_TOKEN = db.Column("QR_TOKEN", db.String(100), nullable=False, unique=True)
    QR_ACTIVE = db.Column("QR_ACTIVE", db.String(1), nullable=False, default="Y")
    CREATED_BY = db.Column("CREATED_BY", db.String(50), nullable=False)
    CREATED_DATE = db.Column("CREATED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
    UPDATE_BY = db.Column("UPDATE_BY", db.String(50))
    UPDATE_DATE = db.Column("UPDATE_DATE", db.DateTime)
