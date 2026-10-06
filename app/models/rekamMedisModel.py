# app/models/rekamMedisModel.py
from datetime import datetime

from app import db


class RekamMedis(db.Model):
    __tablename__ = "REKAM_MEDIS"

    REKAM_ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    JENIS_PASIEN = db.Column(db.String(20), nullable=False)  # PEGAWAI / NON_PEGAWAI
    NIP = db.Column(db.String(50), nullable=True)
    NIK = db.Column(db.String(32), nullable=True)
    NAMA = db.Column(db.String(150), nullable=False)
    UNIT_KERJA = db.Column(db.String(100), nullable=True)
    INSTANSI = db.Column(db.String(200), nullable=True)
    EMAIL = db.Column(db.String(150), nullable=True)
    NO_HANDPHONE = db.Column(db.String(50), nullable=True)

    TEKANAN_DARAH = db.Column(db.String(20), nullable=True)
    NADI = db.Column(db.Integer, nullable=True)
    FREKUENSI_NAFAS = db.Column(db.Integer, nullable=True)
    SUHU = db.Column(db.Numeric(4, 1), nullable=True)
    SPO2 = db.Column(db.Integer, nullable=True)
    KELUHAN = db.Column(db.Text, nullable=True)
    TINDAKAN = db.Column(db.Text, nullable=True)
    HASIL_KEBUGARAN = db.Column(db.String(20), nullable=True)  # FIT / UNFIT

    PEMERIKSA = db.Column(db.String(150), nullable=True)
    CREATED_BY = db.Column(db.String(50), nullable=True)
    CREATED_AT = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    UPDATED_AT = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "rekam_id": self.REKAM_ID,
            "jenis_pasien": self.JENIS_PASIEN,
            "nip": self.NIP,
            "nik": self.NIK,
            "nama": self.NAMA,
            "unit_kerja": self.UNIT_KERJA,
            "instansi": self.INSTANSI,
            "email": self.EMAIL,
            "no_handphone": self.NO_HANDPHONE,
            "tekanan_darah": self.TEKANAN_DARAH,
            "nadi": self.NADI,
            "frekuensi_nafas": self.FREKUENSI_NAFAS,
            "suhu": float(self.SUHU) if self.SUHU is not None else None,
            "spo2": self.SPO2,
            "keluhan": self.KELUHAN,
            "tindakan": self.TINDAKAN,
            "hasil_kebugaran": self.HASIL_KEBUGARAN,
            "pemeriksa": self.PEMERIKSA,
            "created_by": self.CREATED_BY,
            "created_at": self.CREATED_AT.isoformat() if self.CREATED_AT else None,
            "updated_at": self.UPDATED_AT.isoformat() if self.UPDATED_AT else None,
        }
