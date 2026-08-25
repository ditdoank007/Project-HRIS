"""
HRIS REBORN
Calendar ICS Service

Generate iCalendar feed
untuk sinkronisasi mobile device.

Support:
- Google Calendar
- Apple Calendar
- Outlook
"""

from datetime import datetime


from app.models.calendarEventModel import CalendarEvent
from app.models.calendarSyncTokenModel import CalendarSyncToken
from app.models.calendarParticipantModel import CalendarParticipant



def get_events_by_token(token):

    sync = (
        CalendarSyncToken.query
        .filter(
            CalendarSyncToken.TOKEN == token,
            CalendarSyncToken.IS_ACTIVE == 'Y'
        )
        .first()
    )


    if not sync:
        return []


    event_ids = [

        x.EVENT_ID

        for x in CalendarParticipant.query.filter(
            CalendarParticipant.NIP == sync.NIP
        ).all()

    ]


    if not event_ids:
        return []


    return (

        CalendarEvent.query

        .filter(
            CalendarEvent.EVENT_ID.in_(event_ids)
        )

        .order_by(
            CalendarEvent.START_DATE.asc()
        )

        .all()

    )



def generate_ics(events):

    lines = [

        "BEGIN:VCALENDAR",

        "VERSION:2.0",

        "PRODID:-//HRIS REBORN//Calendar//ID",

        "CALSCALE:GREGORIAN"

    ]


    for event in events:


        start = (
            event.START_DATE
            .strftime("%Y%m%dT%H%M%S")
        )


        end = (

            event.END_DATE.strftime(
                "%Y%m%dT%H%M%S"
            )

            if event.END_DATE

            else start

        )


        lines.extend([

            "BEGIN:VEVENT",

            f"UID:{event.EVENT_ID}@hris",

            f"DTSTART:{start}",

            f"DTEND:{end}",

            f"SUMMARY:{event.TITLE}",

            f"DESCRIPTION:{event.DESCRIPTION or ''}",

            f"LOCATION:{event.LOCATION or ''}",

            "END:VEVENT"

        ])



    lines.append(
        "END:VCALENDAR"
    )


    return "\r\n".join(lines)
