from datetime import datetime

from app import db


class GoogleCalendarConfig(db.Model):
    __tablename__ = 'GOOGLE_CALENDAR_CONFIG'

    ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    GOOGLE_EMAIL = db.Column(db.String(255), nullable=True)
    CALENDAR_ID = db.Column(db.String(255), nullable=False)
    API_KEY = db.Column(db.String(255), nullable=True)
    IS_ACTIVE = db.Column(db.String(1), nullable=False, default='Y')
    LAST_SYNC = db.Column(db.DateTime, nullable=True)
    SYNC_STATUS = db.Column(db.String(20), nullable=True)
    SYNC_MESSAGE = db.Column(db.String(500), nullable=True)
    CREATED_BY = db.Column(db.String(50), nullable=True)
    CREATED_DATE = db.Column(db.DateTime, nullable=True)
    UPDATE_BY = db.Column(db.String(50), nullable=True)
    UPDATE_DATE = db.Column(db.DateTime, nullable=True)
