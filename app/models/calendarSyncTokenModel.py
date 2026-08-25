from app import db


class CalendarSyncToken(db.Model):

    __tablename__ = "CALENDAR_SYNC_TOKEN"


    ID = db.Column(
        "ID",
        db.BigInteger,
        primary_key=True
    )


    NIP = db.Column(
        "NIP",
        db.String(30),
        nullable=False
    )


    TOKEN = db.Column(
        "TOKEN",
        db.String(150),
        unique=True,
        nullable=False
    )


    IS_ACTIVE = db.Column(
        "IS_ACTIVE",
        db.String(1)
    )


    CREATED_DATE = db.Column(
        "CREATED_DATE",
        db.DateTime
    )


    LAST_SYNC = db.Column(
        "LAST_SYNC",
        db.DateTime
    )
