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
from sqlalchemy import text

from app import db

from flask import (
    request,
    jsonify,
    Response,
    session,
    send_file,
)



from app.models.calendarCategoryModel import CalendarCategory

from app.models.absensiModel import Absensi
from app.models.dinasLuarModel import DinasLuar
from app.models.pegawaiModel import Pegawai
from app.models.unitKerjaModel import MfUnitKerja
from app.utils.pegawaiHelper import get_operational_pegawai_query
from app.models.kalenderModel import MfKalender
from app.models.calendarSyncTokenModel import CalendarSyncToken
from app.models.calendarEventModel import CalendarEvent
from app.models.calendarParticipantModel import CalendarParticipant
from app.models.agendaRapatAttendanceModel import AgendaRapatAttendance
from app.models.agendaRapatMetaModel import AgendaRapatMeta
from app.models.hrisDocumentModel import HrisDocument

from app.utils.absensiNormalisasiHelper import (
    get_label_dinas_luar,
    get_warna_dinas_luar,
)

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
from app.services.calendar.personal_calendar_service import (
    build_personal_calendar_events
)

from app.services.calendar.conflict_service import (
    check_employee_conflict
)
from app.services.document_storage import notulen_absolute_path, notulen_relative_path



def get_or_create_calendar_sync_token(nip):
    sync = (
        CalendarSyncToken.query
        .filter(
            CalendarSyncToken.NIP == nip,
            CalendarSyncToken.IS_ACTIVE == 'Y'
        )
        .first()
    )

    if sync:
        return sync

    token = __import__("secrets").token_urlsafe(48)

    sync = CalendarSyncToken(
        NIP=nip,
        TOKEN=token,
        IS_ACTIVE='Y',
        CREATED_DATE=datetime.utcnow()
    )

    db.session.add(sync)
    db.session.commit()

    return sync



def api_calendar_sync_token_internal():
    from config import Config

    internal_key = request.headers.get(
        "X-Calendar-Internal-Key"
    )

    if not internal_key or internal_key != Config.CALENDAR_INTERNAL_API_KEY:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    nip = request.headers.get("X-Calendar-NIP")

    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP wajib diisi."
        }), 400

    try:
        sync = get_or_create_calendar_sync_token(nip)

        return jsonify({
            "status": "success",
            "feed_url": f"/api/calendar/feed/{sync.TOKEN}.ics"
        })

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Gagal mendapatkan token kalender"
        }), 500


def api_calendar_personal_sync_token():
    nip = session.get('nip')

    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP tidak ditemukan"
        }), 401

    try:
        sync = get_or_create_calendar_sync_token(nip)

        return jsonify({
            "status": "success",
            "token": sync.TOKEN,
            "feed_url": f"/api/calendar/feed/{sync.TOKEN}.ics"
        })

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Gagal membuat token kalender"
        }), 500



def api_calendar_personal_internal():

    from config import Config

    internal_key = request.headers.get(
        "X-Calendar-Internal-Key"
    )

    if not internal_key or internal_key != Config.CALENDAR_INTERNAL_API_KEY:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    nip = request.headers.get("X-Calendar-NIP")

    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP wajib diisi."
        }), 400

    try:
        tahun = int(request.args.get("year"))
        bulan = int(request.args.get("month"))
    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Parameter year dan month wajib berupa angka."
        }), 400

    if tahun < 2000 or tahun > 2100:
        return jsonify({
            "status": "error",
            "message": "Tahun tidak valid."
        }), 400

    if bulan < 1 or bulan > 12:
        return jsonify({
            "status": "error",
            "message": "Bulan tidak valid."
        }), 400

    from datetime import date

    tanggal_awal = date(tahun, bulan, 1)

    if bulan == 12:
        tanggal_akhir = date(tahun + 1, 1, 1)
    else:
        tanggal_akhir = date(tahun, bulan + 1, 1)

    pegawai, events = build_personal_calendar_events(
        nip,
        tanggal_awal,
        tanggal_akhir
    )

    if not pegawai:
        return jsonify({
            "status": "error",
            "message": "Data pegawai tidak ditemukan."
        }), 404

    return jsonify({
        "status": "success",
        "data": events
    })



def api_calendar_employee_profile_internal():
    """
    Internal employee profile for trusted Calendar Portal requests.

    Source of truth remains the HRIS Reborn PEGAWAI table.
    """
    from config import Config

    internal_key = request.headers.get("X-Calendar-Internal-Key")

    if not internal_key or internal_key != Config.CALENDAR_INTERNAL_API_KEY:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()

    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP wajib diisi."
        }), 400

    pegawai = (
        Pegawai.query
        .filter(Pegawai.NIP == nip)
        .first()
    )

    if not pegawai:
        return jsonify({
            "status": "success",
            "data": None
        })

    return jsonify({
        "status": "success",
        "data": {
            "nip": str(pegawai.NIP or "").strip(),
            "nama": str(pegawai.NAMA or "").strip(),
            "jenis_kel": str(pegawai.JENIS_KEL or "").strip(),
        }
    })


def api_calendar_infografis_internal():
    """
    Internal read-only employee statistics for the Portal Pegawai.

    Source of truth remains HRIS Reborn operational PEGAWAI data.
    """
    from datetime import date

    from config import Config

    internal_key = request.headers.get("X-Calendar-Internal-Key")
    if not internal_key or internal_key != Config.CALENDAR_INTERNAL_API_KEY:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    today = date.today()

    def calculate_age(birth_date):
        if not birth_date:
            return None
        try:
            age = today.year - birth_date.year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
            return age if age >= 0 else None
        except (AttributeError, TypeError):
            return None

    pegawai_rows = get_operational_pegawai_query().all()
    pegawai_rows = [
        row for row in pegawai_rows
        if calculate_age(row.TGL_LAHIR) is None
        or calculate_age(row.TGL_LAHIR) <= 60
    ]

    unit_rows = (
        MfUnitKerja.query
        .filter(MfUnitKerja.IS_USE == 'Y')
        .all()
    )

    unit_map = {
        str(row.UNIT_KERJA_ID).strip(): str(
            row.NAMA_UNIT_KERJA or ''
        ).strip()
        for row in unit_rows
        if row.UNIT_KERJA_ID is not None
    }

    total = len(pegawai_rows)
    pns = sum(1 for row in pegawai_rows if row.STATUS_PEG == 1)
    non_pns = sum(1 for row in pegawai_rows if row.STATUS_PEG == 2)

    gender_counts = {
        "Laki-laki": 0,
        "Perempuan": 0,
        "Belum diisi": 0,
    }

    age_buckets = {
        "<=20 Tahun": 0,
        "21 s/d 30 Tahun": 0,
        "31 s/d 40 Tahun": 0,
        "41 s/d 50 Tahun": 0,
        "51 s/d 60 Tahun": 0,
    }

    age_unknown = 0

    golongan_labels = [
        "II/a", "II/b", "II/c", "II/d",
        "III/a", "III/b", "III/c", "III/d",
        "IV/a", "IV/b", "IV/c", "IV/d", "IV/e",
    ]

    golongan_counts = {label: 0 for label in golongan_labels}
    golongan_employees = {label: [] for label in golongan_labels}
    unit_counts = {}

    for row in pegawai_rows:
        gender = str(row.JENIS_KEL or "").strip().upper()

        if gender in ("L", "LAKI-LAKI", "LAKI LAKI", "LAKI"):
            gender_key = "Laki-laki"
        elif gender in ("P", "PEREMPUAN", "WANITA"):
            gender_key = "Perempuan"
        else:
            gender_key = "Belum diisi"

        gender_counts[gender_key] += 1

        age = calculate_age(row.TGL_LAHIR)

        if age is None:
            age_unknown += 1
        elif age <= 20:
            age_buckets["<=20 Tahun"] += 1
        elif age <= 30:
            age_buckets["21 s/d 30 Tahun"] += 1
        elif age <= 40:
            age_buckets["31 s/d 40 Tahun"] += 1
        elif age <= 50:
            age_buckets["41 s/d 50 Tahun"] += 1
        elif age <= 60:
            age_buckets["51 s/d 60 Tahun"] += 1

        golongan = str(row.GOL_ID or "").strip().lower()

        for label in golongan_labels:
            if golongan == label.lower():
                golongan_counts[label] += 1
                golongan_employees[label].append({
                    "nama": str(row.NAMA or "").strip(),
                    "nip": str(row.NIP or "").strip(),
                })
                break

        unit_id = str(row.UNIT_KERJA_ID or "").strip()
        unit_name = (
            unit_map.get(unit_id)
            or str(row.UNIT_KERJA or "").strip()
            or "Belum diisi"
        )
        unit_counts[unit_name] = unit_counts.get(unit_name, 0) + 1

    for label in golongan_labels:
        golongan_employees[label].sort(
            key=lambda item: item["nama"].lower()
        )

    unit_distribution = sorted(
        [
            {"name": name, "total": count}
            for name, count in unit_counts.items()
        ],
        key=lambda item: (-item["total"], item["name"].lower())
    )

    return jsonify({
        "status": "success",
        "today": today.isoformat(),
        "data": {
            "total": total,
            "pns": pns,
            "non_pns": non_pns,
            "gender_counts": gender_counts,
            "status_counts": {
                "PNS": pns,
                "Non PNS": non_pns,
                "Lainnya": max(total - pns - non_pns, 0),
            },
            "age_buckets": age_buckets,
            "age_unknown": age_unknown,
            "golongan_labels": golongan_labels,
            "golongan_counts": golongan_counts,
            "golongan_employees": golongan_employees,
            "unit_distribution": unit_distribution,
        },
    })

def api_calendar_personal():

    nip = session.get('nip')

    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP tidak ditemukan"
        }), 401

    try:
        tahun = int(request.args.get("year"))
        bulan = int(request.args.get("month"))
    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Parameter year dan month wajib berupa angka."
        }), 400

    if tahun < 2000 or tahun > 2100:
        return jsonify({
            "status": "error",
            "message": "Tahun tidak valid."
        }), 400

    if bulan < 1 or bulan > 12:
        return jsonify({
            "status": "error",
            "message": "Bulan tidak valid."
        }), 400

    from datetime import date

    tanggal_awal = date(tahun, bulan, 1)

    if bulan == 12:
        tanggal_akhir = date(tahun + 1, 1, 1)
    else:
        tanggal_akhir = date(tahun, bulan + 1, 1)

    pegawai, events = build_personal_calendar_events(
        nip,
        tanggal_awal,
        tanggal_akhir,
    )

    if not pegawai:
        return jsonify({
            "status": "error",
            "message": "Data pegawai tidak ditemukan."
        }), 404

    return jsonify({
        "status": "success",
        "year": tahun,
        "month": bulan,
        "nip": nip,
        "nama": pegawai.NAMA,
        "data": events,
        "total": len(events),
    })



def api_calendar_my_agenda_internal():
    from config import Config

    internal_key = request.headers.get(
        "X-Calendar-Internal-Key"
    )

    if not internal_key or internal_key != Config.CALENDAR_INTERNAL_API_KEY:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP wajib diisi."
        }), 400

    try:
        rows = get_my_agenda_detail(nip)

        return jsonify({
            "status": "success",
            "data": [
                {
                    "event_id": x.EVENT_ID,
                    "title": x.TITLE,
                    "description": x.DESCRIPTION,
                    "start_date": x.START_DATE.isoformat() if x.START_DATE else None,
                    "end_date": x.END_DATE.isoformat() if x.END_DATE else None,
                    "location": x.LOCATION,
                    "status": x.STATUS,
                    "event_type": x.EVENT_TYPE,
                    "category": {
                        "code": x.CODE,
                        "name": x.NAME,
                        "color": x.COLOR,
                    },
                    "participant_status": x.participant_status,
                }
                for x in rows
            ]
        })
    except Exception:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Gagal mengambil Agenda Kalender HRIS."
        }), 500

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
# AGENDA RAPAT FOR CALENDAR PORTAL
#
# TERJADWAL -> visible to all employees as a pending agenda.
# SELESAI -> visible only to employees recorded HADIR by QR.
# BATAL -> retained in AgendaKu history, but not Personal Calendar.
# ============================================================

def _calendar_internal_authorized():
    from config import Config
    return (
        request.headers.get("X-Calendar-Internal-Key")
        and request.headers.get("X-Calendar-Internal-Key")
        == Config.CALENDAR_INTERNAL_API_KEY
    )


def _calendar_rapat_visible_to_employee(event, nip):
    if event.STATUS in ("TERJADWAL", "BATAL"):
        return True

    if event.STATUS != "SELESAI":
        return False

    return (
        AgendaRapatAttendance.query
        .filter(
            AgendaRapatAttendance.EVENT_ID == event.EVENT_ID,
            AgendaRapatAttendance.NIP == nip,
            AgendaRapatAttendance.STATUS == "HADIR",
        )
        .first()
        is not None
    )


def _calendar_rapat_rows(nip):
    events = (
        CalendarEvent.query
        .filter(CalendarEvent.EVENT_TYPE == "RAPAT")
        .order_by(CalendarEvent.START_DATE.desc())
        .all()
    )

    data = []

    for event in events:
        if not _calendar_rapat_visible_to_employee(event, nip):
            continue

        meta = (
            AgendaRapatMeta.query
            .filter(AgendaRapatMeta.EVENT_ID == event.EVENT_ID)
            .first()
        )

        organizer_nip = meta.ORGANIZER_NIP if meta else event.CREATED_BY
        organizer = (
            Pegawai.query
            .filter(Pegawai.NIP == organizer_nip)
            .first()
        )

        attendance = (
            AgendaRapatAttendance.query
            .filter(
                AgendaRapatAttendance.EVENT_ID == event.EVENT_ID,
                AgendaRapatAttendance.STATUS == "HADIR",
            )
            .order_by(AgendaRapatAttendance.SCANNED_DATE.asc())
            .all()
        )

        document = (
            HrisDocument.query
            .filter(
                HrisDocument.DOCUMENT_TYPE == "NOTULEN_RAPAT",
                HrisDocument.ENTITY_TYPE == "CALENDAR_EVENT",
                HrisDocument.ENTITY_ID == str(event.EVENT_ID),
            )
            .first()
        )

        data.append({
            "event_id": event.EVENT_ID,
            "title": event.TITLE,
            "description": event.DESCRIPTION,
            "start": event.START_DATE.isoformat() if event.START_DATE else None,
            "end": event.END_DATE.isoformat() if event.END_DATE else None,
            "location": event.LOCATION,
            "status": event.STATUS,
            "organizer_nip": organizer_nip,
            "organizer_name": organizer.NAMA if organizer else organizer_nip,
            "attendance_count": len(attendance),
            "attendance": [
                {
                    "attendee_type": a.ATTENDEE_TYPE,
                    "nip": a.NIP,
                    "nama": (
                        p.NAMA
                        if p
                        else (a.NAME or a.NAME_RAW or "-")
                    ),
                    "email": (
                        p.MAIL
                        if p and p.MAIL
                        else a.EMAIL
                    ),
                    "scanned_date": a.SCANNED_DATE.isoformat(),
                }
                for a in attendance
                for p in [
                    Pegawai.query.filter(Pegawai.NIP == a.NIP).first()
                    if a.ATTENDEE_TYPE == "PEGAWAI" and a.NIP
                    else None
                ]
            ],
            "notulen_available": bool(document),
        })

    return data

def api_calendar_agenda_rapat_internal():
    if not _calendar_internal_authorized():
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP wajib diisi."
        }), 400

    return jsonify({
        "status": "success",
        "data": _calendar_rapat_rows(nip),
    })


def api_calendar_agenda_rapat_notulen_internal(event_id):
    if not _calendar_internal_authorized():
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    nip = str(request.headers.get("X-Calendar-NIP") or "").strip()
    if not nip:
        return jsonify({
            "status": "error",
            "message": "NIP wajib diisi."
        }), 400

    event = (
        CalendarEvent.query
        .filter(
            CalendarEvent.EVENT_ID == event_id,
            CalendarEvent.EVENT_TYPE == "RAPAT",
        )
        .first()
    )

    if not event:
        return jsonify({
            "status": "error",
            "message": "Agenda rapat tidak ditemukan."
        }), 404

    if not _calendar_rapat_visible_to_employee(event, nip):
        return jsonify({
            "status": "error",
            "message": "Anda tidak berhak mengakses Notulen rapat ini."
        }), 403

    document = (
        HrisDocument.query
        .filter(
            HrisDocument.DOCUMENT_TYPE == "NOTULEN_RAPAT",
            HrisDocument.ENTITY_TYPE == "CALENDAR_EVENT",
            HrisDocument.ENTITY_ID == str(event_id),
        )
        .first()
    )

    if not document:
        return jsonify({
            "status": "error",
            "message": "Notulen belum tersedia."
        }), 404

    expected_path = notulen_absolute_path(event.START_DATE, event.EVENT_ID)
    expected_relative = notulen_relative_path(event.START_DATE, event.EVENT_ID)

    if document.STORAGE_PATH != expected_relative:
        return jsonify({
            "status": "error",
            "message": "Metadata storage Notulen tidak valid."
        }), 409

    if not os.path.isfile(expected_path):
        return jsonify({
            "status": "error",
            "message": "File Notulen tidak ditemukan di central storage."
        }), 404

    return send_file(
        expected_path,
        mimetype=document.MIME_TYPE or "application/pdf",
        as_attachment=False,
        download_name=document.ORIGINAL_FILENAME,
        max_age=0,
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
