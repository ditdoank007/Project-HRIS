# app/models/golonganModel.py

from sqlalchemy.orm import synonym

from app import db


class MfGolongan(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy MF_GOL.

    Mapping mengikuti database HRIS legacy hasil migrasi
    tanpa mengubah struktur database.

    Legacy columns:
        Gol
        Pangkat
        Urutan
        TransacID
        GroupGol

    Primary Key:
        TransacID

    Compatibility aliases:
        GOL_ID       -> Gol
        NAMA_GOL     -> Gol
        PANGKAT_GOL  -> Pangkat
        URUT_GOL     -> Urutan
        TRANSAC_ID   -> TransacID
        GROUP_GOL    -> GroupGol

    Catatan:
        GOL_ID sengaja menunjuk ke kolom Gol karena PEGAWAI.Gol
        menyimpan kode golongan seperti III/d, bukan TransacID.
    """

    __tablename__ = 'MF_GOL'

    # ============================================================
    # LEGACY DATABASE COLUMNS
    # ============================================================

    GOL = db.Column(
        'Gol',
        db.String(50),
        nullable=True,
    )

    PANGKAT = db.Column(
        'Pangkat',
        db.String(50),
        nullable=True,
    )

    URUTAN = db.Column(
        'Urutan',
        db.Integer,
        nullable=True,
    )

    TRANSAC_ID = db.Column(
        'TransacID',
        db.BigInteger,
        primary_key=True,
        nullable=False,
    )

    GROUP_GOL = db.Column(
        'GroupGol',
        db.String(2),
        nullable=True,
    )

    # ============================================================
    # COMPATIBILITY ALIASES
    # ============================================================

    GOL_ID = synonym('GOL')
    NAMA_GOL = synonym('GOL')
    PANGKAT_GOL = synonym('PANGKAT')
    URUT_GOL = synonym('URUTAN')

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return f'<Golongan {self.GOL_ID} - {self.PANGKAT_GOL}>'

    def to_dict(self):
        return {
            'gol_id': self.GOL_ID,
            'nama_gol': self.NAMA_GOL,
            'pangkat_gol': self.PANGKAT_GOL,
            'urut_gol': self.URUT_GOL,
            'transac_id': self.TRANSAC_ID,
            'group_gol': self.GROUP_GOL,
        }
