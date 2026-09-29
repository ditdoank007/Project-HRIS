from datetime import datetime

from app import db


class KesamaptaanDokumentasi(db.Model):
    __tablename__ = "KESAMAPTAAN_DOKUMENTASI"

    DOKUMENTASI_ID = db.Column("DOKUMENTASI_ID", db.BigInteger, primary_key=True, autoincrement=True)
    KEGIATAN_ID = db.Column("KEGIATAN_ID", db.BigInteger, nullable=False)
    ORIGINAL_FILENAME = db.Column("ORIGINAL_FILENAME", db.String(255), nullable=False)
    STORAGE_PATH = db.Column("STORAGE_PATH", db.String(500), nullable=False)
    MIME_TYPE = db.Column("MIME_TYPE", db.String(100), nullable=False)
    FILE_SIZE = db.Column("FILE_SIZE", db.BigInteger, nullable=False)
    SHA256 = db.Column("SHA256", db.String(64), nullable=False)
    SORT_ORDER = db.Column("SORT_ORDER", db.Integer, nullable=False, default=1)
    CREATED_BY = db.Column("CREATED_BY", db.String(50), nullable=False)
    CREATED_DATE = db.Column("CREATED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
