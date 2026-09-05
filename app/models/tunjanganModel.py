from app import db


class MfTunjangan(db.Model):
    """
    Mapping ORM ke tabel legacy MF_TUNJANGAN.

    Catatan:
    - Database TIDAK memiliki PRIMARY KEY formal.
    - IDTunjangan saat ini unik dan dipakai aplikasi sebagai logical key.
    - primary_key=True di SQLAlchemy TIDAK mengubah schema database.
    """

    __tablename__ = "MF_TUNJANGAN"

    IDTUNJANGAN = db.Column("IDTunjangan", db.Integer, primary_key=True)

    JENIS_TUNJANGAN = db.Column("JenisTunjangan", db.String(50), nullable=True)
    ACTIVITY = db.Column("Activity", db.String(50), nullable=True)
    NOMINAL = db.Column("Nominal", db.Float, nullable=True)
    TGL_MULAI = db.Column("TglMulai", db.Date, nullable=True)
    HARI_KERJA = db.Column("HariKerja", db.Integer, nullable=True)
    FUNGSIONAL = db.Column("Fungsional", db.String(50), nullable=True)
    UPDATE_BY = db.Column("UpdateBy", db.String(50), nullable=True)
    UPDATE_DATE = db.Column("UpdateDate", db.DateTime, nullable=True)
    DOKREFF = db.Column("DokReff", db.String(250), nullable=True)
    STATUS_PEG = db.Column("StatusPeg", db.Integer, nullable=True)
    ID_UNIT_KERJA = db.Column("IDUnitKerja", db.String(50), nullable=True)
    SHIFT = db.Column("Shift", db.String(5), nullable=True)

    def __repr__(self):
        return (
            f"<MfTunjangan {self.IDTUNJANGAN} - "
            f"{self.JENIS_TUNJANGAN}>"
        )

    def to_dict(self):
        return {
            "tunjangan_id": self.IDTUNJANGAN,
            "jenis_tunjangan": self.JENIS_TUNJANGAN,
            "activity": self.ACTIVITY,
            "nominal": self.NOMINAL,
            "tgl_mulai": (
                self.TGL_MULAI.isoformat()
                if self.TGL_MULAI else None
            ),
            "hari_kerja": self.HARI_KERJA,
            "fungsional": self.FUNGSIONAL,
            "update_by": self.UPDATE_BY,
            "update_date": (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE else None
            ),
            "dokreff": self.DOKREFF,
            "status_peg": self.STATUS_PEG,
            "id_unit_kerja": self.ID_UNIT_KERJA,
            "shift": self.SHIFT,
        }
