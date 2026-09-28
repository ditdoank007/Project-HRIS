from datetime import date, datetime, time

from flask import jsonify, render_template, request, session
from sqlalchemy import func

from app import db
from app.models.agendaDisposisiModel import AgendaDisposisi, AgendaDisposisiPeserta
from app.models.pegawaiModel import Pegawai


def agenda_disposisi():
    return render_template("pages/dashboard_1/Agenda Disposisi.html")


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Tanggal kegiatan tidak valid.")


def _parse_time(value):
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Jam kegiatan tidak valid.")


def _nips(payload):
    raw = payload.get("participants") or []
    values = [x.get("nip") if isinstance(x, dict) else x for x in raw]
    result = list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))
    if not result:
        raise ValueError("Minimal satu pegawai penerima wajib dipilih.")
    rows = Pegawai.query.filter(Pegawai.NIP.in_(result)).all()
    found = {x.NIP for x in rows}
    missing = [x for x in result if x not in found]
    if missing:
        raise ValueError("NIP pegawai tidak ditemukan: " + ", ".join(missing))
    return result


def _serialize(row):
    parts = (
        db.session.query(AgendaDisposisiPeserta.NIP, Pegawai.NAMA)
        .join(Pegawai, Pegawai.NIP == AgendaDisposisiPeserta.NIP)
        .filter(AgendaDisposisiPeserta.AGENDA_ID == row.ID)
        .all()
    )
    data = row.to_dict()
    data["participants"] = [{"nip": nip, "nama": nama} for nip, nama in parts]
    return data


def api_agenda_disposisi_list():
    rows = AgendaDisposisi.query.order_by(AgendaDisposisi.TANGGAL.desc(), AgendaDisposisi.JAM.desc()).all()
    return jsonify({"status": "success", "data": [_serialize(x) for x in rows]})


def api_agenda_disposisi_save():
    payload = request.get_json(silent=True) or {}
    user = session.get("nip")
    if not user:
        return jsonify({"status": "error", "message": "NIP pengguna tidak ditemukan."}), 401
    try:
        kegiatan = str(payload.get("kegiatan") or "").strip()
        lokasi = str(payload.get("lokasi") or "").strip()
        jenis = str(payload.get("jenis") or "").strip().upper()
        sumber = str(payload.get("sumber_dokumen") or "").strip().upper()
        if not kegiatan or not lokasi:
            raise ValueError("Nama kegiatan dan lokasi wajib diisi.")
        if jenis not in {"DL", "NON DL"}:
            raise ValueError("Jenis disposisi tidak valid.")
        if sumber not in {"SURAT MASUK", "SPRIN"}:
            raise ValueError("Sumber dokumen tidak valid.")
        tanggal = _parse_date(payload.get("tanggal"))
        jam = _parse_time(payload.get("jam"))
        nips = _nips(payload)

        row = AgendaDisposisi(
            KEGIATAN=kegiatan,
            TANGGAL=tanggal,
            JAM=jam,
            LOKASI=lokasi,
            JENIS=jenis,
            SUMBER_DOKUMEN=sumber,
            STATUS="AKTIF",
            CREATED_BY=user,
            CREATED_DATE=datetime.utcnow(),
        )
        db.session.add(row)
        db.session.flush()
        now = datetime.utcnow()
        for nip in nips:
            db.session.add(AgendaDisposisiPeserta(
                AGENDA_ID=row.ID, NIP=nip, STATUS="DITUGASKAN", CREATED_DATE=now
            ))
        db.session.commit()
        return jsonify({"status": "success", "data": _serialize(row)})
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Gagal menyimpan agenda disposisi."}), 500


def api_agenda_disposisi_detail(agenda_id):
    row = AgendaDisposisi.query.get(agenda_id)
    if not row:
        return jsonify({"status": "error", "message": "Agenda disposisi tidak ditemukan."}), 404
    return jsonify({"status": "success", "data": _serialize(row)})


def api_agenda_disposisi_cancel(agenda_id):
    row = AgendaDisposisi.query.get(agenda_id)
    if not row:
        return jsonify({"status": "error", "message": "Agenda disposisi tidak ditemukan."}), 404
    row.STATUS = "BATAL"
    row.UPDATE_BY = session.get("nip", "system")
    row.UPDATE_DATE = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "success", "data": _serialize(row)})
