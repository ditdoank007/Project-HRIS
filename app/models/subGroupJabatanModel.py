# app/models/subGroupJabatanModel.py
from app import db


class MfSubGroupJabatan(db.Model):
    """
    Model untuk tabel MF_SUB_GROUP_JABATAN.
    Menyimpan data master sub-kelompok jabatan.

    Primary Key : SUB_GROUP_JABATAN_ID
    """
    __tablename__ = 'MF_SUB_GROUP_JABATAN'

    # Primary Key
    # Python attribute tetap dipertahankan untuk kompatibilitas
    # dengan controller/template HRIS Reborn.
    # Nama kolom mengikuti schema legacy HRIS di CT128.
    SUB_GROUP_JABATAN_ID = db.Column(
        'IDSubGroupJabatan',
        db.Integer,
        primary_key=True,
        nullable=False
    )

    # Nama sub-kelompok jabatan
    NAMA_SUB_GROUP_JABATAN = db.Column(
        'SubGroupJabatan',
        db.String(150),
        nullable=True
    )

    def __repr__(self):
        return f'<MfSubGroupJabatan {self.SUB_GROUP_JABATAN_ID} - {self.NAMA_SUB_GROUP_JABATAN}>'

    def to_dict(self):
        return {
            'sub_group_jabatan_id': self.SUB_GROUP_JABATAN_ID,
            'nama_sub_group_jabatan': self.NAMA_SUB_GROUP_JABATAN
        }