from datetime import datetime
import secrets

from app import db


class RekamMedisKegiatan(db.Model):
    __tablename__ = "REKAM_MEDIS_KEGIATAN"

    KEGIATAN_ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    JENIS = db.Column(db.String(20), nullable=False)
    JUDUL = db.Column(db.String(250), nullable=False)
    TANGGAL = db.Column(db.Date, nullable=False)
    JAM = db.Column(db.Time, nullable=False)
    STATUS = db.Column(db.String(20), nullable=False, default="TERJADWAL")
    QR_TOKEN = db.Column(db.String(120), nullable=False, unique=True)
    QR_ACTIVE = db.Column(db.String(1), nullable=False, default="Y")
    CREATED_BY = db.Column(db.String(50), nullable=False)
    CREATED_AT = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    UPDATED_BY = db.Column(db.String(50), nullable=True)
    UPDATED_AT = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)

    @staticmethod
    def new_token():
        return secrets.token_urlsafe(48)

    def to_dict(self, total=0, selesai=0, menunggu=0):
        return {
            "kegiatan_id": self.KEGIATAN_ID,
            "jenis": self.JENIS,
            "judul": self.JUDUL,
            "tanggal": self.TANGGAL.isoformat() if self.TANGGAL else None,
            "jam": self.JAM.strftime("%H:%M") if self.JAM else None,
            "status": self.STATUS,
            "qr_active": self.QR_ACTIVE == "Y",
            "total_peserta": total,
            "sudah_diperiksa": selesai,
            "belum_diperiksa": menunggu,
        }
