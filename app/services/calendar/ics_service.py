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

from datetime import date, timedelta

from app.models.calendarSyncTokenModel import CalendarSyncToken
from app.services.calendar.personal_calendar_service import (
    build_personal_calendar_events,
)


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

    # Feed kalender mobile mencakup histori HRIS mulai 2015
    # sampai tahun 2099 agar kalender tetap mencakup event
    # historis, saat ini, dan event mendatang.
    tanggal_awal = date(2015, 1, 1)
    tanggal_akhir = date(2100, 1, 1)

    _, events = build_personal_calendar_events(
        sync.NIP,
        tanggal_awal,
        tanggal_akhir,
    )

    return events


def _ics_escape(value):
    value = str(value or "")

    # Buang control character yang tidak valid untuk iCalendar.
    # Tab tetap dipertahankan; CR/LF ditangani sebagai escaped newline.
    value = "".join(
        char
        for char in value
        if char == "\t" or ord(char) >= 32
    )

    return (
        value
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def generate_ics(events):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//HRIS REBORN//Personal Calendar//ID",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:HRIS REBORN",
        "X-WR-TIMEZONE:Asia/Jakarta",
    ]

    for event in events:
        start_text = event.get("start")
        if not start_text:
            continue

        event_id = _ics_escape(event.get("id"))
        title = _ics_escape(event.get("title"))
        description = _ics_escape(event.get("description"))
        location = _ics_escape(event.get("location"))

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{event_id}@hris",
        ])

        if event.get("all_day", True):
            start = date.fromisoformat(start_text[:10])
            end_text = event.get("end") or start_text
            end = date.fromisoformat(end_text[:10])
            dtend = end + timedelta(days=1)
            lines.extend([
                f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{dtend.strftime('%Y%m%d')}",
            ])
        else:
            from datetime import datetime as dt
            start_dt = dt.fromisoformat(start_text.replace("Z", "+00:00"))
            end_text = event.get("end") or start_text
            end_dt = dt.fromisoformat(end_text.replace("Z", "+00:00"))
            lines.extend([
                f"DTSTART;TZID=Asia/Jakarta:{start_dt.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND;TZID=Asia/Jakarta:{end_dt.strftime('%Y%m%dT%H%M%S')}",
            ])

        lines.extend([
            f"SUMMARY:{title}",
            f"DESCRIPTION:{description}",
            f"LOCATION:{location}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    return "\r\n".join(lines) + "\r\n"
