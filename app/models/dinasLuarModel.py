# app/models/dinasLuarModel.py
from app import db


class DinasLuar(db.Model):
    """Model untuk tabel DINAS_LUAR."""
    __tablename__ = 'dinas_luar'  # ✅ HARUS HURUF KECIL (sesuai database)

    DINAS_TRANSAKSI_ID = db.Column(db.String(50), primary_key=True)
    GUID_SPRIN = db.Column(db.String(50), nullable=True)
    NIP = db.Column(db.String(50), nullable=True)
    TGL_AWAL_DINAS_LUAR = db.Column(db.DateTime, nullable=True)
    TGL_AKHIR_DINAS_LUAR = db.Column(db.DateTime, nullable=True)
    KETERANGAN_DINAS_LUAR = db.Column(db.String(450), nullable=True)
    PENEMPATAN_DINAS_LUAR = db.Column(db.String(350), nullable=True)
    TRANSAKSI = db.Column(db.String(50), nullable=True)
    PENDUKUNG = db.Column(db.String(50), nullable=True)
    NO_SURAT = db.Column(db.String(250), nullable=True)
    JENIS = db.Column(db.String(10), nullable=True)
    NAMA_FILE = db.Column(db.String(100), nullable=True)
    TGL_AWAL_SURAT = db.Column(db.Date, nullable=True)
    TGL_AKHIR_SURAT = db.Column(db.Date, nullable=True)
    TGL_EMAIL = db.Column(db.DateTime, nullable=True)
    TIPE = db.Column(db.Integer, nullable=True)
    STATUS_UM = db.Column(db.Integer, nullable=True)
    UPDATE_BY = db.Column(db.String(50), nullable=True)
    UPDATE_DATE = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<DinasLuar {self.DINAS_TRANSAKSI_ID}>'