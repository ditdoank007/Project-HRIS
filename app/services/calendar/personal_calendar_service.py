"""
HRIS REBORN
Personal Calendar Service

Single source of truth untuk event Personal Calendar.

Sumber:
- ABSENSI       : CUTI / SAKIT / IJIN
- DINAS_LUAR
- LOG_ACTIVITIY : Piket Siaga
- KALENDER      : WFH / LIBUR

Service ini mengembalikan list event dictionary.
"""

from sqlalchemy import text

from app import db

from app.models.absensiModel import Absensi
from app.models.dinasLuarModel import DinasLuar
from app.models.pegawaiModel import Pegawai
from app.models.kalenderModel import MfKalender

from app.utils.absensiNormalisasiHelper import (
    get_label_dinas_luar,
    get_warna_dinas_luar,
)


def build_personal_calendar_events(
    nip,
    tanggal_awal,
    tanggal_akhir,
):
    pegawai = (
        Pegawai.query
        .filter(Pegawai.NIP == nip)
        .first()
    )

    if not pegawai:
        raise ValueError("Data pegawai tidak ditemukan.")

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
    # 5. KALENDER INSTITUSI
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

    return pegawai, events
