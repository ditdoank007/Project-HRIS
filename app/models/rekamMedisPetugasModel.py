from app import db


class RekamMedisPetugas(db.Model):
    __tablename__ = "REKAM_MEDIS_KEGIATAN_PETUGAS"

    PETUGAS_ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    KEGIATAN_ID = db.Column(db.BigInteger, nullable=False)
    NIP = db.Column(db.String(50), nullable=True)
    NAMA_PETUGAS = db.Column(db.String(150), nullable=False)
    CREATED_AT = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    def to_dict(self):
        return {
            "petugas_id": self.PETUGAS_ID,
            "kegiatan_id": self.KEGIATAN_ID,
            "nip": self.NIP,
            "nama": self.NAMA_PETUGAS,
            "sumber": "PEGAWAI" if self.NIP else "MANUAL",
        }
