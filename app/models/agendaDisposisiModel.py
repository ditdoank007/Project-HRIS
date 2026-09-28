from app import db
from datetime import datetime


class AgendaDisposisi(db.Model):
    __tablename__ = "AGENDA_DISPOSISI"

    ID = db.Column("ID", db.BigInteger, primary_key=True, autoincrement=True)
    KEGIATAN = db.Column("KEGIATAN", db.String(250), nullable=False)
    TANGGAL = db.Column("TANGGAL", db.Date, nullable=False)
    JAM = db.Column("JAM", db.Time, nullable=False)
    LOKASI = db.Column("LOKASI", db.String(250), nullable=False)
    JENIS = db.Column("JENIS", db.String(20), nullable=False)
    SUMBER_DOKUMEN = db.Column("SUMBER_DOKUMEN", db.String(30), nullable=False)
    DOCUMENT_NAME = db.Column("DOCUMENT_NAME", db.String(255))
    DOCUMENT_PATH = db.Column("DOCUMENT_PATH", db.String(500))
    STATUS = db.Column("STATUS", db.String(20), nullable=False, default="AKTIF")
    CREATED_BY = db.Column("CREATED_BY", db.String(50), nullable=False)
    CREATED_DATE = db.Column("CREATED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
    UPDATE_BY = db.Column("UPDATE_BY", db.String(50))
    UPDATE_DATE = db.Column("UPDATE_DATE", db.DateTime)

    def to_dict(self):
        return {
            "id": self.ID,
            "kegiatan": self.KEGIATAN,
            "tanggal": self.TANGGAL.isoformat() if self.TANGGAL else None,
            "jam": self.JAM.strftime("%H:%M") if self.JAM else None,
            "lokasi": self.LOKASI,
            "jenis": self.JENIS,
            "sumber_dokumen": self.SUMBER_DOKUMEN,
            "document_name": self.DOCUMENT_NAME,
            "status": self.STATUS,
        }


class AgendaDisposisiPeserta(db.Model):
    __tablename__ = "AGENDA_DISPOSISI_PESERTA"

    ID = db.Column("ID", db.BigInteger, primary_key=True, autoincrement=True)
    AGENDA_ID = db.Column("AGENDA_ID", db.BigInteger, nullable=False)
    NIP = db.Column("NIP", db.String(50), nullable=False)
    STATUS = db.Column("STATUS", db.String(20), nullable=False, default="DITUGASKAN")
    CREATED_DATE = db.Column("CREATED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
