# controllers/dashboard_2HomeController.py
from flask import render_template
from app import db


def dashboard_tim_siaga():
    """Render dashboard kehadiran siaga dengan urutan unit dari Master Unit Kerja."""
    unit_rows = db.session.execute(
        db.text("""
            SELECT IDUnitKerja, UnitKerjaName, UrutReport
            FROM MF_UNIT_KERJA
            WHERE COALESCE(isUse, 'N') = 'Y'
            ORDER BY COALESCE(UrutReport, 999999) ASC, UnitKerjaName ASC
        """)
    ).mappings().all()

    unit_order = [
        {
            'id': str(row['IDUnitKerja']),
            'name': row['UnitKerjaName'] or '',
            'order': int(row['UrutReport'] or 999999),
        }
        for row in unit_rows
    ]
    return render_template(
        'pages/dashboard_2/Dashboard_Piket_Siaga.html',
        siaga_unit_order=unit_order,
    )
