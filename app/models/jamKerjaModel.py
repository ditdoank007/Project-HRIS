# app/models/jamKerjaModel.py

from app import db


class MfJamKerja(db.Model):
    """
    Mapping tabel legacy MF_JAM_KERJA.

    Mapping mengikuti nama kolom FISIK database.
    Jangan menggunakan nama kolom asumsi.
    """

    __tablename__ = 'MF_JAM_KERJA'

    # ============================================================
    # PRIMARY KEY
    # ============================================================

    IDJKERJA = db.Column(
        'IDJKerja',
        db.Integer,
        primary_key=True,
        nullable=False,
    )

    # ============================================================
    # JAM KERJA
    # ============================================================

    STD_JAM_IN = db.Column(
        'StdJamIn',
        db.DateTime,
        nullable=True,
    )

    STD_JAM_OUT = db.Column(
        'StdJamOut',
        db.DateTime,
        nullable=True,
    )

    TGL_MULAI_BERLAKU = db.Column(
        'TglMulaiBerlaku',
        db.DateTime,
        nullable=True,
    )

    # ============================================================
    # KONFIGURASI
    # ============================================================

    SHIFT = db.Column(
        'Shift',
        db.String(50),
        nullable=True,
    )

    AGENDA = db.Column(
        'Agenda',
        db.String(50),
        nullable=True,
    )

    PENGGANTIAN_TLM1 = db.Column(
        'PenggantianTLM1',
        db.String(5),
        nullable=True,
    )

    SHIFT_KERJA = db.Column(
        'ShiftKerja',
        db.String(2),
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
        'UpdateDate',
        db.DateTime,
        nullable=True,
    )

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<MfJamKerja '
            f'{self.IDJKERJA} '
            f'{self.SHIFT}>'
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        return {
            'id_j_kerja': self.IDJKERJA,
            'std_jam_in': (
                self.STD_JAM_IN.isoformat()
                if self.STD_JAM_IN
                else None
            ),
            'std_jam_out': (
                self.STD_JAM_OUT.isoformat()
                if self.STD_JAM_OUT
                else None
            ),
            'tgl_mulai_berlaku': (
                self.TGL_MULAI_BERLAKU.isoformat()
                if self.TGL_MULAI_BERLAKU
                else None
            ),
            'shift': self.SHIFT,
            'agenda': self.AGENDA,
            'penggantian_tlm1': self.PENGGANTIAN_TLM1,
            'update_by': self.UPDATE_BY,
            'update_date': (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE
                else None
            ),
            'shift_kerja': self.SHIFT_KERJA,
        }
