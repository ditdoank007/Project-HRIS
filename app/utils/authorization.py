# app/utils/authorization.py
"""
Authorization helper HRIS Reborn.

Sumber otorisasi:
    USER_ACCOUNT
    HAK_AKSES_FORM

Aturan:
    INIT_LEVEL = 0
        -> Administrator -> full access

    INIT_LEVEL > 0
        -> Operator -> cek HAK_AKSES_FORM

Database legacy tidak diubah.
"""

from flask import session

from app.models.userAccountModel import UserAccount
from app.models.hakAksesFormModel import HakAksesForm


def get_current_nip():
    """Mengambil NIP user yang sedang login."""
    return session.get('nip')


def get_current_user_account():
    """Mengambil UserAccount HRIS untuk user yang sedang login."""
    nip = get_current_nip()

    if not nip:
        return None

    return UserAccount.query.filter(
        UserAccount.NIP == nip,
        UserAccount.MODUL == 'HRIS'
    ).first()


def get_current_level():
    """Mengambil INIT_LEVEL user saat ini."""
    user_account = get_current_user_account()

    if not user_account:
        return None

    return user_account.INIT_LEVEL


def is_administrator():
    """True jika user adalah Administrator HRIS atau SYSADMIN bootstrap."""
    if session.get("sysadmin") is True:
        return True
    return get_current_level() == 0



def has_form_access(form_id):
    """
    Memeriksa apakah user mempunyai akses terhadap FormID.

    Administrator:
        selalu True.

    Operator:
        True jika HAK_AKSES_FORM mempunyai:
            MODUL = HRIS
            NIP = user login
            FORM_ID = form_id
            isAkses = Y
    """
    if not get_current_nip():
        return False

    level = get_current_level()

    if level == 0:
        return True

    if level is None:
        return False

    # ============================================================
    # Permission source
    #
    # Menu HRIS Reborn umumnya berada pada Modul='HRIS'.
    # Menu Siaga legacy berada pada Modul='eDoc' tetapi tetap
    # dikendalikan dari Account User HRIS.
    #
    # Database tidak diubah.
    # ============================================================
    allowed_modules = ['HRIS']

    # Form Siaga legacy yang masih tercatat sebagai eDoc.
    SIAGA_FORM_IDS = {
        'KehadiranPiket.aspx',
        'InJadwalSiaga.aspx',
        'ReJadwalSiaga.aspx',
        'Rekapsiaga.aspx',
        'TTUPiket.aspx',
        'MFTimSiaga.aspx',
        'MFTunjPiket.aspx',
        'MFKGR.aspx',
        'MFEmail.aspx',
        'DaftarLemburSiaga.aspx',
    }

    if form_id in SIAGA_FORM_IDS:
        allowed_modules.append('eDoc')

    row = HakAksesForm.query.filter(
        HakAksesForm.NIP == get_current_nip(),
        HakAksesForm.FORM_ID == form_id,
        HakAksesForm.MODUL.in_(allowed_modules),
        HakAksesForm.IS_AKSES == 'Y'
    ).first()

    return row is not None


def can_read(form_id):
    """
    Memeriksa hak baca.

    Administrator:
        True.

    Operator:
        membutuhkan isAkses=Y.
    """
    return has_form_access(form_id)


def can_modify(form_id):
    """
    Memeriksa hak ubah.

    Administrator:
        True.

    Operator:
        membutuhkan isAkses=Y dan TypeAkses yang mengizinkan
        perubahan.

    Untuk tahap awal, TypeAkses R/M diperlakukan:
        M = modify
    """
    if not get_current_nip():
        return False

    level = get_current_level()

    if level == 0:
        return True

    if level is None:
        return False

    # Form Siaga legacy tertentu masih berada pada MODUL='eDoc'.
    # Gunakan sumber modul yang sama dengan has_form_access()
    # agar permission read/modify tetap konsisten.
    allowed_modules = ['HRIS']

    SIAGA_FORM_IDS = {
        'KehadiranPiket.aspx',
        'InJadwalSiaga.aspx',
        'ReJadwalSiaga.aspx',
        'Rekapsiaga.aspx',
        'TTUPiket.aspx',
        'MFTimSiaga.aspx',
        'MFTunjPiket.aspx',
        'MFKGR.aspx',
        'MFEmail.aspx',
        'DaftarLemburSiaga.aspx',
    }

    if form_id in SIAGA_FORM_IDS:
        allowed_modules.append('eDoc')

    row = HakAksesForm.query.filter(
        HakAksesForm.NIP == get_current_nip(),
        HakAksesForm.FORM_ID == form_id,
        HakAksesForm.MODUL.in_(allowed_modules),
        HakAksesForm.IS_AKSES == 'Y'
    ).first()

    if not row:
        return False

    return (row.TYPE_AKSES or '').upper() == 'M'
