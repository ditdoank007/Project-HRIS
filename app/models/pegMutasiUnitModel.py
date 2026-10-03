# app/models/pegMutasiUnitModel.py
from app import db

class PegMutasiUnit(db.Model):
    """
    Model untuk tabel PEG_MUTASI_UNIT.
    """
    __tablename__ = 'PEG_MUTASI_UNIT'

    # Composite Primary Key
    # HRIS 2013 physical column: IDTransaksi.\n    # Database membuat nomor transaksi otomatis saat INSERT.\n    TRAKSAKSI_ID = db.Column(\n        'IDTransaksi',\n        db.Integer,\n        primary_key=True,\n        nullable=False,\n        autoincrement=True,\n    )
    NIP = db.Column(db.String(50), primary_key=True, nullable=False)

    TGL_MUTASI = db.Column(db.Date)
    UNIT_KERJA = db.Column(db.String(50))
    UPDATE_BY = db.Column(db.String(50))
    UPDATE_DATE = db.Column(db.DateTime)
    NO_SK = db.Column(db.String(50))
    KETERANGAN = db.Column(db.String(250))

    def __repr__(self):
        return f'<PegMutasiUnit {self.NIP} Trx:{self.TRAKSAKSI_ID}>'