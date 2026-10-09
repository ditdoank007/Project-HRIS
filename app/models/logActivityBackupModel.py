# app/models/logActivityBackupModel.py
from app import db


class LogActivityBackup(db.Model):
    """
    Mapping LOG_ACTIVITIY_BACKUP ke nama kolom fisik HRIS 2013.

    IDBackUp adalah identitas baris backup; GUIDBackUp menyimpan penanda
    transaksi seperti "Delete Rejadwal" dan bukan primary key.
    """
    __tablename__ = 'LOG_ACTIVITIY_BACKUP'

    GUID_LOG_BACKUP = db.Column('IDBackUp', db.Integer, primary_key=True, autoincrement=True)
    GUID_LOG = db.Column('GUIDLog', db.String(50))
    TRX = db.Column('trx', db.String(50))
    ACTIVITY = db.Column('Activity', db.String(50))
    STATUS_ID = db.Column('StatusID', db.Integer)
    ACTIVITY_DATE = db.Column('ActivityDate', db.Date)
    NOTE = db.Column('Note', db.String(150))
    TEMPAT = db.Column('Tempat', db.String(150))
    PERIHAL = db.Column('Perihal', db.String(150))
    UPDATE_BY = db.Column('Updateby', db.String(50))
    UPDATE_DATE = db.Column('UpdateDate', db.DateTime)
    GUID_TIM = db.Column('GUIDTim', db.String(50))
    NIP = db.Column('NIP', db.String(50))
    UNIT_KERJA_ID = db.Column('IDUnitKerja', db.String(50))
    FUNGSIONAL = db.Column('Fungsional', db.String(50))
    TGL_CLOSING = db.Column('TglClosing', db.Date)
    SHIFT_1 = db.Column('shift1', db.Integer)
    SHIFT_2 = db.Column('shift2', db.Integer)
    PENGGANTI = db.Column('Pengganti', db.Integer)
    STATUS_TRX = db.Column('StatusTrx', db.String(50))
    BACK_UPDATE = db.Column('BackUpdate', db.DateTime)
    GUID_BACKUP = db.Column('GUIDBackUp', db.String(50))
    KET_UPDATE = db.Column('KetUpdate', db.String(250))
    NIP_PENGGANTI = db.Column('NIPPengganti', db.String(50))
    BIAYA = db.Column('Biaya', db.Float)
    QTY = db.Column('Qty', db.Float)
    SATUAN_QTY = db.Column('SatuanQty', db.String(50))
    SHIFT = db.Column('Shift', db.String(5))
    TRANSAKSI_FORM = db.Column('TransacForm', db.String(50))
    TGL_JAM_IN = db.Column('TglJamIn', db.DateTime)
    TGL_JAM_OUT = db.Column('TglJamOut', db.DateTime)
    TGL_JAM_BAKU_IN = db.Column('TglJamBakuIn', db.DateTime)
    TGL_JAM_BAKU_OUT = db.Column('TglJamBakuOut', db.DateTime)

    def __repr__(self):
        return f'<LogActivityBackup {self.GUID_LOG_BACKUP}>'
