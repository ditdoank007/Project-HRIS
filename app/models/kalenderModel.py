# app/models/kalenderModel.py

from sqlalchemy.orm import synonym

from app import db


class MfKalender(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy KALENDER.

    Mapping mengikuti database HRIS legacy.

    Legacy columns:
        Tgl
        IsLibur
        Ket
        UpdateBy
        UpdateDate

    Primary Key:
        Tgl

    Compatibility aliases:
        TGL_KERJA   -> Tgl
        IS_LIBUR    -> IsLibur
        KET         -> Ket
        UPDATE_BY   -> UpdateBy
        UPDATE_DATE -> UpdateDate
    """

    __tablename__ = 'KALENDER'

    # ============================================================
    # LEGACY DATABASE COLUMNS
    # ============================================================

    TGL = db.Column(
        'Tgl',
        db.DateTime,
        primary_key=True,
        nullable=False,
    )

    IS_LIBUR_LEGACY = db.Column(
        'IsLibur',
        db.String(1),
        nullable=True,
    )

    KET = db.Column(
        'Ket',
        db.String(50),
        nullable=True,
    )

    UPDATE_BY_LEGACY = db.Column(
        'UpdateBy',
        db.String(50),
        nullable=True,
    )

    UPDATE_DATE_LEGACY = db.Column(
        'UpdateDate',
        db.DateTime,
        nullable=True,
    )

    # ============================================================
    # COMPATIBILITY ALIASES
    # ============================================================

    TGL_KERJA = synonym('TGL')
    IS_LIBUR = synonym('IS_LIBUR_LEGACY')
    UPDATE_BY = synonym('UPDATE_BY_LEGACY')
    UPDATE_DATE = synonym('UPDATE_DATE_LEGACY')

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<Kalender {self.TGL_KERJA} - '
            f'Libur: {self.IS_LIBUR}>'
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        return {
            'tgl_kerja': (
                self.TGL_KERJA.isoformat()
                if self.TGL_KERJA
                else None
            ),
            'is_libur': self.IS_LIBUR,
            'ket': self.KET,
            'update_by': self.UPDATE_BY,
            'update_date': (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE
                else None
            ),
        }
