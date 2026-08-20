# app/models/pegawaiModel.py

from sqlalchemy.orm import synonym

from app import db


class Pegawai(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy PEGAWAI.

    Mapping mengikuti database HRIS hasil migrasi SQL Server 2013
    tanpa mengubah struktur tabel database.

    Primary Key legacy:
        NIP + Nama + FingerID

    Compatibility aliases:
        ABSENSI_ID   -> FingerID
        GOL_ID       -> Gol
        UNIT_KERJA_ID -> UnitKerja
        JABATAN_ID   -> JabatanID
        CLASS_ID     -> ClassID
    """

    __tablename__ = 'PEGAWAI'

    # ============================================================
    # PRIMARY KEY LEGACY
    # ============================================================

    NIP = db.Column(
        'NIP',
        db.String(50),
        primary_key=True,
        nullable=False,
    )

    NAMA = db.Column(
        'Nama',
        db.String(70),
        primary_key=True,
        nullable=False,
    )

    FINGER_ID = db.Column(
        'FingerID',
        db.String(10),
        primary_key=True,
        nullable=False,
    )

    # ============================================================
    # LEGACY MASTER / RELATION COLUMNS
    # ============================================================

    PANGKAT = db.Column(
        'Pangkat',
        db.String(50),
    )

    GOL = db.Column(
        'Gol',
        db.String(10),
    )

    JABATAN = db.Column(
        'Jabatan',
        db.String(50),
    )

    UNIT_KERJA = db.Column(
        'UnitKerja',
        db.String(50),
    )

    JABATAN_ID = db.Column(
        'JabatanID',
        db.Integer,
    )

    CLASS_ID = db.Column(
        'ClassID',
        db.Integer,
    )

    ESELON = db.Column(
        'eselon',
        db.String(50),
    )

    # ============================================================
    # LEGACY LOGIN / ACCESS
    # ============================================================

    PASS = db.Column(
        'Pass',
        db.String(50),
    )

    # ============================================================
    # PERSONAL DATA
    # ============================================================

    ALAMAT = db.Column(
        'Alamat',
        db.String(50),
    )

    JENIS_KEL = db.Column(
        'JenisKel',
        db.String(15),
    )

    TGL_LAHIR = db.Column(
        'TglLahir',
        db.DateTime,
    )

    KELURAHAN = db.Column(
        'Kelurahan',
        db.String(50),
    )

    KECAMATAN = db.Column(
        'Kecamatan',
        db.String(50),
    )

    KOTA = db.Column(
        'Kota',
        db.String(50),
    )

    TEMPAT_LAHIR = db.Column(
        'TempatLahir',
        db.String(100),
    )

    AGAMA = db.Column(
        'Agama',
        db.String(100),
    )

    STATUS_PERKAWINAN = db.Column(
        'StatusPerkawinan',
        db.String(2),
    )

    NO_KTP = db.Column(
        'NoKTP',
        db.String(50),
    )

    NO_NPWP = db.Column(
        'NoNPWP',
        db.String(50),
    )

    HOBI = db.Column(
        'Hobi',
        db.String(150),
    )

    IS_VIP = db.Column(
        'IsVIP',
        db.String(2),
    )

    NO_TELP = db.Column(
        'NoTelp',
        db.String(50),
    )

    MAIL = db.Column(
        'Mail',
        db.String(100),
    )

    # ============================================================
    # EMPLOYMENT HISTORY
    # ============================================================

    TMTPANGKAT = db.Column(
        'TMTPangkat',
        db.DateTime,
    )

    IS_KELUAR = db.Column(
        'isKeluar',
        db.String(5),
    )

    TGL_KELUAR = db.Column(
        'Tglkeluar',
        db.DateTime,
    )

    ALASAN_KELUAR = db.Column(
        'AlasanKeluar',
        db.String(250),
    )

    TGL_MASUK = db.Column(
        'TglMasuk',
        db.DateTime,
    )

    TMTPNS = db.Column(
        'TMTPNS',
        db.Date,
    )

    TMTCPNS = db.Column(
        'TMTCPNS',
        db.Date,
    )

    GOL_RECRUIT = db.Column(
        'GolRecruit',
        db.String(10),
    )

    STATUS_PEG = db.Column(
        'StatusPeg',
        db.Integer,
    )

    TMT_CLASS = db.Column(
        'TMTClass',
        db.Date,
    )

    TMT_JABATAN = db.Column(
        'TMTJabatan',
        db.Date,
    )

    # ============================================================
    # AUDIT / METADATA
    # ============================================================

    UPDATE_BY = db.Column(
        'UpdateBy',
        db.String(50),
    )

    UPDATE_DATE = db.Column(
        'UpdateDate',
        db.DateTime,
    )

    # ============================================================
    # COMPATIBILITY ALIASES
    #
    # Source code HRIS baru menggunakan nama-nama berikut.
    # Alias diarahkan ke kolom legacy yang sebenarnya.
    # ============================================================

    ABSENSI_ID = synonym('FINGER_ID')

    GOL_ID = synonym('GOL')

    UNIT_KERJA_ID = synonym('UNIT_KERJA')

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<Pegawai '
            f'{self.NIP} - '
            f'{self.NAMA} - '
            f'{self.FINGER_ID}>'
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        def format_date(value):
            if not value:
                return None

            if isinstance(value, str):
                if value.startswith('0000-00-00'):
                    return None

                try:
                    return value[:10]
                except Exception:
                    return None

            return value.strftime('%Y-%m-%d')

        return {
            'nip': self.NIP,
            'nama': self.NAMA,
            'finger_id': self.FINGER_ID,

            'unit_kerja_id': self.UNIT_KERJA_ID,
            'jabatan_id': self.JABATAN_ID,
            'gol_id': self.GOL_ID,
            'class_id': self.CLASS_ID,
            'eselon': self.ESELON,

            'pangkat': self.PANGKAT,
            'jabatan': self.JABATAN,

            'tgl_masuk': format_date(self.TGL_MASUK),
            'status_peg': self.STATUS_PEG,
            'is_keluar': self.IS_KELUAR,
            'tgl_keluar': format_date(self.TGL_KELUAR),
            'alasan_keluar': self.ALASAN_KELUAR,

            'tmt_class': format_date(self.TMT_CLASS),
            'tmt_pangkat': format_date(self.TMTPANGKAT),
            'tmt_jabatan': format_date(self.TMT_JABATAN),

            'tgl_lahir': format_date(self.TGL_LAHIR),
            'jenis_kel': self.JENIS_KEL,

            'no_telp': self.NO_TELP,
            'email': self.MAIL,

            'alamat': self.ALAMAT,
            'kelurahan': self.KELURAHAN,
            'kecamatan': self.KECAMATAN,
            'kota': self.KOTA,
            'tempat_lahir': self.TEMPAT_LAHIR,
            'agama': self.AGAMA,
            'status_perkawinan': self.STATUS_PERKAWINAN,

            'no_ktp': self.NO_KTP,
            'no_npwp': self.NO_NPWP,
            'hobi': self.HOBI,

            'gol_recruit': self.GOL_RECRUIT,
            'tmt_cpns': format_date(self.TMTCPNS),
            'tmt_pns': format_date(self.TMTPNS),

            'is_vip': self.IS_VIP,
            'update_by': self.UPDATE_BY,
            'update_date': (
                self.UPDATE_DATE.isoformat()
                if self.UPDATE_DATE
                else None
            ),
        }
