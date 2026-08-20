# app/models/hakAksesFormModel.py
from app import db


class HakAksesForm(db.Model):
    """
    Model untuk tabel HAK_AKSES_FORM.
    Menentukan hak akses user terhadap form/menu tertentu.

    Composite Primary Key : FORM_ID + NIP
    Foreign Key           : FORM_ID -> MF_FORM (FORM_ID)
                            NIP     -> PEGAWAI (NIP)
    """
    __tablename__ = 'HAK_AKSES_FORM'

    # Primary Keys (sekaligus foreign keys)
    FORM_ID = db.Column(
        'FormID',
        db.String(50),
        db.ForeignKey('MF_FORM.FormID'),
        primary_key=True,
        nullable=False
    )
    NIP = db.Column(
        'NIP',
        db.String(20),
        db.ForeignKey('PEGAWAI.NIP'),
        primary_key=True,
        nullable=False
    )

    # Hak akses
    IS_AKSES = db.Column('isAkses', db.String(5))    # Y/N
    TYPE_AKSES = db.Column('TypeAkses', db.String(5))  # Jenis akses
    ID_UNIT_KERJA = db.Column('IdUnitKerja', db.String(5))
    MODUL = db.Column('Modul', db.String(50))

    # Metadata
    UPDATE_BY = db.Column('Updateby', db.String(50))
    UPDATE_DATE = db.Column('UpdateDate', db.DateTime)

    def __repr__(self):
        return f'<HakAksesForm Form:{self.FORM_ID} NIP:{self.NIP}>'

    def to_dict(self):
        return {
            'form_id': self.FORM_ID,
            'nip': self.NIP,
            'is_akses': self.IS_AKSES,
            'type_akses': self.TYPE_AKSES,
            'modul': self.MODUL,
            'update_by': self.UPDATE_BY,
            'update_date': self.UPDATE_DATE.isoformat() if self.UPDATE_DATE else None
        }