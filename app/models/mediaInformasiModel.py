# app/models/mediaInformasiModel.py
from app import db


class MediaInformasi(db.Model):
    """
    Model untuk tabel MEDIA_INFORMASI.
    Menyimpan data media informasi (pengumuman, banner, berita internal).

    Primary Key : MED_INFOR_ID
    """
    __tablename__ = 'MEDIA_INFORMASI'

    MED_INFOR_ID = db.Column('ID', db.BigInteger, primary_key=True, nullable=False)

    # Metadata
    UPDATE_DATE = db.Column('UpdateDate', db.DateTime)
    UPDATE_BY = db.Column('UpdateBy', db.String(50))

    # Kode transaksi
    TRX = db.Column('trx', db.String(50))

    # Konten
    NAMA_FILE = db.Column('NamaFile', db.String(100))
    DESKRIPSI = db.Column('Diskripsi', db.String(250))

    # Periode publikasi
    PUBLISH_DATE_START = db.Column('PublishDateStart', db.Date)
    PUBLISH_DATE_END = db.Column('PublishDateEnd', db.Date)

    # Status aktif
    IS_AKTIF = db.Column('IsAktif', db.String(5))

    # Penanggung jawab
    PIC = db.Column('PIC', db.String(150))

    # Alamat / URL terkait
    ALAMAT = db.Column('Alamat', db.String(250))

    def __repr__(self):
        return f'<MediaInformasi {self.MED_INFOR_ID}>'

    def to_dict(self):
        return {
            'med_infor_id': self.MED_INFOR_ID,
            'update_date': self.UPDATE_DATE.isoformat() if self.UPDATE_DATE else None,
            'update_by': self.UPDATE_BY,
            'trx': self.TRX,
            'nama_file': self.NAMA_FILE,
            'deskripsi': self.DESKRIPSI,
            'publish_date_start': self.PUBLISH_DATE_START.isoformat() if self.PUBLISH_DATE_START else None,
            'publish_date_end': self.PUBLISH_DATE_END.isoformat() if self.PUBLISH_DATE_END else None,
            'is_aktif': self.IS_AKTIF,
            'pic': self.PIC,
            'alamat': self.ALAMAT
        }
