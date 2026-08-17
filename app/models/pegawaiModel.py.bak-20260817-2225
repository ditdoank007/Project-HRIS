# app/models/pegawaiModel.py
from app import db


class Pegawai(db.Model):
    """
    Model untuk tabel PEGAWAI.
    Merepresentasikan data induk pegawai BASARNAS Surabaya.

    Primary Key : NIP (Nomor Induk Pegawai)
    Foreign Key : ABSENSI_ID, ESELON, TUNJANGAN_ID, CLASS_ID,
                  UNIT_KERJA_ID, JABATAN_ID, GOL_ID
    """
    __tablename__ = 'PEGAWAI'

    # Primary Key
    NIP = db.Column(db.String(50), primary_key=True)

    # Foreign Key (kolom "penunjuk" ke tabel lain)
    # NOT NULL semua sesuai DDL asli
    ABSENSI_ID = db.Column(db.Integer, nullable=False)
    ESELON = db.Column(db.String(50), nullable=False)
    TUNJANGAN_ID = db.Column(db.Integer, nullable=False)
    CLASS_ID = db.Column(db.Integer, nullable=False)
    UNIT_KERJA_ID = db.Column(db.Integer, nullable=False)
    JABATAN_ID = db.Column(db.Integer, nullable=False)
    GOL_ID = db.Column(db.Integer, nullable=False)

    # Data identitas & kontak
    NIP_MANAGER = db.Column(db.String(50), nullable=True)
    NAMA = db.Column(db.String(70), nullable=False)
    NO_TELP = db.Column(db.String(50), nullable=False)
    PANGKAT = db.Column(db.String(50), nullable=True)
    JABATAN = db.Column(db.String(50), nullable=True)  # label teks jabatan (beda dgn JABATAN_ID)
    MAIL = db.Column(db.String(100), nullable=True)

    # Kredensial login
    PASS = db.Column(db.String(50), nullable=False)

    # Data pribadi
    ALAMAT = db.Column(db.String(50), nullable=True)
    JENIS_KEL = db.Column(db.String(15), nullable=True)
    TGL_LAHIR = db.Column(db.DateTime, nullable=True)
    KELURAHAN = db.Column(db.String(50), nullable=True)
    KECAMATAN = db.Column(db.String(50), nullable=True)
    KOTA = db.Column(db.String(50), nullable=True)
    TEMPAT_LAHIR = db.Column(db.String(100), nullable=True)
    AGAMA = db.Column(db.String(100), nullable=True)
    STATUS_PERKAWINAN = db.Column(db.SmallInteger, nullable=True)
    NO_KTP = db.Column(db.String(50), nullable=True)
    NO_NPWP = db.Column(db.String(50), nullable=True)
    HOBI = db.Column(db.String(150), nullable=True)
    IS_VIP = db.Column(db.SmallInteger, nullable=True)

    # Riwayat kepegawaian
    TMT_PANGKAT = db.Column(db.DateTime, nullable=True)
    IS_KELUAR = db.Column(db.SmallInteger, nullable=True)
    TGL_KELUAR = db.Column(db.DateTime, nullable=True)
    ALASAN_KELUAR = db.Column(db.String(250), nullable=True)
    TGL_MASUK = db.Column(db.DateTime, nullable=True)
    TMT_PNS = db.Column(db.Date, nullable=True)
    TMT_CPNS = db.Column(db.Date, nullable=True)
    GOL_RECRUIT = db.Column(db.String(10), nullable=True)
    STATUS_PEG = db.Column(db.SmallInteger, nullable=True)
    TMT_CLASS = db.Column(db.Date, nullable=True)
    TMT_JABATAN = db.Column(db.Date, nullable=True)

    # Metadata audit
    UPDATE_IN_BY = db.Column(db.String(50), nullable=True)
    UPDATE_DATE = db.Column(db.DateTime, nullable=True)

    # Representasi objek (memudahkan debugging di console/log)
    def __repr__(self):
        return f'<Pegawai {self.NIP} - {self.NAMA}>'

    # Helper: ubah objek jadi dict (berguna untuk response JSON/API)
    # Password (PASS) sengaja TIDAK disertakan demi keamanan.
    def to_dict(self):
        return {
            'nip': self.NIP,
            'nama': self.NAMA,
            'no_telp': self.NO_TELP,
            'mail': self.MAIL,
            'pangkat': self.PANGKAT,
            'jabatan': self.JABATAN,
            'jabatan_id': self.JABATAN_ID,
            'unit_kerja_id': self.UNIT_KERJA_ID,
            'gol_id': self.GOL_ID,
            'eselon': self.ESELON,
            'alamat': self.ALAMAT,
            'jenis_kel': self.JENIS_KEL,
            'kota': self.KOTA,
            'status_peg': self.STATUS_PEG,
            'is_keluar': self.IS_KELUAR,
        }