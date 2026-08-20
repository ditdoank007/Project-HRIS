# app/models/loadFingerModel.py
from app import db


class MfLoadFinger(db.Model):
    """
    Mapping tabel legacy MF_LOAD_FINGER.

    Database CT128 tidak diubah.
    Nama kolom fisik legacy dipetakan di source HRIS Reborn.
    """

    __tablename__ = 'MF_LOAD_FINGER'

    TRAKSAKSI_ID = db.Column(
        'TransaksiID',
        db.Integer,
        primary_key=True,
        nullable=False,
    )

    START_FINGER = db.Column(
        'StartFinger',
        db.DateTime,
        nullable=True,
    )

    END_FINGER = db.Column(
        'EndFinger',
        db.DateTime,
        nullable=True,
    )

    TGL_MULAI_BERLAKU = db.Column(
        'TglMulaiBerlaku',
        db.Date,
        nullable=True,
    )

    UPDATE_BY = db.Column(
        'UpdateBy',
        db.String(50),
        nullable=True,
    )

    UPDATE_DATE = db.Column(
        'UpdateDate',
        db.DateTime,
        nullable=True,
    )

    SHIFT_KERJA = db.Column(
        'ShiftKerja',
        db.String(2),
        nullable=True,
    )

    START_FINGER_OUT = db.Column(
        'StartFingerOut',
        db.DateTime,
        nullable=True,
    )

    END_FINGER_OUT = db.Column(
        'EndFingerOut',
        db.DateTime,
        nullable=True,
    )

    def __repr__(self):
        return f'<MfLoadFinger {self.TRAKSAKSI_ID}>'

    def to_dict(self):
        return {
            'traksaksi_id': self.TRAKSAKSI_ID,
            'start_finger': (
                self.START_FINGER.isoformat()
                if self.START_FINGER else None
            ),
            'end_finger': (
                self.END_FINGER.isoformat()
                if self.END_FINGER else None
            ),
            'tgl_mulai_berlaku': (
                self.TGL_MULAI_BERLAKU.isoformat()
                if self.TGL_MULAI_BERLAKU else None
            ),
            'update_by': self.UPDATE_BY,
            'update_date': (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE else None
            ),
            'shift_kerja': self.SHIFT_KERJA,
            'start_finger_out': (
                self.START_FINGER_OUT.isoformat()
                if self.START_FINGER_OUT else None
            ),
            'end_finger_out': (
                self.END_FINGER_OUT.isoformat()
                if self.END_FINGER_OUT else None
            ),
        }
