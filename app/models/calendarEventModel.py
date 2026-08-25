from app import db


class CalendarEvent(db.Model):

    __tablename__ = "CALENDAR_EVENT"


    EVENT_ID = db.Column(
        "EVENT_ID",
        db.BigInteger,
        primary_key=True
    )


    TITLE = db.Column(
        "TITLE",
        db.String(200),
        nullable=False
    )


    DESCRIPTION = db.Column(
        "DESCRIPTION",
        db.Text
    )


    START_DATE = db.Column(
        "START_DATE",
        db.DateTime,
        nullable=False
    )


    END_DATE = db.Column(
        "END_DATE",
        db.DateTime
    )


    LOCATION = db.Column(
        "LOCATION",
        db.String(200)
    )


    CATEGORY_ID = db.Column(
        "CATEGORY_ID",
        db.Integer
    )


    EVENT_TYPE = db.Column(
        "EVENT_TYPE",
        db.String(50)
    )


    REFERENCE_ID = db.Column(
        "REFERENCE_ID",
        db.String(100)
    )


    SOURCE = db.Column(
        "SOURCE",
        db.String(50)
    )


    STATUS = db.Column(
        "STATUS",
        db.String(20)
    )


    CREATED_BY = db.Column(
        "CREATED_BY",
        db.String(50)
    )


    CREATED_DATE = db.Column(
        "CREATED_DATE",
        db.DateTime
    )


    UPDATE_BY = db.Column(
        "UPDATE_BY",
        db.String(50)
    )


    UPDATE_DATE = db.Column(
        "UPDATE_DATE",
        db.DateTime
    )


    def to_dict(self):

        return {

            "event_id": self.EVENT_ID,

            "title": self.TITLE,

            "description": self.DESCRIPTION,

            "start": (
                self.START_DATE.isoformat()
                if self.START_DATE else None
            ),

            "end": (
                self.END_DATE.isoformat()
                if self.END_DATE else None
            ),

            "location": self.LOCATION,

            "event_type": self.EVENT_TYPE,

            "reference_id": self.REFERENCE_ID,

            "status": self.STATUS

        }
