from app import db


class DinasLuar(db.Model):
    """
    Model tabel DINAS_LUAR HRIS Reborn.

    Migrasi langsung dari HRIS 2013.
    """

    __tablename__ = "DINAS_LUAR"


    TRANSAKSI_ID = db.Column(
        "TransaksiID",
        db.String(50),
        primary_key=True
    )


    FINGER_ID = db.Column(
        "FingerID",
        db.String(50)
    )


    TGL_AWAL_DINAS_LUAR = db.Column(
        "TglAwaldinasLuar",
        db.DateTime
    )


    TGL_AKHIR_DINAS_LUAR = db.Column(
        "TglAkhirDinasLuar",
        db.DateTime
    )


    KETERANGAN_DINAS_LUAR = db.Column(
        "KeteranganDinasLuar",
        db.String(450)
    )


    PENEMPATAN_DINAS_LUAR = db.Column(
        "PenempatanDinasLuar",
        db.String(350)
    )


    UPDATE_BY = db.Column(
        "UpdateBy",
        db.String(50)
    )


    UPDATE_DATE = db.Column(
        "UpdateDate",
        db.DateTime
    )


    TRANSAKSI = db.Column(
        "Transaksi",
        db.String(50)
    )


    PENDUKUNG = db.Column(
        "Pendukung",
        db.String(50)
    )


    NO_SURAT = db.Column(
        "Nosurat",
        db.String(250)
    )


    STATUS_UM = db.Column(
        "StatusUM",
        db.Integer
    )


    GUID_SPRIN = db.Column(
        "GUIDSprin",
        db.String(100)
    )


    JENIS = db.Column(
        "Jenis",
        db.String(10)
    )


    TGL_AWAL_SURAT = db.Column(
        "TglAwalSurat",
        db.Date
    )


    TGL_AKHIR_SURAT = db.Column(
        "TglAkhirSurat",
        db.Date
    )


    NAMA_FILE = db.Column(
        "NamaFile",
        db.String(100)
    )


    TGL_EMAIL = db.Column(
        "TglEmail",
        db.DateTime
    )


    TIPE = db.Column(
        "Tipe",
        db.Integer
    )


    def __repr__(self):
        return f"<DinasLuar {self.TRANSAKSI_ID}>"
