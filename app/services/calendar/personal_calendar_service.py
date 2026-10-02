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
from app.models.agendaRapatAttendanceModel import AgendaRapatAttendance
from app.models.calendarEventModel import CalendarEvent
from app.models.kesamaptaanKegiatanModel import KesamaptaanKegiatan
from app.models.kesamaptaanKehadiranModel import KesamaptaanKehadiran
from app.models.hrisDocumentModel import HrisDocument

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
                shift2,
                IDUnitKerja
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
        unit_kerja_id = row["IDUnitKerja"]

        if shift == "1":
            warna = "#166534"
            label = "Piket Siaga Shift 1"
        elif shift == "2":
            warna = "#86efac"
            label = "Piket Siaga Shift 2"
        else:
            continue

        document_key = f"{tanggal.isoformat()}|{int(unit_kerja_id)}|{shift}"
        document = HrisDocument.query.filter(
            HrisDocument.DOCUMENT_TYPE == "ABSEN_KEHADIRAN_SIAGA",
            HrisDocument.ENTITY_TYPE == "PIKET_SIAGA",
            HrisDocument.ENTITY_ID == document_key,
        ).first()

        events.append({
            "id": f"PIKET-SIAGA-{shift}-{tanggal.isoformat()}-{int(unit_kerja_id)}",
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
            "pdf_available": bool(document),
            "pdf_filename": document.ORIGINAL_FILENAME if document else None,
            "pdf_key": document_key if document else None,
            "pdf_url": (
                f"/api/agenda/piket-siaga/pdf?key={document_key}"
                if document else None
            ),
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
    # 6. AGENDA RAPAT
    #
    # FASE 1 - TERJADWAL:
    #   Semua pegawai melihat agenda rapat yang akan datang.
    #
    # FASE 2 - SELESAI:
    #   Hanya pegawai yang tercatat HADIR melalui QR yang
    #   mendapatkan rapat tersebut secara permanen.
    #
    # RAPAT BATAL tidak masuk Personal Calendar.
    # ============================================================

    from sqlalchemy import or_, and_, exists

    attendance_exists = exists().where(
        and_(
            AgendaRapatAttendance.EVENT_ID == CalendarEvent.EVENT_ID,
            AgendaRapatAttendance.NIP == nip,
            AgendaRapatAttendance.STATUS == "HADIR",
        )
    )

    rapat_rows = (
        CalendarEvent.query
        .filter(
            CalendarEvent.EVENT_TYPE == "RAPAT",
            or_(
                CalendarEvent.STATUS == "TERJADWAL",
                and_(
                    CalendarEvent.STATUS == "SELESAI",
                    attendance_exists,
                ),
            ),
            CalendarEvent.START_DATE >= tanggal_awal,
            CalendarEvent.START_DATE < tanggal_akhir,
        )
        .order_by(CalendarEvent.START_DATE.asc())
        .all()
    )

    for event in rapat_rows:
        attendance = (
            AgendaRapatAttendance.query
            .filter(
                AgendaRapatAttendance.EVENT_ID == event.EVENT_ID,
                AgendaRapatAttendance.NIP == nip,
                AgendaRapatAttendance.STATUS == "HADIR",
            )
            .order_by(AgendaRapatAttendance.SCANNED_DATE.asc())
            .first()
        )

        events.append({
            "id": f"RAPAT-{event.EVENT_ID}-{nip}",
            "title": event.TITLE,
            "type": "RAPAT",
            "source": "AGENDA_RAPAT",
            "start": event.START_DATE.isoformat() if event.START_DATE else None,
            "end": event.END_DATE.isoformat() if event.END_DATE else (
                event.START_DATE.isoformat() if event.START_DATE else None
            ),
            "all_day": False,
            "description": event.DESCRIPTION,
            "location": event.LOCATION,
            "event_id": event.EVENT_ID,
            "status": event.STATUS,
            "attendance_at": (
                attendance.SCANNED_DATE.isoformat()
                if attendance else None
            ),
        })

    # ============================================================
    # 7. KESAMAPTAAN
    #
    # Hanya pegawai yang benar-benar tercatat HADIR melalui QR
    # yang mendapatkan event setelah kegiatan SELESAI.
    # ============================================================

    kesamaptaan_rows = (
        db.session.query(KesamaptaanKegiatan, KesamaptaanKehadiran)
        .join(
            KesamaptaanKehadiran,
            KesamaptaanKehadiran.KEGIATAN_ID == KesamaptaanKegiatan.KEGIATAN_ID,
        )
        .filter(
            KesamaptaanKehadiran.NIP == nip,
            KesamaptaanKehadiran.STATUS == "HADIR",
            KesamaptaanKegiatan.STATUS == "SELESAI",
            KesamaptaanKegiatan.TANGGAL >= tanggal_awal,
            KesamaptaanKegiatan.TANGGAL < tanggal_akhir,
        )
        .order_by(KesamaptaanKegiatan.TANGGAL.asc(), KesamaptaanKegiatan.JAM.asc())
        .all()
    )

    for kegiatan, attendance in kesamaptaan_rows:
        events.append({
            "id": f"KESAMAPTAAN-{kegiatan.KEGIATAN_ID}-{nip}",
            "title": kegiatan.JUDUL,
            "type": "KESAMAPTAAN",
            "source": "KESAMAPTAAN",
            "start": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
            "end": f"{kegiatan.TANGGAL.isoformat()}T{kegiatan.JAM.strftime('%H:%M')}:00",
            "all_day": False,
            "description": "Kesamaptaan Pegawai Kantor SAR Surabaya",
            "location": "Kantor SAR Surabaya",
            "event_id": kegiatan.KEGIATAN_ID,
            "status": kegiatan.STATUS,
            "attendance_at": attendance.SCANNED_DATE.isoformat(),
            "pdf_available": bool(kegiatan.PDF_PATH),
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
