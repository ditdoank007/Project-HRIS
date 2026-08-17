# app/models/sprinHeaderModel.py
from app import db


class SprinHeader(db.Model):
    """Model untuk tabel SPRIN_HEADER."""
    __tablename__ = 'SPRIN_HEADER'  # ✅ HARUS HURUF KECIL (sesuai database)

    GUID_SPRIN = db.Column(db.String(50), primary_key=True, nullable=False)
    TYPE_SPRIN_ID = db.Column(db.String(20), nullable=True)
    UPDATE_BY = db.Column(db.String(50))
    UPDATE_DATE = db.Column(db.DateTime)
    ROLE_NUMBER = db.Column(db.Integer)
    ABSENSI_FINGER = db.Column(db.String(2))
    TGL_SPRIN = db.Column(db.Date)
    PERIHAL_SPRIN = db.Column(db.String(250))
    MENIMBANG_1 = db.Column(db.String(250))
    MENIMBANG_2 = db.Column(db.String(250))
    MENIMBANG_3 = db.Column(db.String(250))
    DASAR_1 = db.Column(db.String(250))
    DASAR_2 = db.Column(db.String(250))
    DASAR_3 = db.Column(db.String(250))
    UNTUK_1 = db.Column(db.String(250))
    UNTUK_2 = db.Column(db.String(250))
    UNTUK_3 = db.Column(db.String(250))
    UNTUK_4 = db.Column(db.String(250))
    UNTUK_5 = db.Column(db.String(250))
    JABATAN_OTO = db.Column(db.String(100))
    NIP_OTO = db.Column(db.String(50))
    NO_URUT_SPRIN = db.Column(db.String(5))
    NO_SISIPAN = db.Column(db.String(50))
    NO_SPRIN = db.Column(db.String(50))
    TGL_AWAL_SPRIN = db.Column(db.Date)
    TGL_AKHIR_SPRIN = db.Column(db.String(50))
    PENEMPATAN = db.Column(db.String(150))
    STATUS_UM = db.Column(db.Integer)

    def __repr__(self):
        return f'<SprinHeader {self.GUID_SPRIN}>'