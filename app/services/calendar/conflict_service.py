"""
HRIS REBORN
Calendar Conflict Service

Business Layer untuk mendeteksi benturan agenda pegawai.

Dipakai oleh:
- Dinas Luar
- Cuti
- Siaga
- SPRIN
- Disposisi
- Agenda manual
"""

from datetime import datetime

from app.models.calendarEventModel import CalendarEvent
from app.models.calendarParticipantModel import CalendarParticipant


def check_employee_conflict(
    nip,
    start_date,
    end_date
):
    """
    Cek apakah pegawai memiliki agenda yang
    waktunya bertabrakan dengan periode yang diberikan.

    Benturan terjadi jika:

        event.START_DATE < requested_end
        DAN
        event.END_DATE > requested_start
    """

    rows = (
        CalendarEvent.query

        .join(
            CalendarParticipant,
            CalendarEvent.EVENT_ID ==
            CalendarParticipant.EVENT_ID
        )

        .filter(
            CalendarParticipant.NIP == nip
        )

        .filter(
            CalendarEvent.START_DATE < end_date
        )

        .filter(
            CalendarEvent.END_DATE > start_date
        )

        .order_by(
            CalendarEvent.START_DATE.asc()
        )

        .all()
    )

    return rows
