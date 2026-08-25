"""
HRIS REBORN
Calendar Event Service

Business Layer:

- Create Event
- Participant Management
- Notification Generator
- Audit Trail
"""

from datetime import datetime
import json

from app import db

from app.models.calendarEventModel import CalendarEvent
from app.models.calendarParticipantModel import CalendarParticipant
from app.models.calendarNotificationModel import CalendarNotification
from app.models.calendarAuditModel import CalendarAuditLog



def create_event(data, user):

    try:

        now = datetime.utcnow()


        # ====================================================
        # 1. CREATE EVENT
        # ====================================================

        event = CalendarEvent(

            TITLE=data.get(
                "title"
            ),

            DESCRIPTION=data.get(
                "description"
            ),

            START_DATE=data.get(
                "start_date"
            ),

            END_DATE=data.get(
                "end_date"
            ),

            LOCATION=data.get(
                "location"
            ),

            CATEGORY_ID=data.get(
                "category_id"
            ),

            EVENT_TYPE=data.get(
                "event_type",
                "MANUAL"
            ),

            REFERENCE_ID=data.get(
                "reference_id"
            ),

            SOURCE=data.get(
                "source",
                "MANUAL"
            ),

            STATUS=data.get(
                "status",
                "PLAN"
            ),

            CREATED_BY=user,

            CREATED_DATE=now,

            UPDATE_BY=user,

            UPDATE_DATE=now

        )


        db.session.add(event)

        db.session.flush()



        # ====================================================
        # 2. CREATE PARTICIPANT
        # ====================================================

        participants = data.get(
            "participants",
            []
        )


        for item in participants:

            participant = CalendarParticipant(

                EVENT_ID=event.EVENT_ID,

                NIP=item.get(
                    "nip"
                ),

                ROLE=item.get(
                    "role",
                    "PESERTA"
                ),

                STATUS="INVITED",

                CREATED_DATE=now

            )


            db.session.add(
                participant
            )


            # ================================================
            # CREATE NOTIFICATION
            # ================================================

            notif = CalendarNotification(

                EVENT_ID=event.EVENT_ID,

                NIP=item.get(
                    "nip"
                ),

                MESSAGE=(
                    f"Agenda baru: {event.TITLE}"
                ),

                READ_STATUS="N",

                SENT_DATE=None

            )


            db.session.add(
                notif
            )


        # ====================================================
        # 3. AUDIT LOG
        # ====================================================

        audit = CalendarAuditLog(

            EVENT_ID=event.EVENT_ID,

            ACTION="CREATE",

            OLD_VALUE=None,

            NEW_VALUE=json.dumps(
                data,
                default=str
            ),

            UPDATE_BY=user,

            UPDATE_DATE=now

        )


        db.session.add(
            audit
        )


        db.session.commit()


        return event


    except Exception:

        db.session.rollback()

        raise




def get_event(event_id):

    return (

        CalendarEvent.query

        .filter(
            CalendarEvent.EVENT_ID == event_id
        )

        .first()

    )
