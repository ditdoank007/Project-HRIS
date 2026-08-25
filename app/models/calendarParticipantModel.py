from app import db


class CalendarParticipant(db.Model):

    __tablename__ = "CALENDAR_PARTICIPANT"


    ID = db.Column(
        "ID",
        db.BigInteger,
        primary_key=True
    )


    EVENT_ID = db.Column(
        "EVENT_ID",
        db.BigInteger,
        nullable=False
    )


    NIP = db.Column(
        "NIP",
        db.String(30),
        nullable=False
    )


    ROLE = db.Column(
        "ROLE",
        db.String(30)
    )


    STATUS = db.Column(
        "STATUS",
        db.String(30)
    )


    CREATED_DATE = db.Column(
        "CREATED_DATE",
        db.DateTime
    )
