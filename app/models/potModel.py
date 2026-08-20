# app/models/potModel.py

from app import db


class MfPot(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy MF_POT.

    Mapping mengikuti database HRIS legacy
    tanpa mengubah struktur database.

    Legacy columns:
        IDPot
        Kategori
        Tingkat
        PersenPot
        TglMulai
        RangeAwal
        RangeAkhir
        NamaPot
        UpdateBy
        UpdateDate
        IsPendukung
        Tindakan
        DurasiPot
        SatuanDurasi

    Primary Key:
        IDPot

    Compatibility aliases:
        POTONGAN_ID -> IDPot
        KATEGORI    -> Kategori
        TINGKAT     -> Tingkat
        PERSEN_POT  -> PersenPot
        TGL_MULAI   -> TglMulai
        RANGE_AWAL  -> RangeAwal
        RANGE_AKHIR -> RangeAkhir
        NAMA_POT    -> NamaPot
        UPDATE_BY   -> UpdateBy
        UPDATE_DATE -> UpdateDate
        IS_PENDUKUNG -> IsPendukung
        TINDAKAN    -> Tindakan
        DURASI_POT  -> DurasiPot
        SATUAN_DURASI -> SatuanDurasi
    """

    __tablename__ = 'MF_POT'

    # ============================================================
    # LEGACY DATABASE COLUMNS
    # ============================================================

    POTONGAN_ID = db.Column(
        'IDPot',
        db.Integer,
        primary_key=True,
        nullable=False,
    )

    KATEGORI = db.Column(
        'Kategori',
        db.String(50),
        nullable=True,
    )

    TINGKAT = db.Column(
        'Tingkat',
        db.String(50),
        nullable=True,
    )

    PERSEN_POT = db.Column(
        'PersenPot',
        db.Float,
        nullable=True,
    )

    TGL_MULAI = db.Column(
        'TglMulai',
        db.DateTime,
        nullable=True,
    )

    RANGE_AWAL = db.Column(
        'RangeAwal',
        db.Float,
        nullable=True,
    )

    RANGE_AKHIR = db.Column(
        'RangeAkhir',
        db.Float,
        nullable=True,
    )

    NAMA_POT = db.Column(
        'NamaPot',
        db.String(50),
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

    IS_PENDUKUNG = db.Column(
        'IsPendukung',
        db.String(2),
        nullable=True,
    )

    TINDAKAN = db.Column(
        'Tindakan',
        db.String(250),
        nullable=True,
    )

    DURASI_POT = db.Column(
        'DurasiPot',
        db.Float,
        nullable=True,
    )

    SATUAN_DURASI = db.Column(
        'SatuanDurasi',
        db.String(10),
        nullable=True,
    )

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return f'<MfPot {self.POTONGAN_ID} - {self.NAMA_POT}>'

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        return {
            'potongan_id': self.POTONGAN_ID,
            'kategori': self.KATEGORI,
            'tingkat': self.TINGKAT,
            'persen_pot': self.PERSEN_POT,
            'tgl_mulai': (
                self.TGL_MULAI.isoformat()
                if self.TGL_MULAI
                else None
            ),
            'range_awal': self.RANGE_AWAL,
            'range_akhir': self.RANGE_AKHIR,
            'nama_pot': self.NAMA_POT,
            'update_by': self.UPDATE_BY,
            'update_date': (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE
                else None
            ),
            'is_pendukung': self.IS_PENDUKUNG,
            'tindakan': self.TINDAKAN,
            'durasi_pot': self.DURASI_POT,
            'satuan_durasi': self.SATUAN_DURASI,
        }
