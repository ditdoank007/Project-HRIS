from datetime import datetime
from app import db


class RekamMedisPeserta(db.Model):
    __tablename__ = "REKAM_MEDIS_PESERTA"

    PESERTA_ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    KEGIATAN_ID = db.Column(db.BigInteger, nullable=False)
    JENIS_PESERTA = db.Column(db.String(20), nullable=False)
    NIP = db.Column(db.String(50), nullable=True)
    NIK = db.Column(db.String(32), nullable=True)
    JENIS_KELAMIN = db.Column(db.String(1), nullable=True)
    NAMA = db.Column(db.String(150), nullable=False)
    UNIT_KERJA = db.Column(db.String(100), nullable=True)
    INSTANSI = db.Column(db.String(200), nullable=True)
    EMAIL = db.Column(db.String(150), nullable=True)
    NO_HANDPHONE = db.Column(db.String(50), nullable=True)
    TANDA_TANGAN = db.Column(db.Text, nullable=True)
    STATUS_PEMERIKSAAN = db.Column(db.String(20), nullable=False, default="MENUNGGU")
    REKAM_ID = db.Column(db.BigInteger, nullable=True)
    SCANNED_AT = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    UPDATED_AT = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "peserta_id": self.PESERTA_ID,
            "kegiatan_id": self.KEGIATAN_ID,
            "jenis_peserta": self.JENIS_PESERTA,
            "nip": self.NIP,
            "nik": self.NIK,
            "jenis_kelamin": self.JENIS_KELAMIN,
            "nama": self.NAMA,
            "unit_kerja": self.UNIT_KERJA,
            "instansi": self.INSTANSI,
            "email": self.EMAIL,
            "no_handphone": self.NO_HANDPHONE,
            "tanda_tangan": self.TANDA_TANGAN,
            "status_pemeriksaan": self.STATUS_PEMERIKSAAN,
            "rekam_id": self.REKAM_ID,
            "scanned_at": self.SCANNED_AT.isoformat() if self.SCANNED_AT else None,
        }
