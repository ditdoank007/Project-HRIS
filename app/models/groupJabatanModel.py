# app/models/groupJabatanModel.py
from app import db


class MfGroupJabatan(db.Model):
    """
    Model untuk tabel MF_GROUP_JABATAN.
    Menyimpan data master pengelompokan jabatan.

    Primary Key : GROUP_JABATAN_ID
    """
    __tablename__ = 'MF_GROUP_JABATAN'

    # Primary Key
    # Python attribute tetap dipertahankan untuk kompatibilitas
    # dengan controller/template HRIS Reborn.
    # Nama kolom mengikuti schema legacy HRIS di CT128.
    GROUP_JABATAN_ID = db.Column(
        'IDGroupJabatan',
        db.Integer,
        primary_key=True,
        nullable=False
    )

    # Nama kelompok jabatan
    NAMA_GROUP_JABATAN = db.Column(
        'GroupJabatan',
        db.String(50),
        nullable=True
    )

    def __repr__(self):
        return f'<MfGroupJabatan {self.GROUP_JABATAN_ID} - {self.NAMA_GROUP_JABATAN}>'

    def to_dict(self):
        return {
            'group_jabatan_id': self.GROUP_JABATAN_ID,
            'nama_group_jabatan': self.NAMA_GROUP_JABATAN
        }