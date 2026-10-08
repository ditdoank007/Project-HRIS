from app import db


class CalendarNotification(db.Model):

    __tablename__ = "CALENDAR_NOTIFICATION"

    ID = db.Column("ID", db.BigInteger, primary_key=True)
    EVENT_ID = db.Column("EVENT_ID", db.BigInteger, nullable=True)
    NIP = db.Column("NIP", db.String(30), nullable=True)
    MESSAGE = db.Column("MESSAGE", db.String(255), nullable=True)
    READ_STATUS = db.Column("READ_STATUS", db.String(1), default="N")
    SENT_DATE = db.Column("SENT_DATE", db.DateTime, nullable=True)

    # Notification Center V1
    SOURCE_TYPE = db.Column("SOURCE_TYPE", db.String(30), nullable=True)
    SOURCE_ID = db.Column("SOURCE_ID", db.String(150), nullable=True)
    TITLE = db.Column("TITLE", db.String(200), nullable=True)
    URL = db.Column("URL", db.String(500), nullable=True)
    CREATED_DATE = db.Column("CREATED_DATE", db.DateTime, nullable=True)
    READ_DATE = db.Column("READ_DATE", db.DateTime, nullable=True)
    COMPLETED_DATE = db.Column("COMPLETED_DATE", db.DateTime, nullable=True)
    IS_ACTIVE = db.Column("IS_ACTIVE", db.String(1), default="Y")
