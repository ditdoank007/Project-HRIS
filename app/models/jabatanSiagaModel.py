from app import db


class MfJabatanSiaga(db.Model):
    __tablename__ = 'MF_JABATAN_SIAGA'

    ID_JABATAN_SIAGA = db.Column(
        'IDJabatanSiaga',
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    NO_URUT = db.Column(
        'NoUrut',
        db.Integer,
        nullable=False
    )

    NAMA_JABATAN = db.Column(
        'NamaJabatan',
        db.String(50),
        nullable=False
    )

    KETERANGAN = db.Column(
        'Keterangan',
        db.String(250),
        nullable=True
    )

    IS_AKTIF = db.Column(
        'IsAktif',
        db.String(1),
        nullable=False,
        default='Y'
    )

    UPDATE_BY = db.Column(
        'UpdateBy',
        db.String(50),
        nullable=True
    )

    UPDATE_DATE = db.Column(
        'UpdateDate',
        db.DateTime,
        nullable=True
    )

    def to_dict(self):
        return {
            'id': self.ID_JABATAN_SIAGA,
            'no_urut': self.NO_URUT,
            'nama_jabatan': self.NAMA_JABATAN,
            'keterangan': self.KETERANGAN,
            'is_aktif': self.IS_AKTIF,
            'update_by': self.UPDATE_BY,
            'update_date': self.UPDATE_DATE.isoformat()
            if self.UPDATE_DATE else None,
        }
