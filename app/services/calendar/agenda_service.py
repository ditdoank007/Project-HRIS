"""
HRIS REBORN
Calendar Agenda Query Service

Business Layer:

- Agenda Personal Pegawai
- Join Event
- Join Category
- Participant Status
"""

from app.models.calendarEventModel import CalendarEvent
from app.models.calendarParticipantModel import CalendarParticipant
from app.models.calendarCategoryModel import CalendarCategory



def get_my_agenda(nip):


    rows = (

        CalendarEvent.query

        .join(
            CalendarParticipant,
            CalendarEvent.EVENT_ID ==
            CalendarParticipant.EVENT_ID
        )

        .outerjoin(
            CalendarCategory,
            CalendarEvent.CATEGORY_ID ==
            CalendarCategory.ID
        )

        .filter(
            CalendarParticipant.NIP == nip
        )

        .order_by(
            CalendarEvent.START_DATE.asc()
        )

        .all()

    )


    return rows



def get_my_agenda_detail(nip):

    rows = (

        CalendarEvent.query

        .join(
            CalendarParticipant,
            CalendarEvent.EVENT_ID ==
            CalendarParticipant.EVENT_ID
        )

        .outerjoin(
            CalendarCategory,
            CalendarEvent.CATEGORY_ID ==
            CalendarCategory.ID
        )

        .filter(
            CalendarParticipant.NIP == nip
        )

        .with_entities(

            CalendarEvent.EVENT_ID,

            CalendarEvent.TITLE,

            CalendarEvent.DESCRIPTION,

            CalendarEvent.START_DATE,

            CalendarEvent.END_DATE,

            CalendarEvent.LOCATION,

            CalendarEvent.STATUS,

            CalendarEvent.EVENT_TYPE,

            CalendarCategory.CODE,

            CalendarCategory.NAME,

            CalendarCategory.COLOR.label(
                "category_color"
            ),

            CalendarParticipant.STATUS.label(
                "participant_status"
            )

        )

        .order_by(
            CalendarEvent.START_DATE.asc()
        )

        .all()

    )


    return rows


def get_user_agenda_detail(nip):

    rows = (

        CalendarEvent.query

        .join(
            CalendarParticipant,
            CalendarEvent.EVENT_ID ==
            CalendarParticipant.EVENT_ID
        )

        .outerjoin(
            CalendarCategory,
            CalendarEvent.CATEGORY_ID ==
            CalendarCategory.ID
        )

        .filter(
            CalendarParticipant.NIP == nip
        )

        .with_entities(

            CalendarEvent.EVENT_ID,

            CalendarEvent.TITLE,

            CalendarEvent.DESCRIPTION,

            CalendarEvent.START_DATE,

            CalendarEvent.END_DATE,

            CalendarEvent.LOCATION,

            CalendarEvent.STATUS,

            CalendarEvent.EVENT_TYPE,

            CalendarEvent.SOURCE,

            CalendarCategory.CODE,

            CalendarCategory.NAME,

            CalendarCategory.COLOR.label(
                "category_color"
            ),

            CalendarParticipant.STATUS.label(
                "participant_status"
            )

        )

        .order_by(
            CalendarEvent.START_DATE.asc()
        )

        .all()

    )


    return rows

