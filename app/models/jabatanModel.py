# app/models/jabatanModel.py

from sqlalchemy.orm import synonym

from app import db


class MfJabatan(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy MF_JABATAN.

    Mapping mengikuti database HRIS legacy hasil migrasi
    tanpa mengubah struktur database.

    Legacy columns:
        JabatanID
        NamaJabatan
        ParentID
        UrutJabatan
        IsUse
        UpdateBy
        UpdateDate
        TypeJabatan
        IDGroupJabatan
        JabatanIDOld
        IDSubGroupJabatan

    Primary Key:
        JabatanID

    Compatibility aliases:
        JABATAN_ID             -> JabatanID
        NAMA_JABATAN          -> NamaJabatan
        PARENT_ID             -> ParentID
        URUT_JABATAN          -> UrutJabatan
        IS_USE                -> IsUse
        UPDATE_BY             -> UpdateBy
        UPDATE_DATE           -> UpdateDate
        TYPE_JABATAN          -> TypeJabatan
        GROUP_JABATAN_ID      -> IDGroupJabatan
        JABATAN_ID_OLD        -> JabatanIDOld
        SUB_GROUP_JABATAN_ID  -> IDSubGroupJabatan
    """

    __tablename__ = 'MF_JABATAN'

    # ============================================================
    # LEGACY DATABASE COLUMNS
    # ============================================================

    JABATAN_ID = db.Column(
        'JabatanID',
        db.Integer,
        primary_key=True,
        nullable=False,
    )

    NAMA_JABATAN = db.Column(
        'NamaJabatan',
        db.String(100),
        nullable=True,
    )

    PARENT_ID = db.Column(
        'ParentID',
        db.Integer,
        nullable=True,
    )

    URUT_JABATAN = db.Column(
        'UrutJabatan',
        db.Integer,
        nullable=True,
    )

    IS_USE = db.Column(
        'IsUse',
        db.String(2),
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

    TYPE_JABATAN = db.Column(
        'TypeJabatan',
        db.String(10),
        nullable=True,
    )

    GROUP_JABATAN_ID = db.Column(
        'IDGroupJabatan',
        db.Integer,
        nullable=True,
    )

    JABATAN_ID_OLD = db.Column(
        'JabatanIDOld',
        db.Integer,
        nullable=True,
    )

    SUB_GROUP_JABATAN_ID = db.Column(
        'IDSubGroupJabatan',
        db.Integer,
        nullable=True,
    )

    # ============================================================
    # COMPATIBILITY ALIASES
    # ============================================================

    JABATAN_ID_BARU = synonym('JABATAN_ID')

    JABATAN_MANAGE = synonym('PARENT_ID')

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<Jabatan '
            f'{self.JABATAN_ID} - '
            f'{self.NAMA_JABATAN}>'
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        return {
            'jabatan_id': self.JABATAN_ID,
            'nama_jabatan': self.NAMA_JABATAN,
            'parent_id': self.PARENT_ID,
            'group_jabatan_id': self.GROUP_JABATAN_ID,
            'sub_group_jabatan_id': self.SUB_GROUP_JABATAN_ID,
            'jabatan_id_old': self.JABATAN_ID_OLD,
            'urut_jabatan': self.URUT_JABATAN,
            'type_jabatan': self.TYPE_JABATAN,
            'is_use': self.IS_USE,
        }
