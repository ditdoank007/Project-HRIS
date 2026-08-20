# app/models/timeRecorderModel.py

from app import db


class TimeRecorder(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy TIME_RECORDER.

    Mapping mengikuti database HRIS legacy
    tanpa mengubah struktur database.

    Legacy columns:
        FingerID
        Waktu
        Status
        Mesin
        Ket
        Transaksi
        UpdateBy
        UpdateDate
        KetInject
        ReffInject
        trx

    Legacy Primary Key:
        (FingerID, Waktu, Status, Mesin)
    """

    __tablename__ = 'TIME_RECORDER'

    # ============================================================
    # LEGACY DATABASE PRIMARY KEY
    # ============================================================

    FINGER_ID = db.Column(
        'FingerID',
        db.String(10),
        primary_key=True,
        nullable=False,
    )

    WAKTU = db.Column(
        'Waktu',
        db.DateTime,
        primary_key=True,
        nullable=False,
    )

    STATUS = db.Column(
        'Status',
        db.String(3),
        primary_key=True,
        nullable=False,
    )

    MESIN = db.Column(
        'Mesin',
        db.String(100),
        primary_key=True,
        nullable=False,
    )

    # ============================================================
    # LEGACY DATA COLUMNS
    # ============================================================

    KET = db.Column(
        'Ket',
        db.String(50),
        nullable=True,
    )

    TRANSAKSI = db.Column(
        'Transaksi',
        db.String(50),
        nullable=True,
    )

    UPDATE_IN_BY = db.Column(
        'UpdateBy',
        db.String(50),
        nullable=True,
    )

    UPDATE_DATE = db.Column(
        'UpdateDate',
        db.DateTime,
        nullable=True,
    )

    KET_INJECT = db.Column(
        'KetInject',
        db.String(150),
        nullable=True,
    )

    REF_INJECT = db.Column(
        'ReffInject',
        db.String(150),
        nullable=True,
    )

    TRX = db.Column(
        'trx',
        db.String(50),
        nullable=True,
    )

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<TimeRecorder '
            f'{self.FINGER_ID} '
            f'{self.WAKTU} '
            f'{self.STATUS} '
            f'{self.MESIN}>'
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        return {
            'finger_id': self.FINGER_ID,
            'waktu': (
                self.WAKTU.isoformat()
                if self.WAKTU else None
            ),
            'status': self.STATUS,
            'mesin': self.MESIN,
            'ket': self.KET,
            'transaksi': self.TRANSAKSI,
            'update_in_by': self.UPDATE_IN_BY,
            'update_date': (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE else None
            ),
            'ket_inject': self.KET_INJECT,
            'ref_inject': self.REF_INJECT,
            'trx': self.TRX,
        }
