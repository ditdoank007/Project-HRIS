from app import db


class CalendarCategory(db.Model):

    __tablename__ = "CALENDAR_CATEGORY"


    ID = db.Column(
        "ID",
        db.Integer,
        primary_key=True
    )


    CODE = db.Column(
        "CODE",
        db.String(50),
        unique=True,
        nullable=False
    )


    NAME = db.Column(
        "NAME",
        db.String(100),
        nullable=False
    )


    COLOR = db.Column(
        "COLOR",
        db.String(20)
    )


    IS_ACTIVE = db.Column(
        "IS_ACTIVE",
        db.String(1)
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
            "id": self.ID,
            "code": self.CODE,
            "name": self.NAME,
            "color": self.COLOR,
            "is_active": self.IS_ACTIVE
        }
