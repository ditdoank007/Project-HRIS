"""
HRIS Reborn — Global Operational Population Rule.

Single Source of Truth untuk menentukan siapa yang termasuk
populasi operasional HRIS.

RULE:
    Pegawai aktif
        = PEGAWAI.isKeluar IN ('N', '0')

    Unit kerja aktif
        = MF_UNIT_KERJA.isUse IN ('Y', '1')

    Pegawai Operasional
        = Pegawai aktif
        AND Unit Kerja aktif

CATATAN:
- Data historis tetap disimpan di database.
- Rule ini dipakai untuk modul operasional: pencarian, daftar,
  autocomplete, laporan dan perhitungan.
- Master File tetap boleh membaca data nonaktif untuk kebutuhan
  administrasi/mastering.
"""

from app.models.pegawaiModel import Pegawai
from app.models.unitKerjaModel import MfUnitKerja


# Nilai legacy HRIS 2013 dan nilai standar HRIS Reborn.
ACTIVE_EMPLOYEE_VALUES = ('N', '0')
INACTIVE_EMPLOYEE_VALUES = ('Y', '1')
ACTIVE_UNIT_VALUES = ('Y', '1')


def operational_pegawai_query():
    """
    Query utama Pegawai Operasional HRIS.

    Selalu gunakan fungsi ini untuk daftar/count pegawai operasional.
    """
    return (
        Pegawai.query
        .join(
            MfUnitKerja,
            Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID
        )
        .filter(
            Pegawai.IS_KELUAR.in_(ACTIVE_EMPLOYEE_VALUES),
            MfUnitKerja.IS_USE.in_(ACTIVE_UNIT_VALUES),
        )
    )


def join_operational_pegawai(query, finger_column):
    """
    Menambahkan scope Pegawai Operasional ke query transaksi.

    Contoh:
        query = join_operational_pegawai(
            DinasLuar.query,
            DinasLuar.FINGER_ID
        )

    Hasil:
        transaksi hanya terkait pegawai aktif pada unit aktif.
    """
    return (
        query
        .join(
            Pegawai,
            Pegawai.FINGER_ID == finger_column
        )
        .join(
            MfUnitKerja,
            Pegawai.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID
        )
        .filter(
            Pegawai.IS_KELUAR.in_(ACTIVE_EMPLOYEE_VALUES),
            MfUnitKerja.IS_USE.in_(ACTIVE_UNIT_VALUES),
        )
    )


def is_operational_pegawai(pegawai):
    """
    Mengecek satu object Pegawai terhadap rule operasional global.
    """
    if pegawai is None:
        return False

    if str(pegawai.IS_KELUAR or '').strip().upper() not in ACTIVE_EMPLOYEE_VALUES:
        return False

    if not pegawai.UNIT_KERJA_ID:
        return False

    return (
        MfUnitKerja.query
        .filter(
            MfUnitKerja.UNIT_KERJA_ID == pegawai.UNIT_KERJA_ID,
            MfUnitKerja.IS_USE.in_(ACTIVE_UNIT_VALUES),
        )
        .first()
        is not None
    )


def is_operational_nip(nip):
    """
    Mengecek NIP terhadap populasi operasional HRIS.
    """
    if not nip:
        return False

    return (
        operational_pegawai_query()
        .filter(Pegawai.NIP == str(nip).strip())
        .first()
        is not None
    )


def get_operational_pegawai_nips():
    """
    Mengambil seluruh NIP pegawai operasional.
    """
    return [
        str(row.NIP)
        for row in operational_pegawai_query()
        .with_entities(Pegawai.NIP)
        .all()
        if row.NIP is not None
    ]


def resolve_operational_employee_name(nip):
    """
    Mengembalikan nama pegawai hanya jika pegawai masih operasional.

    Dipakai untuk field audit seperti UPDATE_BY agar pegawai dari
    unit nonaktif tidak ikut ditampilkan sebagai identitas operasional.
    """
    if not nip:
        return None

    row = (
        operational_pegawai_query()
        .filter(Pegawai.NIP == str(nip).strip())
        .with_entities(Pegawai.NAMA)
        .first()
    )

    return row[0] if row and row[0] else None
