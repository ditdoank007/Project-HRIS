# app/models/lemburModel.py

from app import db


class Lembur(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy LEMBUR.

    Mapping mengikuti database HRIS legacy tanpa mengubah
    struktur database.

    Legacy columns:
        fingerid
        tglkerja
        jamin
        jamout
        Updateby
        Updatedate
        keterangan
        nosurat
        jambakuin
        jambakuout

    Database legacy tidak mendefinisikan PRIMARY KEY.

    Hasil audit menunjukkan:
        fingerid + tglkerja
        merupakan natural key unik untuk seluruh 1.704 record.

    ORM identity:
        FINGER_ID + TGL_KERJA

    Catatan:
        NIP bukan kolom pada LEMBUR legacy.
        Resolusi FingerID -> PEGAWAI.NIP dilakukan pada
        layer query/service.
    """

    __tablename__ = 'LEMBUR'

    # ============================================================
    # ORM IDENTITY
    # ============================================================

    FINGER_ID = db.Column(
        'fingerid',
        db.String(50),
        primary_key=True,
        nullable=False,
    )

    TGL_KERJA = db.Column(
        'tglkerja',
        db.Date,
        primary_key=True,
        nullable=False,
    )

    # ============================================================
    # JAM LEMBUR AKTUAL
    # ============================================================

    JAM_IN = db.Column(
        'jamin',
        db.DateTime,
        nullable=True,
    )

    JAM_OUT = db.Column(
        'jamout',
        db.DateTime,
        nullable=True,
    )

    # ============================================================
    # JAM BAKU
    # ============================================================

    JAM_BAKU_IN = db.Column(
        'jambakuin',
        db.DateTime,
        nullable=True,
    )

    JAM_BAKU_OUT = db.Column(
        'jambakuout',
        db.DateTime,
        nullable=True,
    )

    # ============================================================
    # KETERANGAN / SURAT
    # ============================================================

    KETERANGAN = db.Column(
        'keterangan',
        db.String(50),
        nullable=True,
    )

    NO_SURAT = db.Column(
        'nosurat',
        db.String(50),
        nullable=True,
    )

    # ============================================================
    # AUDIT
    # ============================================================

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

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<Lembur '
            f'FingerID:{self.FINGER_ID} '
            f'Tgl:{self.TGL_KERJA}>'
        )

    def to_dict(self):
        return {
            'finger_id': self.FINGER_ID,
            'tgl_kerja': (
                self.TGL_KERJA.isoformat()
                if self.TGL_KERJA else None
            ),
            'jam_in': (
                self.JAM_IN.strftime('%H:%M:%S')
                if self.JAM_IN else None
            ),
            'jam_out': (
                self.JAM_OUT.strftime('%H:%M:%S')
                if self.JAM_OUT else None
            ),
            'jam_baku_in': (
                self.JAM_BAKU_IN.strftime('%H:%M:%S')
                if self.JAM_BAKU_IN else None
            ),
            'jam_baku_out': (
                self.JAM_BAKU_OUT.strftime('%H:%M:%S')
                if self.JAM_BAKU_OUT else None
            ),
            'keterangan': self.KETERANGAN,
            'no_surat': self.NO_SURAT,
            'update_by': self.UPDATE_BY,
            'update_date': (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE else None
            ),
        }
