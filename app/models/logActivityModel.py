# app/models/logActivityModel.py
from app import db


class LogActivity(db.Model):
    """
    Model untuk tabel LOG_ACTIVITIY.
    """
    __tablename__ = 'LOG_ACTIVITIY'

    # Tabel legacy LOG_ACTIVITIY tidak memiliki kolom ID.
    # GUID_LOG adalah identifier unik yang tersedia dan menjadi
    # primary key ORM agar SQLAlchemy tidak meminta kolom ID.
    GUID_LOG = db.Column(
        db.String(50),
        primary_key=True,
        nullable=False,
        unique=True,
    )

    # ✅ TANPA FOREIGN KEY - semua kolom biasa
    TRAKSAKSI_ID = db.Column(db.Integer, nullable=False)
    UNIT_KERJA_ID = db.Column(db.Integer, nullable=False)
    GUID_LOG_BACKUP = db.Column(db.String(50), nullable=False)
    GUID_TIM = db.Column(db.String(50), nullable=False)
    STATUS_ID = db.Column(db.Integer, nullable=False)
    NIP = db.Column(db.String(50), nullable=False)

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
        return f'<LogActivity {self.GUID_LOG}>'