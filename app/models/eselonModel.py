# app/models/eselonModel.py

from app import db


class MfEselon(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy MF_ESELON.

    Mapping mengikuti database HRIS legacy hasil migrasi
    tanpa mengubah struktur database.

    Legacy columns:
        eselon
        UrutEselon

    Catatan:
        Database legacy tidak mendefinisikan PRIMARY KEY.
        Karena SQLAlchemy ORM membutuhkan identifier, ESELON
        digunakan sebagai ORM primary key berdasarkan struktur
        data legacy yang tersedia.

    Compatibility:
        ESELON       -> eselon
        URUT_ESELON  -> UrutEselon
    """

    __tablename__ = 'MF_ESELON'

    # ============================================================
    # LEGACY DATABASE COLUMNS
    # ============================================================

    ESELON = db.Column(
        'eselon',
        db.String(50),
        primary_key=True,
    )

    URUT_ESELON = db.Column(
        'UrutEselon',
        db.Integer,
        nullable=True,
    )

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return f'<Eselon {self.ESELON}>'

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        return {
            'eselon': self.ESELON,
            'urut_eselon': self.URUT_ESELON,
        }
