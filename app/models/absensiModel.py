# app/models/absensiModel.py

from sqlalchemy.orm import synonym

from app import db


class Absensi(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy ABSENSI.

    Mapping mengikuti database HRIS legacy hasil migrasi
    tanpa mengubah struktur database.

    Primary Key legacy:
        FingerID + TglKerja

    Catatan:
        ABSENSI merupakan tabel hasil olahan transaksi kehadiran.
        Relasi ke PEGAWAI dilakukan melalui FingerID pada layer
        query/service, karena database legacy tidak menyimpan NIP
        pada tabel ABSENSI.
    """

    __tablename__ = 'ABSENSI'

    # ============================================================
    # LEGACY PRIMARY KEY
    # ============================================================

    FINGER_ID = db.Column(
        'FingerID',
        db.String(50),
        primary_key=True,
        nullable=False,
    )

    TGL_KERJA = db.Column(
        'TglKerja',
        db.DateTime,
        primary_key=True,
        nullable=False,
    )

    # ============================================================
    # JAM AKTUAL
    # ============================================================

    TGL_JAM_IN = db.Column(
        'TglJamIn',
        db.DateTime,
        nullable=True,
    )

    TGL_JAM_OUT = db.Column(
        'TglJamOut',
        db.DateTime,
        nullable=True,
    )

    KET_IN = db.Column(
        'KetIn',
        db.String(850),
        nullable=True,
    )

    TRANSAKSI_IN = db.Column(
        'TransaksiIn',
        db.String(50),
        nullable=True,
    )

    UPDATE_IN_BY = db.Column(
        'UpdateInBy',
        db.String(50),
        nullable=True,
    )

    UPDATE_IN_DATE = db.Column(
        'UpdateInDate',
        db.DateTime,
        nullable=True,
    )

    KET_OUT = db.Column(
        'KetOut',
        db.String(850),
        nullable=True,
    )

    TRANSAKSI_OUT = db.Column(
        'TransaksiOut',
        db.String(50),
        nullable=True,
    )

    UPDATE_OUT_BY = db.Column(
        'UpdateOutBy',
        db.String(50),
        nullable=True,
    )

    UPDATE_OUT_DATE = db.Column(
        'UpdateOutDate',
        db.DateTime,
        nullable=True,
    )

    # ============================================================
    # KETERLAMBATAN / PULANG SEBELUM WAKTU
    # ============================================================

    TINGKAT_TLM = db.Column(
        'TingkatTLM',
        db.String(50),
        nullable=True,
    )

    TOTAL_TLM = db.Column(
        'TotalTLM',
        db.Float,
        nullable=True,
    )

    TOTAL_PSW = db.Column(
        'TotalPSW',
        db.Float,
        nullable=True,
    )

    TINGKAT_PSW = db.Column(
        'TingkatPSW',
        db.String(50),
        nullable=True,
    )

    IS_INVALID = db.Column(
        'IsInValid',
        db.String(1),
        nullable=True,
    )

    IS_OUTVALID = db.Column(
        'isOutValid',
        db.String(1),
        nullable=True,
    )

    AWAL_TLM = db.Column(
        'AwalTLM',
        db.Float,
        nullable=True,
    )

    PERSEN_POT_TLM = db.Column(
        'PersenPotTLM',
        db.Float,
        nullable=True,
    )

    PERSEN_POT_PSW = db.Column(
        'PersenPotPSW',
        db.Float,
        nullable=True,
    )

    # ============================================================
    # JAM BAKU
    # ============================================================

    TGL_JAM_BAKU_IN = db.Column(
        'TglJamBakuIn',
        db.DateTime,
        nullable=True,
    )

    TGL_JAM_BAKU_OUT = db.Column(
        'TglJamBakuOut',
        db.DateTime,
        nullable=True,
    )

    # ============================================================
    # REFERENSI TRANSAKSI
    # ============================================================

    TRANSAKSI_ID_FROM = db.Column(
        'TransaksiIDFrom',
        db.String(250),
        nullable=True,
    )

    # Compatibility alias untuk typo source lama
    TRAKSAKSI_ID_FROM = synonym('TRANSAKSI_ID_FROM')

    # ============================================================
    # DOKUMEN PENDUKUNG
    # ============================================================

    PENDUKUNG_IN = db.Column(
        'PendukungIN',
        db.String(50),
        nullable=True,
    )

    PENDUKUNG_OUT = db.Column(
        'PendukungOut',
        db.String(50),
        nullable=True,
    )

    # ============================================================
    # HISTORY TRANSAKSI
    # ============================================================

    HISTORY_TRANSAKSI_IN = db.Column(
        'HistoryTransaksiIn',
        db.String(450),
        nullable=True,
    )

    HISTORY_TRANSAKSI_OUT = db.Column(
        'HistoryTransaksiOut',
        db.String(450),
        nullable=True,
    )

    # ============================================================
    # STATUS
    # ============================================================

    STATUS_UM = db.Column(
        'StatusUM',
        db.Integer,
        nullable=True,
    )

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<Absensi {self.FINGER_ID} '
            f'- {self.TGL_KERJA}>'
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(self):
        def format_datetime(value):
            return value.isoformat() if value else None

        return {
            'finger_id': self.FINGER_ID,
            'tgl_kerja': format_datetime(self.TGL_KERJA),
            'tgl_jam_in': format_datetime(self.TGL_JAM_IN),
            'tgl_jam_out': format_datetime(self.TGL_JAM_OUT),
            'ket_in': self.KET_IN,
            'transaksi_in': self.TRANSAKSI_IN,
            'update_in_by': self.UPDATE_IN_BY,
            'update_in_date': format_datetime(self.UPDATE_IN_DATE),
            'ket_out': self.KET_OUT,
            'transaksi_out': self.TRANSAKSI_OUT,
            'update_out_by': self.UPDATE_OUT_BY,
            'update_out_date': format_datetime(self.UPDATE_OUT_DATE),
            'tingkat_tlm': self.TINGKAT_TLM,
            'total_tlm': self.TOTAL_TLM,
            'total_psw': self.TOTAL_PSW,
            'tingkat_psw': self.TINGKAT_PSW,
            'is_invalid': self.IS_INVALID,
            'is_outvalid': self.IS_OUTVALID,
            'awal_tlm': self.AWAL_TLM,
            'persen_pot_tlm': self.PERSEN_POT_TLM,
            'persen_pot_psw': self.PERSEN_POT_PSW,
            'tgl_jam_baku_in': format_datetime(self.TGL_JAM_BAKU_IN),
            'tgl_jam_baku_out': format_datetime(self.TGL_JAM_BAKU_OUT),
            'transaksi_id_from': self.TRANSAKSI_ID_FROM,
            'pendukung_in': self.PENDUKUNG_IN,
            'pendukung_out': self.PENDUKUNG_OUT,
            'history_transaksi_in': self.HISTORY_TRANSAKSI_IN,
            'history_transaksi_out': self.HISTORY_TRANSAKSI_OUT,
            'status_um': self.STATUS_UM,
        }
