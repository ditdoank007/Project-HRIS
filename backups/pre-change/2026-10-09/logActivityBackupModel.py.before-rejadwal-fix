# app/models/logActivityBackupModel.py
from app import db


class LogActivityBackup(db.Model):
    """
    Model untuk tabel LOG_ACTIVITIY_BACKUP.
    """
    __tablename__ = 'LOG_ACTIVITIY_BACKUP'

    GUID_LOG_BACKUP = db.Column(db.String(50), primary_key=True, nullable=False)
    GUID_LOG = db.Column(db.String(50), nullable=True)  # ✅ Tanpa FK

    TRX = db.Column(db.String(50))
    ACTIVITY = db.Column(db.String(50))
    ACTIVITY_DATE = db.Column(db.Date)
    NOTE = db.Column(db.String(150))
    TEMPAT = db.Column(db.String(150))
    PERIHAL = db.Column(db.String(150))
    UPDATE_BY = db.Column(db.String(50))
    UPDATE_DATE = db.Column(db.DateTime)
    FUNGSIONAL = db.Column(db.String(50))
    TGL_CLOSING = db.Column(db.Date)
    SHIFT_1 = db.Column(db.Integer)
    SHIFT_2 = db.Column(db.Integer)
    PENGGANTI = db.Column(db.Integer)
    STATUS_TRX = db.Column(db.String(50))
    KET_UPDATE = db.Column(db.String(250))
    NIP_PENGGANTI = db.Column(db.String(50))
    BIAYA = db.Column(db.Float)
    QTY = db.Column(db.Float)
    SATUAN_QTY = db.Column(db.String(50))
    SHIFT = db.Column(db.String(5))
    TRANSAKSI_FORM = db.Column(db.String(50))
    TGL_JAM_IN = db.Column(db.DateTime)
    TGL_JAM_OUT = db.Column(db.DateTime)
    TGL_JAM_BAKU_IN = db.Column(db.DateTime)
    TGL_JAM_BAKU_OUT = db.Column(db.DateTime)

    def __repr__(self):
        return f'<LogActivityBackup {self.GUID_LOG_BACKUP}>'