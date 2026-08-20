# app/models/absensiTempModel.py

from sqlalchemy.orm import synonym

from app import db


class AbsensiTemp(db.Model):
    """
    Model SQLAlchemy untuk tabel legacy ABSENSI_TEMP.

    Mapping mengikuti database HRIS legacy tanpa mengubah
    struktur database.

    Database legacy tidak mendefinisikan PRIMARY KEY.

    ORM identity:
        FingerID + TglKerja

    Struktur ABSENSI_TEMP identik dengan ABSENSI_BACKUP.
    Tabel saat ini kosong, sehingga composite identity digunakan
    untuk memenuhi kebutuhan SQLAlchemy ORM.

    Legacy columns:
        FingerID
        TglKerja
        TglJamIn
        TglJamOut
        KetIn
        TransaksiIn
        UpdateInBy
        UpdateInDate
        KetOut
        TransaksiOut
        UpdateOutBy
        UpdateOutDate
        TingkatTLM
        TotalTLM
        TotalPSW
        TingkatPSW
        IsInValid
        isOutValid
        AwalTLM
        PersenPotTLM
        PersenPotPSW
        TglJamBakuIn
        TglJamBakuOut
        TransaksiIDFrom
        PendukungIN
        PendukungOut
        HistoryTransaksiIn
        HistoryTransaksiOut
    """

    __tablename__ = 'ABSENSI_TEMP'

    # ============================================================
    # ORM COMPOSITE IDENTITY
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
    )

    TGL_JAM_OUT = db.Column(
        'TglJamOut',
        db.DateTime,
    )

    # ============================================================
    # TRANSAKSI IN
    # ============================================================

    KET_IN = db.Column(
        'KetIn',
        db.String(450),
    )

    TRANSAKSI_IN = db.Column(
        'TransaksiIn',
        db.String(50),
    )

    UPDATE_IN_BY = db.Column(
        'UpdateInBy',
        db.String(50),
    )

    UPDATE_IN_DATE = db.Column(
        'UpdateInDate',
        db.DateTime,
    )

    PENDUKUNG_IN = db.Column(
        'PendukungIN',
        db.String(50),
    )

    HISTORY_TRANSAKSI_IN = db.Column(
        'HistoryTransaksiIn',
        db.String(450),
    )

    # ============================================================
    # TRANSAKSI OUT
    # ============================================================

    KET_OUT = db.Column(
        'KetOut',
        db.String(450),
    )

    TRANSAKSI_OUT = db.Column(
        'TransaksiOut',
        db.String(50),
    )

    UPDATE_OUT_BY = db.Column(
        'UpdateOutBy',
        db.String(50),
    )

    UPDATE_OUT_DATE = db.Column(
        'UpdateOutDate',
        db.DateTime,
    )

    PENDUKUNG_OUT = db.Column(
        'PendukungOut',
        db.String(50),
    )

    HISTORY_TRANSAKSI_OUT = db.Column(
        'HistoryTransaksiOut',
        db.String(450),
    )

    # ============================================================
    # KETERLAMBATAN / PULANG CEPAT
    # ============================================================

    TINGKAT_TLM = db.Column(
        'TingkatTLM',
        db.String(50),
    )

    TOTAL_TLM = db.Column(
        'TotalTLM',
        db.Float,
    )

    TOTAL_PSW = db.Column(
        'TotalPSW',
        db.Float,
    )

    TINGKAT_PSW = db.Column(
        'TingkatPSW',
        db.String(50),
    )

    AWAL_TLM = db.Column(
        'AwalTLM',
        db.Float,
    )

    PERSEN_POT_TLM = db.Column(
        'PersenPotTLM',
        db.Float,
    )

    PERSEN_POT_PSW = db.Column(
        'PersenPotPSW',
        db.Float,
    )

    # ============================================================
    # VALIDASI
    # ============================================================

    IS_INVALID = db.Column(
        'IsInValid',
        db.String(1),
    )

    IS_OUTVALID = db.Column(
        'isOutValid',
        db.String(1),
    )

    # ============================================================
    # JAM BAKU
    # ============================================================

    TGL_JAM_BAKU_IN = db.Column(
        'TglJamBakuIn',
        db.DateTime,
    )

    TGL_JAM_BAKU_OUT = db.Column(
        'TglJamBakuOut',
        db.DateTime,
    )

    # ============================================================
    # REFERENSI TRANSAKSI
    # ============================================================

    TRANSAKSI_ID_FROM = db.Column(
        'TransaksiIDFrom',
        db.String(50),
    )

    # Compatibility alias untuk typo source lama
    TRAKSAKSI_ID_FROM = synonym(
        'TRANSAKSI_ID_FROM'
    )

    # ============================================================
    # REPRESENTATION
    # ============================================================

    def __repr__(self):
        return (
            f'<AbsensiTemp '
            f'{self.FINGER_ID} - {self.TGL_KERJA}>'
        )

    def to_dict(self):
        return {
            'finger_id': self.FINGER_ID,
            'tgl_kerja': (
                self.TGL_KERJA.isoformat()
                if self.TGL_KERJA else None
            ),
            'tgl_jam_in': (
                self.TGL_JAM_IN.isoformat()
                if self.TGL_JAM_IN else None
            ),
            'tgl_jam_out': (
                self.TGL_JAM_OUT.isoformat()
                if self.TGL_JAM_OUT else None
            ),
            'ket_in': self.KET_IN,
            'transaksi_in': self.TRANSAKSI_IN,
            'update_in_by': self.UPDATE_IN_BY,
            'update_in_date': (
                self.UPDATE_IN_DATE.isoformat()
                if self.UPDATE_IN_DATE else None
            ),
            'ket_out': self.KET_OUT,
            'transaksi_out': self.TRANSAKSI_OUT,
            'update_out_by': self.UPDATE_OUT_BY,
            'update_out_date': (
                self.UPDATE_OUT_DATE.isoformat()
                if self.UPDATE_OUT_DATE else None
            ),
            'tingkat_tlm': self.TINGKAT_TLM,
            'total_tlm': self.TOTAL_TLM,
            'total_psw': self.TOTAL_PSW,
            'tingkat_psw': self.TINGKAT_PSW,
            'is_invalid': self.IS_INVALID,
            'is_outvalid': self.IS_OUTVALID,
            'awal_tlm': self.AWAL_TLM,
            'persen_pot_tlm': self.PERSEN_POT_TLM,
            'persen_pot_psw': self.PERSEN_POT_PSW,
            'tgl_jam_baku_in': (
                self.TGL_JAM_BAKU_IN.isoformat()
                if self.TGL_JAM_BAKU_IN else None
            ),
            'tgl_jam_baku_out': (
                self.TGL_JAM_BAKU_OUT.isoformat()
                if self.TGL_JAM_BAKU_OUT else None
            ),
            'transaksi_id_from': self.TRANSAKSI_ID_FROM,
            'pendukung_in': self.PENDUKUNG_IN,
            'pendukung_out': self.PENDUKUNG_OUT,
            'history_transaksi_in': self.HISTORY_TRANSAKSI_IN,
            'history_transaksi_out': self.HISTORY_TRANSAKSI_OUT,
        }
