from app import db


class CalendarNotification(db.Model):

    __tablename__ = "CALENDAR_NOTIFICATION"


    ID = db.Column(
        "ID",
        db.BigInteger,
        primary_key=True
    )


    EVENT_ID = db.Column(
        "EVENT_ID",
        db.BigInteger
    )


    NIP = db.Column(
        "NIP",
        db.String(30)
    )


    MESSAGE = db.Column(
        "MESSAGE",
        db.String(255)
    )


    READ_STATUS = db.Column(
        "READ_STATUS",
        db.String(1)
    )


    SENT_DATE = db.Column(
        "SENT_DATE",
        db.DateTime
    )
