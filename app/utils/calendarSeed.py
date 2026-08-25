"""
HRIS REBORN
Calendar Master Seed

Generate default calendar category.
"""


from datetime import datetime

from app import db
from app.models.calendarCategoryModel import CalendarCategory



DEFAULT_CATEGORY = [

    {
        "CODE": "LIBUR",
        "NAME": "Hari Libur",
        "COLOR": "#dc3545",
    },

    {
        "CODE": "CUTI",
        "NAME": "Cuti Pegawai",
        "COLOR": "#198754",
    },

    {
        "CODE": "SAKIT",
        "NAME": "Sakit",
        "COLOR": "#ffc107",
    },

    {
        "CODE": "IJIN",
        "NAME": "Ijin",
        "COLOR": "#6c757d",
    },

    {
        "CODE": "DINAS_LUAR",
        "NAME": "Dinas Luar",
        "COLOR": "#0d6efd",
    },

    {
        "CODE": "SIAGA",
        "NAME": "Siaga",
        "COLOR": "#fd7e14",
    },

    {
        "CODE": "RAPAT",
        "NAME": "Rapat",
        "COLOR": "#6610f2",
    },

    {
        "CODE": "APEL",
        "NAME": "Apel",
        "COLOR": "#20c997",
    },

    {
        "CODE": "SPRIN",
        "NAME": "Surat Perintah",
        "COLOR": "#795548",
    },

    {
        "CODE": "LAIN",
        "NAME": "Agenda Lainnya",
        "COLOR": "#343a40",
    },

]



def seed_calendar_category():

    inserted = 0


    for item in DEFAULT_CATEGORY:


        exists = (
            CalendarCategory.query
            .filter(
                CalendarCategory.CODE == item["CODE"]
            )
            .first()
        )


        if exists:
            continue



        row = CalendarCategory(

            CODE=item["CODE"],

            NAME=item["NAME"],

            COLOR=item["COLOR"],

            IS_ACTIVE="Y",

            UPDATE_BY="SYSTEM",

            UPDATE_DATE=datetime.utcnow()

        )


        db.session.add(row)

        inserted += 1



    db.session.commit()


    return inserted
