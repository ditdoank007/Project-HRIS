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
    session
)



from app.models.calendarCategoryModel import CalendarCategory

from app.models.absensiModel import Absensi
from app.models.dinasLuarModel import DinasLuar
from app.models.pegawaiModel import Pegawai
from app.models.kalenderModel import MfKalender

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

from app.services.calendar.conflict_service import (
    check_employee_conflict
)



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

    from calendar import monthrange
    from datetime import date

    tanggal_awal = date(tahun, bulan, 1)

    if bulan == 12:
        tanggal_akhir = date(tahun + 1, 1, 1)
    else:
        tanggal_akhir = date(tahun, bulan + 1, 1)

    pegawai = (
        Pegawai.query
        .filter(Pegawai.NIP == nip)
        .first()
    )

    if not pegawai:
        return jsonify({
            "status": "error",
            "message": "Data pegawai tidak ditemukan."
        }), 404

    events = []

    # ============================================================
    # 1. CUTI / SAKIT
    # ============================================================

    absensi_rows = (
        Absensi.query
        .filter(Absensi.FINGER_ID == pegawai.FINGER_ID)
        .filter(Absensi.TGL_KERJA >= tanggal_awal)
        .filter(Absensi.TGL_KERJA < tanggal_akhir)
        .filter(
            Absensi.TRANSAKSI_IN.in_([
                "CUTI",
                "Cuti",
                "SAKIT",
                "Sakit"
            ])
        )
        .order_by(Absensi.TGL_KERJA.asc())
        .all()
    )

    for row in absensi_rows:

        transaksi = (row.TRANSAKSI_IN or "").strip().upper()

        if transaksi == "CUTI":
            jenis = "CUTI"
        elif transaksi == "SAKIT":
            jenis = "SAKIT"
        else:
            continue

        tanggal = row.TGL_KERJA.date()

        events.append({
            "id": f"ABSENSI-{pegawai.FINGER_ID}-{tanggal.isoformat()}",
            "title": jenis,
            "type": jenis,
            "source": "ABSENSI",
            "start": tanggal.isoformat(),
            "end": tanggal.isoformat(),
            "all_day": True,
            "description": row.KET_IN,
            "location": None,
        })

    # ============================================================
    # 2. IJIN
    #
    # HRIS legacy mengenali IJIN dari:
    # TRANSAKSI_IN = ALPA
    # PENDUKUNG_IN = Y
    # ============================================================

    ijin_rows = (
        Absensi.query
        .filter(Absensi.FINGER_ID == pegawai.FINGER_ID)
        .filter(Absensi.TGL_KERJA >= tanggal_awal)
        .filter(Absensi.TGL_KERJA < tanggal_akhir)
        .filter(Absensi.TRANSAKSI_IN.in_(["ALPA", "Alpa"]))
        .filter(Absensi.PENDUKUNG_IN == "Y")
        .order_by(Absensi.TGL_KERJA.asc())
        .all()
    )

    for row in ijin_rows:

        tanggal = row.TGL_KERJA.date()

        events.append({
            "id": f"ABSENSI-IJIN-{pegawai.FINGER_ID}-{tanggal.isoformat()}",
            "title": "IJIN",
            "type": "IJIN",
            "source": "ABSENSI",
            "start": tanggal.isoformat(),
            "end": tanggal.isoformat(),
            "all_day": True,
            "description": row.KET_IN,
            "location": None,
        })

    # ============================================================
    # 3. DINAS LUAR
    #
    # Ambil seluruh perjalanan yang bersinggungan dengan bulan
    # yang sedang diminta.
    # ============================================================

    dinas_rows = (
        DinasLuar.query
        .filter(DinasLuar.FINGER_ID == pegawai.FINGER_ID)
        .filter(
            DinasLuar.TGL_AWAL_DINAS_LUAR < tanggal_akhir
        )
        .filter(
            DinasLuar.TGL_AKHIR_DINAS_LUAR >= tanggal_awal
        )
        .order_by(
            DinasLuar.TGL_AWAL_DINAS_LUAR.asc()
        )
        .all()
    )

    for row in dinas_rows:

        if not row.TGL_AWAL_DINAS_LUAR:
            continue

        start_date = row.TGL_AWAL_DINAS_LUAR.date()

        end_date = (
            row.TGL_AKHIR_DINAS_LUAR.date()
            if row.TGL_AKHIR_DINAS_LUAR
            else start_date
        )

        events.append({
            "id": f"DINAS-LUAR-{row.TRANSAKSI_ID}",
            "title": get_label_dinas_luar(row.JENIS),
            "type": "DINAS_LUAR",
            "source": "DINAS_LUAR",
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "all_day": True,
            "description": row.KETERANGAN_DINAS_LUAR,
            "location": row.PENEMPATAN_DINAS_LUAR,
            "no_surat": row.NO_SURAT,
            "status_um": row.STATUS_UM,
            "color": get_warna_dinas_luar(row.STATUS_UM),
        })

    # ============================================================
    # 4. PIKET SIAGA
    #
    # ActivityDate = tanggal siaga (H).
    # Shift 1 dan Shift 2 ditampilkan pada tanggal H.
    # Shift 2 tidak digeser ke H+1.
    #
    # Priority:
    # DINAS LUAR > PIKET SIAGA > KALENDER
    # ============================================================

    piket_rows = db.session.execute(
        text("""
            SELECT
                ActivityDate,
                Shift,
                StatusID,
                shift2
            FROM LOG_ACTIVITIY
            WHERE NIP = :nip
              AND Activity = 'Piket Siaga'
              AND ActivityDate >= :tanggal_awal
              AND ActivityDate < :tanggal_akhir
              AND StatusID = 3
              AND (
                    Shift = '1'
                    OR (Shift = '2' AND shift2 = 1)
              )
            ORDER BY ActivityDate ASC, Shift ASC
        """),
        {
            "nip": nip,
            "tanggal_awal": tanggal_awal,
            "tanggal_akhir": tanggal_akhir,
        },
    ).mappings().all()

    for row in piket_rows:
        if not row["ActivityDate"]:
            continue

        tanggal = (
            row["ActivityDate"].date()
            if hasattr(row["ActivityDate"], "date")
            else row["ActivityDate"]
        )

        shift = str(row["Shift"] or "").strip()

        if shift == "1":
            warna = "#166534"
            label = "Piket Siaga Shift 1"
        elif shift == "2":
            warna = "#86efac"
            label = "Piket Siaga Shift 2"
        else:
            continue

        events.append({
            "id": f"PIKET-SIAGA-{shift}-{tanggal.isoformat()}",
            "title": label,
            "type": "PIKET_SIAGA",
            "source": "LOG_ACTIVITIY",
            "start": tanggal.isoformat(),
            "end": tanggal.isoformat(),
            "all_day": True,
            "description": label,
            "location": None,
            "shift": shift,
            "color": warna,
        })

    # ============================================================
    # 4. KALENDER INSTITUSI
    #
    # Layer terbawah:
    # - Sabtu / Minggu
    # - Hari libur nasional
    # - Cuti bersama
    # - WFH
    #
    # DINAS LUAR tetap berada di atas layer ini.
    # ============================================================

    kalender_rows = (
        MfKalender.query
        .filter(MfKalender.TGL_KERJA >= tanggal_awal)
        .filter(MfKalender.TGL_KERJA < tanggal_akhir)
        .filter(
            (MfKalender.IS_LIBUR == "Y") |
            (MfKalender.KET == "WFH")
        )
        .order_by(MfKalender.TGL_KERJA.asc())
        .all()
    )

    for row in kalender_rows:
        if not row.TGL_KERJA:
            continue

        tanggal = row.TGL_KERJA.date()
        keterangan = str(row.KET or "").strip()

        if keterangan.upper() == "WFH":
            events.append({
                "id": f"KALENDER-WFH-{tanggal.isoformat()}",
                "title": "WFH",
                "type": "WFH",
                "source": "KALENDER",
                "start": tanggal.isoformat(),
                "end": tanggal.isoformat(),
                "all_day": True,
                "description": keterangan,
                "location": None,
            })
        else:
            events.append({
                "id": f"KALENDER-LIBUR-{tanggal.isoformat()}",
                "title": "LIBUR",
                "type": "LIBUR",
                "source": "KALENDER",
                "start": tanggal.isoformat(),
                "end": tanggal.isoformat(),
                "all_day": True,
                "description": keterangan or "Hari Libur",
                "location": None,
            })

    # ============================================================
    # SORT FINAL
    # ============================================================

    events.sort(
        key=lambda item: (
            item["start"],
            item["type"],
            item["id"]
        )
    )

    return jsonify({
        "status": "success",
        "year": tahun,
        "month": bulan,
        "nip": nip,
        "nama": pegawai.NAMA,
        "data": events,
        "total": len(events),
    })


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
