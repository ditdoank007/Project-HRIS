from datetime import datetime

from app import db


class HrisDocument(db.Model):
    """Metadata dokumen HRIS; file fisik disimpan di central HRIS-DATA."""

    __tablename__ = "HRIS_DOCUMENT"

    DOCUMENT_ID = db.Column("DOCUMENT_ID", db.BigInteger, primary_key=True, autoincrement=True)
    DOCUMENT_TYPE = db.Column("DOCUMENT_TYPE", db.String(50), nullable=False)
    ENTITY_TYPE = db.Column("ENTITY_TYPE", db.String(50), nullable=False)
    ENTITY_ID = db.Column("ENTITY_ID", db.String(100), nullable=False)
    ORIGINAL_FILENAME = db.Column("ORIGINAL_FILENAME", db.String(255), nullable=False)
    STORAGE_PATH = db.Column("STORAGE_PATH", db.String(500), nullable=False)
    MIME_TYPE = db.Column("MIME_TYPE", db.String(100), nullable=False)
    FILE_SIZE = db.Column("FILE_SIZE", db.BigInteger, nullable=False)
    SHA256 = db.Column("SHA256", db.String(64), nullable=False)
    CREATED_BY = db.Column("CREATED_BY", db.String(50), nullable=False)
    CREATED_DATE = db.Column("CREATED_DATE", db.DateTime, nullable=False, default=datetime.utcnow)
    UPDATE_BY = db.Column("UPDATE_BY", db.String(50))
    UPDATE_DATE = db.Column("UPDATE_DATE", db.DateTime)

    __table_args__ = (
        db.UniqueConstraint(
            "DOCUMENT_TYPE",
            "ENTITY_TYPE",
            "ENTITY_ID",
            name="UQ_HRIS_DOCUMENT_ENTITY",
        ),
        db.Index("IDX_HRIS_DOCUMENT_ENTITY", "ENTITY_TYPE", "ENTITY_ID"),
        db.Index("IDX_HRIS_DOCUMENT_TYPE", "DOCUMENT_TYPE"),
    )

    def to_dict(self):
        return {
            "document_id": self.DOCUMENT_ID,
            "document_type": self.DOCUMENT_TYPE,
            "entity_type": self.ENTITY_TYPE,
            "entity_id": self.ENTITY_ID,
            "original_filename": self.ORIGINAL_FILENAME,
            "storage_path": self.STORAGE_PATH,
            "mime_type": self.MIME_TYPE,
            "file_size": self.FILE_SIZE,
            "sha256": self.SHA256,
            "created_by": self.CREATED_BY,
            "created_date": self.CREATED_DATE.isoformat() if self.CREATED_DATE else None,
            "update_by": self.UPDATE_BY,
            "update_date": self.UPDATE_DATE.isoformat() if self.UPDATE_DATE else None,
        }
