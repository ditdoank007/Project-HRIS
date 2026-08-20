# app/models/classModel.py

from sqlalchemy.orm import synonym

from app import db


class MfClass(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy MF_CLASS.

    Mapping mengikuti database HRIS legacy.

    Legacy columns:
        ClassID
        Tunjangan
        ID
        UpdateBy
        UpdateDate
        TglMulai
        DokReff

    Catatan:
        MF_CLASS legacy tidak mempunyai PRIMARY KEY pada DDL.
        Kolom ID bersifat NOT NULL dan digunakan sebagai identifier
        baris legacy.

    Compatibility aliases:
        CLASS_ID     -> ClassID
        TUNJANGAN    -> Tunjangan
        ID           -> ID
        UPDATE_BY    -> UpdateBy
        UPDATE_DATE  -> UpdateDate
        TGL_MULAI    -> TglMulai
        DOKREFF      -> DokReff
    """

    __tablename__ = 'MF_CLASS'

    # ============================================================
    # LEGACY DATABASE COLUMNS
    # ============================================================

    # SQLAlchemy membutuhkan primary key untuk ORM mapping.
    #
    # Karena database legacy tidak mendefinisikan PK, kita gunakan
    # kombinasi ClassID + ID sebagai composite ORM primary key.
    #
    # Ini TIDAK mengubah database.
    CLASS_ID = db.Column(
        'ClassID',
        db.Integer,
        primary_key=True,
    )

    ID = db.Column(
        'ID',
        db.Integer,
        primary_key=True,
        nullable=False,
    )

    TUNJANGAN = db.Column(
        'Tunjangan',
        db.Float,
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

    TGL_MULAI = db.Column(
        'TglMulai',
        db.DateTime,
        nullable=True,
    )

    DOKREFF = db.Column(
        'DokReff',
        db.String(250),
        nullable=True,
    )

    # ============================================================
    # COMPATIBILITY ALIASES
    # ============================================================

    UPDATE_BY = synonym('UPDATE_IN_BY')

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<MfClass CLASS_ID={self.CLASS_ID} '
            f'ID={self.ID}>'
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        return {
            'class_id': self.CLASS_ID,
            'tunjangan': self.TUNJANGAN,
            'id': self.ID,
            'tgl_mulai': (
                self.TGL_MULAI.isoformat()
                if self.TGL_MULAI
                else None
            ),
            'dokreff': self.DOKREFF,
        }
