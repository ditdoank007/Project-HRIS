# app/models/bukuTamuModel.py
from app import db


class BukuTamu(db.Model):
    __tablename__ = "BUKU_TAMU"

    ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    JUDUL = db.Column(db.String(150), nullable=False)
    ID_UNIT_KERJA = db.Column(db.String(50), nullable=False)
    UNIT_KERJA_NAME = db.Column(db.String(100), nullable=False)
    QR_TOKEN = db.Column(db.String(80), nullable=False, unique=True, index=True)
    QR_ACTIVE = db.Column(db.String(1), nullable=False, default="Y")
    CREATED_BY = db.Column(db.String(50))
    CREATED_DATE = db.Column(db.DateTime, nullable=False)
    UPDATE_BY = db.Column(db.String(50))
    UPDATE_DATE = db.Column(db.DateTime)


class BukuTamuEntry(db.Model):
    __tablename__ = "BUKU_TAMU_ENTRY"

    ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    BUKU_TAMU_ID = db.Column(db.BigInteger, nullable=False, index=True)
    SCANNED_DATE = db.Column(db.DateTime, nullable=False, index=True)
    NAMA_LENGKAP = db.Column(db.String(150), nullable=False)
    INSTANSI = db.Column(db.String(150), nullable=False)
    NO_HP = db.Column(db.String(50), nullable=False)
    KEPERLUAN = db.Column(db.String(255), nullable=False)
    KEPERLUAN_DETAIL = db.Column(db.String(255))
    KETERANGAN = db.Column(db.String(255))
    PEGAWAI_NIP = db.Column(db.String(30))
    PEGAWAI_NAMA = db.Column(db.String(150))
    TANDA_TANGAN_PATH = db.Column(db.String(500))
    CREATED_IP = db.Column(db.String(64))
    USER_AGENT = db.Column(db.String(500))


class JenisKeperluan(db.Model):
    __tablename__ = "MF_JENIS_KEPERLUAN"

    ID = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    NAMA_KEPERLUAN = db.Column(db.String(100), nullable=False, unique=True)
    IS_AKTIF = db.Column(db.String(1), nullable=False, default="Y")
    URUT = db.Column(db.Integer, nullable=False, default=0)
    CREATED_BY = db.Column(db.String(50))
    CREATED_DATE = db.Column(db.DateTime, nullable=False)
    UPDATE_BY = db.Column(db.String(50))
    UPDATE_DATE = db.Column(db.DateTime)
