from app import db


class CalendarAuditLog(db.Model):

    __tablename__ = "CALENDAR_AUDIT_LOG"


    LOG_ID = db.Column(
        "LOG_ID",
        db.BigInteger,
        primary_key=True
    )


    EVENT_ID = db.Column(
        "EVENT_ID",
        db.BigInteger
    )


    ACTION = db.Column(
        "ACTION",
        db.String(50)
    )


    OLD_VALUE = db.Column(
        "OLD_VALUE",
        db.Text
    )


    NEW_VALUE = db.Column(
        "NEW_VALUE",
        db.Text
    )


    UPDATE_BY = db.Column(
        "UPDATE_BY",
        db.String(50)
    )


    UPDATE_DATE = db.Column(
        "UPDATE_DATE",
        db.DateTime
    )
