# app/models/unitKerjaModel.py

from sqlalchemy.orm import synonym

from app import db


class MfUnitKerja(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy MF_UNIT_KERJA.

    Mapping mengikuti database HRIS legacy hasil migrasi
    tanpa mengubah struktur database.

    Legacy columns:
        IDUnitKerja
        UnitKerjaName
        isUse
        Updateby
        Updatedate
        UrutReport
        IsPusat
        TransacID

    Primary Key:
        TransacID

    Compatibility aliases:
        UNIT_KERJA_ID -> IDUnitKerja
        NAMA_UNIT_KERJA -> UnitKerjaName
        IS_USE -> isUse
        UPDATE_BY -> Updateby
        UPDATE_DATE -> Updatedate
        URUT_REPORT -> UrutReport
        IS_PUSAT -> IsPusat
        TRANSAC_ID -> TransacID
    """

    __tablename__ = 'MF_UNIT_KERJA'

    # ============================================================
    # LEGACY DATABASE COLUMNS
    # ============================================================

    ID_UNIT_KERJA = db.Column(
        'IDUnitKerja',
        db.String(50),
        nullable=True,
    )

    UNIT_KERJA_NAME = db.Column(
        'UnitKerjaName',
        db.String(50),
        nullable=True,
    )

    IS_USE = db.Column(
        'isUse',
        db.String(5),
        nullable=True,
    )

    UPDATE_BY = db.Column(
        'Updateby',
        db.String(50),
        nullable=True,
    )

    UPDATE_DATE = db.Column(
        'Updatedate',
        db.DateTime,
        nullable=True,
    )

    URUT_REPORT = db.Column(
        'UrutReport',
        db.Integer,
        nullable=True,
    )

    IS_PUSAT = db.Column(
        'IsPusat',
        db.Integer,
        nullable=True,
    )

    TRANSAC_ID = db.Column(
        'TransacID',
        db.BigInteger,
        primary_key=True,
        nullable=False,
    )

    # ============================================================
    # COMPATIBILITY ALIASES
    # ============================================================

    UNIT_KERJA_ID = synonym('ID_UNIT_KERJA')

    NAMA_UNIT_KERJA = synonym('UNIT_KERJA_NAME')

    # Nama semantik HRIS Reborn.
    # Tetap menggunakan kolom legacy database: isUse.
    IS_AKTIF = synonym('IS_USE')

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<UnitKerja '
            f'{self.UNIT_KERJA_ID} - '
            f'{self.NAMA_UNIT_KERJA}>'
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        return {
            'unit_kerja_id': self.UNIT_KERJA_ID,
            'nama_unit_kerja': self.NAMA_UNIT_KERJA,
            'is_use': self.IS_USE,
            'is_aktif': self.IS_AKTIF,
            'urut_report': self.URUT_REPORT,
            'is_pusat': self.IS_PUSAT,
            'transac_id': self.TRANSAC_ID,
        }
