# app/models/userAccountModel.py
from app import db


class UserAccount(db.Model):
    """
    Model tabel USER_ACCOUNT legacy HRIS.

    Mapping database legacy:
        UserID     -> NIP aplikasi
        IntLevel   -> INIT_LEVEL aplikasi
        Modul      -> MODUL
        UpdateBy   -> UPDATE_BY
        UpdateDate -> UPDATE_DATE

    Catatan:
    Tabel legacy USER_ACCOUNT tidak memiliki PRIMARY KEY pada DDL.
    Karena SQLAlchemy membutuhkan primary key untuk ORM, UserID
    digunakan sebagai identity ORM sementara.

    Jangan mengubah struktur database legacy.
    """

    __tablename__ = 'USER_ACCOUNT'

    # USER_ACCOUNT legacy tidak memiliki PRIMARY KEY fisik.
    # Untuk identity ORM, kombinasi UserID + Modul digunakan sebagai
    # composite identity karena satu UserID dapat memiliki beberapa
    # account untuk modul yang berbeda (HRIS, eDoc, Esprin, Umum).
    NIP = db.Column(
        'UserID',
        db.String(50),
        primary_key=True
    )

    INIT_LEVEL = db.Column(
        'IntLevel',
        db.Integer,
        nullable=True
    )

    MODUL = db.Column(
        'Modul',
        db.String(50),
        primary_key=True,
        nullable=True
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

    def __repr__(self):
        return f'<UserAccount {self.NIP} - {self.MODUL}>'

    def to_dict(self):
        return {
            'nip': self.NIP,
            'init_level': self.INIT_LEVEL,
            'modul': self.MODUL,
            'update_by': self.UPDATE_BY,
            'update_date': (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE
                else None
            ),
        }
