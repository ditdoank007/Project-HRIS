"""
HRIS REBORN
Calendar Controller

API Layer:
- Agenda pribadi
- Agenda pegawai
- Create event
- ICS feed
"""

from datetime import datetime

from flask import (
    request,
    jsonify,
    Response,
    session
)



from app.models.calendarCategoryModel import CalendarCategory

from app.services.calendar.event_service import (
    create_event
)

from app.services.calendar.agenda_service import (
    get_my_agenda_detail,
    get_user_agenda_detail
)

from app.services.calendar.ics_service import (
    get_events_by_token,
    generate_ics
)

from app.services.calendar.conflict_service import (
    check_employee_conflict
)



def api_calendar_my_agenda():

    nip = session.get(
        'nip'
    )


    if not nip:

        return jsonify({
            "status": "error",
            "message": "NIP tidak ditemukan"
        }), 401


    rows = get_my_agenda_detail(
        nip
    )


    return jsonify({

        "status": "success",

        "data": [

            {

                "event_id": x.EVENT_ID,

                "title": x.TITLE,

                "description": x.DESCRIPTION,

                "start_date": (
                    x.START_DATE.isoformat()
                    if x.START_DATE
                    else None
                ),

                "end_date": (
                    x.END_DATE.isoformat()
                    if x.END_DATE
                    else None
                ),

                "location": x.LOCATION,

                "status": x.STATUS,

                "event_type": x.EVENT_TYPE,


                "category": {

                    "code": x.CODE,

                    "name": x.NAME,

                    "color": x.COLOR

                },


                "participant_status":
                    x.participant_status

            }

            for x in rows

        ]

    })



def api_calendar_create_event():

    payload = request.get_json(
        silent=True
    ) or {}


    user = session.get(
        'nip',
        'system'
    )


    event = create_event(
        payload,
        user
    )


    return jsonify({

        "status": "success",

        "data": event.to_dict()

    })



def api_calendar_feed(token):

    events = get_events_by_token(
        token
    )


    content = generate_ics(
        events
    )


    return Response(
        content,
        mimetype='text/calendar'
    )


# ============================================================
# CALENDAR CATEGORY API
#
# Master kategori agenda
#
# ============================================================


def api_calendar_category():

    rows = (
        CalendarCategory.query
        .filter(
            CalendarCategory.IS_ACTIVE == 'Y'
        )
        .order_by(
            CalendarCategory.ID.asc()
        )
        .all()
    )


    return jsonify({

        "status": "success",

        "data": [

            {
                "id": row.ID,
                "code": row.CODE,
                "name": row.NAME,
                "color": row.COLOR
            }

            for row in rows

        ]

    })



# ============================================================
# USER AGENDA API
#
# Digunakan untuk:
# - cek agenda pegawai
# - pengecekan konflik SPRIN
# - pengecekan Dinas Luar
# ============================================================


def api_calendar_user_agenda(nip):


    rows = get_user_agenda_detail(
        nip
    )


    data = []


    for x in rows:

        data.append({

            "event_id":
                x.EVENT_ID,

            "title":
                x.TITLE,

            "category":
                x.NAME,

            "category_color":
                x.category_color,

            "event_type":
                x.EVENT_TYPE,

            "source":
                x.SOURCE,

            "start":
                (
                    x.START_DATE.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if x.START_DATE
                    else None
                ),

            "end":
                (
                    x.END_DATE.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if x.END_DATE
                    else None
                ),

            "location":
                x.LOCATION,

            "status":
                x.STATUS,

            "participant_status":
                x.participant_status

        })


    return jsonify({

        "status":
            "success",

        "nip":
            nip,

        "total":
            len(data),

        "agenda":
            data

    })



# ============================================================
# CALENDAR CONFLICT API
#
# Cek benturan agenda seorang pegawai
#
# Parameter:
#   /api/calendar/conflict/<nip>
#   ?start=YYYY-MM-DD HH:MM:SS
#   &end=YYYY-MM-DD HH:MM:SS
#
# ============================================================


def api_calendar_conflict(nip):

    start_text = request.args.get(
        "start"
    )

    end_text = request.args.get(
        "end"
    )


    if not start_text or not end_text:

        return jsonify({
            "status": "error",
            "message": "Parameter start dan end wajib diisi"
        }), 400


    try:

        start_date = datetime.strptime(
            start_text,
            "%Y-%m-%d %H:%M:%S"
        )

        end_date = datetime.strptime(
            end_text,
            "%Y-%m-%d %H:%M:%S"
        )

    except ValueError:

        return jsonify({
            "status": "error",
            "message":
                "Format tanggal harus YYYY-MM-DD HH:MM:SS"
        }), 400


    if end_date <= start_date:

        return jsonify({
            "status": "error",
            "message":
                "Waktu end harus lebih besar dari start"
        }), 400


    rows = check_employee_conflict(
        nip,
        start_date,
        end_date
    )


    data = []


    for x in rows:

        data.append({

            "event_id":
                x.EVENT_ID,

            "title":
                x.TITLE,

            "start":
                (
                    x.START_DATE.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if x.START_DATE
                    else None
                ),

            "end":
                (
                    x.END_DATE.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if x.END_DATE
                    else None
                ),

            "location":
                x.LOCATION,

            "status":
                x.STATUS,

            "event_type":
                x.EVENT_TYPE,

            "source":
                x.SOURCE

        })


    return jsonify({

        "status": "success",

        "nip":
            nip,

        "conflict":
            len(data) > 0,

        "total":
            len(data),

        "agenda":
            data

    })
