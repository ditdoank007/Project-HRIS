# controllers/dashboard_2DataSiagaController.py
from flask import render_template, request, jsonify, g, current_app
from datetime import datetime
import uuid
from app import db
from app.models.otorisasiModel import Otorisasi
from app.models.jabatanSiagaModel import MfJabatanSiaga
from app.models.pegawaiModel import Pegawai
from app.models.unitKerjaModel import MfUnitKerja
from app.models.logActivityModel import LogActivity
from app.models.shiftModel import MfShift
from app.models.statusModel import MfStatus
from app.models.orgzSiagaModel import MfOrgzSiaga
from app.models.logActivityBackupModel import LogActivityBackup
from app.models.dinasLuarModel import DinasLuar

def data_siaga_absensi_kehadiran():
    """Render halaman Absensi Kehadiran Piket Siaga."""
    unit_kerja_list = MfUnitKerja.query.order_by(MfUnitKerja.NAMA_UNIT_KERJA.asc()).all()
    shift_list = MfShift.query.filter(
        MfShift.NAMA_SHIFT != ''
    ).order_by(MfShift.SHIFT_ID.asc()).all()
    
    return render_template(
        'pages/dashboard_2/Data_Siaga_Absensi_Kehadiran.html',
        unit_kerja_list=unit_kerja_list,
        shift_list=shift_list
    )

def api_absensi_kehadiran_get():
    """
    API VIEW DATA Absensi Kehadiran Piket Siaga.

    Sumber:
        LOG_ACTIVITIY

    Aturan:
        Activity     = Piket Siaga
        ActivityDate = tanggal yang dipilih
        Shift        = shift yang dipilih

    Status:
        STATUS_ID = 3  -> Hadir
        STATUS_ID = -1 -> Tidak Hadir
        lainnya          -> Belum

    Catatan:
        Untuk halaman kehadiran kita sengaja menggunakan SQL
        terhadap kolom fisik LOG_ACTIVITIY agar tidak tergantung
        pada ketidaksesuaian model lama.
    """
    try:
        tgl = (
            request.args.get(
                'tgl',
                datetime.now().strftime('%Y-%m-%d')
            )
            or ''
        ).strip()

        unit_kerja_id = (
            request.args.get('unit_kerja_id', '')
            or ''
        ).strip()

        shift = (
            request.args.get('shift', '')
            or ''
        ).strip()

        if not tgl:
            return jsonify({
                'success': False,
                'error': 'Tanggal harus diisi',
                'data': []
            })

        sql = db.text("""
            SELECT
                l.GUIDLog,
                l.NIP,
                l.ActivityDate,
                l.Fungsional,
                l.Shift,
                l.StatusID,
                l.shift1,
                l.shift2,
                l.Pengganti,
                l.StatusTrx,
                l.UpdateBy,
                l.UpdateDate,
                l.IDUnitKerja,
                p.Nama AS NAMA,
                u.UnitKerjaName AS NAMA_UNIT_KERJA
            FROM LOG_ACTIVITIY l
            LEFT JOIN PEGAWAI p
                ON p.NIP = l.NIP
            LEFT JOIN MF_UNIT_KERJA u
                ON u.IDUnitKerja = l.IDUnitKerja
            WHERE l.Activity = 'Piket Siaga'
              AND l.ActivityDate = :tgl
        """)

        params = {
            'tgl': tgl
        }

        if unit_kerja_id:
            sql = db.text("""
                SELECT
                    l.GUIDLog,
                    l.NIP,
                    l.ActivityDate,
                    l.Fungsional,
                    l.Shift,
                    l.StatusID,
                    l.shift1,
                    l.shift2,
                    l.Pengganti,
                    l.StatusTrx,
                    l.UpdateBy,
                    l.UpdateDate,
                    l.IDUnitKerja,
                    p.Nama AS NAMA,
                    u.UnitKerjaName AS NAMA_UNIT_KERJA
                FROM LOG_ACTIVITIY l
                LEFT JOIN PEGAWAI p
                    ON p.NIP = l.NIP
                LEFT JOIN MF_UNIT_KERJA u
                    ON u.IDUnitKerja = l.IDUnitKerja
                WHERE l.Activity = 'Piket Siaga'
                  AND l.ActivityDate = :tgl
                  AND l.IDUnitKerja = :unit_kerja_id
            """)
            params['unit_kerja_id'] = int(unit_kerja_id)

        if shift:
            base = sql.text
            # handled below by rebuilding query with shift
            sql_string = str(sql)
            sql_string = sql_string.replace(
                "AND l.ActivityDate = :tgl",
                "AND l.ActivityDate = :tgl\n"
                "              AND l.Shift = :shift"
            )
            sql = db.text(sql_string)
            params['shift'] = shift

        rows = db.session.execute(
            sql,
            params
        ).mappings().all()

        data = []

        for i, row in enumerate(rows, 1):
            status_id = row['StatusID']

            if status_id == 3:
                status = 'Hadir'
            elif status_id == -1:
                status = 'Tidak Hadir'
            else:
                status = 'Belum'

            data.append({
                'no': i,
                'guid_log': row['GUIDLog'],
                'nip': row['NIP'],
                'nama': row['NAMA'] or '-',
                'activity_date': (
                    row['ActivityDate'].strftime('%d-%m-%Y')
                    if row['ActivityDate']
                    else ''
                ),
                'fungsional': row['Fungsional'] or '',
                'fungsional_ket': row['Fungsional'] or '',
                'unit_kerja': row['NAMA_UNIT_KERJA'] or '',
                'shift': row['Shift'] or '',
                'status_id': status_id,
                'status': status,
                'shift_1': row['shift1'] or 0,
                'shift_2': row['shift2'] or 0,
                'pengganti': row['Pengganti'] or 0,
                'status_trx': row['StatusTrx'] or '-',
                'update_by': row['UpdateBy'] or '',
                'update_date': (
                    row['UpdateDate'].strftime('%d/%m/%Y %H:%M')
                    if row['UpdateDate']
                    else ''
                ),
            })

        return jsonify({
            'success': True,
            'data': data,
            'total': len(data)
        })

    except Exception as e:
        db.session.rollback()

        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })


def api_absensi_kehadiran_update():
    """
    API SIMPAN KEHADIRAN PIKET SIAGA.

    Hadir Shift 1:
        StatusID = 3
        shift1   = 1
        shift2   = 0

    Hadir Shift 2:
        StatusID = 3
        shift1   = 0
        shift2   = 1

    Tidak hadir:
        StatusID = -1
        shift1   = 0
        shift2   = 0
    """
    try:
        data = request.get_json() or {}

        guid_log = (
            str(data.get('guid_log') or '')
            .strip()
        )

        nip = (
            str(data.get('nip') or '')
            .strip()
        )

        shift1 = bool(data.get('shift1'))
        shift2 = bool(data.get('shift2'))

        if not guid_log or not nip:
            return jsonify({
                'success': False,
                'error': 'GUID Log dan NIP wajib diisi'
            })

        # Tidak boleh dua shift sekaligus.
        if shift1 and shift2:
            return jsonify({
                'success': False,
                'error': 'Shift 1 dan Shift 2 tidak boleh aktif bersamaan'
            })

        status_id = 3 if (shift1 or shift2) else -1

        update_sql = db.text("""
            UPDATE LOG_ACTIVITIY
            SET
                StatusID = :status_id,
                shift1 = :shift1,
                shift2 = :shift2,
                TglClosing = ActivityDate,
                UpdateBy = :update_by,
                UpdateDate = :update_date
            WHERE GUIDLog = :guid_log
              AND NIP = :nip
              AND Activity = 'Piket Siaga'
        """)

        result = db.session.execute(
            update_sql,
            {
                'status_id': status_id,
                'shift1': 1 if shift1 else 0,
                'shift2': 1 if shift2 else 0,
                'update_by': 'admin',
                'update_date': datetime.now(),
                'guid_log': guid_log,
                'nip': nip,
            }
        )

        if result.rowcount == 0:
            db.session.rollback()

            return jsonify({
                'success': False,
                'error': 'Data piket siaga tidak ditemukan'
            })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                'Kehadiran Shift 1 berhasil disimpan'
                if shift1
                else
                'Kehadiran Shift 2 berhasil disimpan'
                if shift2
                else
                'Status Tidak Hadir berhasil disimpan'
            )
        })

    except Exception as e:
        db.session.rollback()

        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        })




# ============================================================
# HRIS REBORN - MASTER DROPDOWN BUAT JADWAL SIAGA
# ============================================================

def api_siaga_master_jabatan_aktif():
    """
    Mengambil Master Jabatan Siaga aktif.

    Single Source:
        MF_JABATAN_SIAGA

    Business Rule:
        IsAktif = Y
        ORDER BY NoUrut ASC
    """

    try:

        rows = (
            MfJabatanSiaga.query
            .filter(
                MfJabatanSiaga.IS_AKTIF == 'Y'
            )
            .order_by(
                MfJabatanSiaga.NO_URUT.asc()
            )
            .all()
        )

        return jsonify({
            'success': True,
            'data': [
                {
                    'id_jabatan_siaga':
                        row.ID_JABATAN_SIAGA,

                    'no_urut':
                        row.NO_URUT,

                    'nama_jabatan':
                        row.NAMA_JABATAN,

                    'keterangan':
                        row.KETERANGAN or ''
                }
                for row in rows
            ]
        })

    except Exception:

        current_app.logger.exception(
            'Gagal mengambil Master Jabatan Siaga aktif'
        )

        return jsonify({
            'success': False,
            'error': 'Gagal mengambil Master Jabatan Siaga.'
        }), 500


def api_siaga_master_unit_aktif():
    """
    Mengambil Master Unit Kerja aktif.

    Single Source:
        MF_UNIT_KERJA

    Business Rule:
        IS_USE = Y

    Unit nonaktif tidak boleh muncul pada
    dropdown Buat Jadwal Siaga.
    """

    try:

        rows = (
            MfUnitKerja.query
            .filter(
                MfUnitKerja.IS_USE == 'Y'
            )
            .order_by(
                MfUnitKerja.URUT_REPORT.asc()
            )
            .all()
        )

        return jsonify({
            'success': True,
            'data': [
                {
                    'id_unit_kerja':
                        row.UNIT_KERJA_ID,

                    'nama_unit_kerja':
                        row.NAMA_UNIT_KERJA
                }
                for row in rows
            ]
        })

    except Exception:

        current_app.logger.exception(
            'Gagal mengambil Master Unit Kerja aktif'
        )

        return jsonify({
            'success': False,
            'error': 'Gagal mengambil Master Unit Kerja.'
        }), 500



def api_pembuatan_jadwal_siaga_save():
    """
    API SAVE PEMBUATAN JADWAL PIKET SIAGA.

    Business Rule:

        1. Satu SAVE = satu roster.
        2. Urutan roster otomatis mengikuti roster terakhir
           pada bulan + tahun + unit + fungsional + shift.
        3. Satu roster boleh berisi lebih dari satu pegawai.
        4. Satu pegawai tidak boleh berada pada roster berbeda
           dalam periode yang sama untuk unit + fungsional + shift.
        5. Duplicate NIP dalam satu input ditolak.
        6. Shift 1 = Shift 2 membuat pasangan roster otomatis.
        7. Pasangan otomatis Shift 2 tidak dianggap duplicate.
        8. Pengganti bukan bagian dari master roster dan akan
           ditangani pada proses jadwal harian/rejadwal.
        9. Database legacy tidak diubah struktur.

    Identifier pegawai:
        NIP pada tabel PEGAWAI adalah identifier resmi HRIS.
        Untuk pegawai non-ASN/PPPK, nilai NIP mengikuti ID/FingerID
        yang tersimpan pada master PEGAWAI.
    """

    try:
        data = request.get_json(silent=True) or {}

        bulan = str(
            data.get('bulan') or ''
        ).strip().zfill(2)

        tahun = str(
            data.get('tahun') or ''
        ).strip()

        shift = str(
            data.get('shift') or ''
        ).strip()

        unit_id = str(
            data.get('unit_kerja_id') or ''
        ).strip()

        fungsional = str(
            data.get('fungsional') or ''
        ).strip()

        pegawai = data.get('pegawai') or []

        shift1_sama_shift2 = bool(
            data.get('shift1_sama_shift2')
        )

        # ============================================================
        # VALIDASI INPUT DASAR
        # ============================================================

        if bulan not in {
            '01', '02', '03', '04', '05', '06',
            '07', '08', '09', '10', '11', '12'
        }:
            return jsonify({
                'success': False,
                'error': 'Bulan tidak valid.'
            }), 400

        if (
            len(tahun) != 4
            or not tahun.isdigit()
        ):
            return jsonify({
                'success': False,
                'error': 'Tahun tidak valid.'
            }), 400

        if shift not in ('1', '2'):
            return jsonify({
                'success': False,
                'error': 'Shift harus 1 atau 2.'
            }), 400

        if not unit_id:
            return jsonify({
                'success': False,
                'error': 'Unit kerja wajib dipilih.'
            }), 400

        if not fungsional:
            return jsonify({
                'success': False,
                'error': 'Jabatan siaga wajib dipilih.'
            }), 400

        if not isinstance(pegawai, list):
            return jsonify({
                'success': False,
                'error': 'Daftar pegawai tidak valid.'
            }), 400

        # ============================================================
        # NORMALISASI NIP INPUT
        # ============================================================

        nip_list = []

        for item in pegawai:

            if isinstance(item, dict):
                nip = str(
                    item.get('nip') or ''
                ).strip()
            else:
                nip = str(
                    item or ''
                ).strip()

            if not nip:
                continue

            if nip in nip_list:
                return jsonify({
                    'success': False,
                    'error': (
                        'Pegawai duplicate dalam roster: '
                        + nip
                    )
                }), 400

            nip_list.append(nip)

        if not nip_list:
            return jsonify({
                'success': False,
                'error': 'Minimal satu pegawai harus dipilih.'
            }), 400

        # ============================================================
        # VALIDASI PEGAWAI
        # ============================================================

        placeholders = ','.join(
            f':nip_{i}'
            for i in range(len(nip_list))
        )

        params = {
            f'nip_{i}': nip
            for i, nip in enumerate(nip_list)
        }

        rows = db.session.execute(
            db.text(f"""
                SELECT
                    NIP,
                    Nama,
                    UnitKerja,
                    FingerID
                FROM PEGAWAI
                WHERE NIP IN ({placeholders})
            """),
            params,
        ).mappings().all()

        pegawai_map = {
            str(r['NIP']).strip(): r
            for r in rows
        }

        tidak_ditemukan = [
            nip
            for nip in nip_list
            if nip not in pegawai_map
        ]

        if tidak_ditemukan:
            return jsonify({
                'success': False,
                'error': (
                    'Pegawai tidak ditemukan: '
                    + ', '.join(tidak_ditemukan)
                )
            }), 400

        # ============================================================
        # VALIDASI UNIT
        # ============================================================

        unit = db.session.execute(
            db.text("""
                SELECT
                    IDUnitKerja,
                    UnitKerjaName
                FROM MF_UNIT_KERJA
                WHERE IDUnitKerja = :unit_id
                LIMIT 1
            """),
            {
                'unit_id': unit_id
            },
        ).mappings().first()

        if not unit:
            return jsonify({
                'success': False,
                'error': 'Unit kerja tidak ditemukan.'
            }), 400

        # ============================================================
        # CEK PEGAWAI SUDAH ADA DI ROSTER LAIN
        #
        # Khusus pasangan Shift 1 = Shift 2:
        #   Shift target dianggap bagian dari pasangan roster
        #   yang sedang dibuat.
        #
        # Jadi duplicate dicek terhadap roster yang sudah ada,
        # bukan terhadap roster pasangan yang baru akan dibuat.
        # ============================================================

        existing_rows = db.session.execute(
            db.text("""
                SELECT
                    a.NIP,
                    a.GUIDTim,
                    t.NoUrutTim,
                    t.NamaTim,
                    t.IDUnitKerja,
                    t.FungsionalTIM,
                    t.Shift
                FROM MF_TIM_SIAGA_ANGGOTA a
                INNER JOIN MF_TIM_SIAGA t
                    ON t.GUIDTim = a.GUIDTim
                WHERE a.NIP IN (
                    SELECT NIP
                    FROM MF_TIM_SIAGA_ANGGOTA
                    WHERE NIP IN ("""
                    + placeholders
                    + """)
                )
                  AND a.BulanPeriode = :bulan
                  AND a.TahunPeriode = :tahun
                  AND a.IsAktif = 'Y'
                  AND t.BulanPeriode = :bulan
                  AND t.TahunPeriode = :tahun
                  AND t.IsAktif = 'Y'
            """),
            {
                **params,
                'bulan': bulan,
                'tahun': tahun,
            },
        ).mappings().all()

        if existing_rows:

            duplicate_messages = []

            for row in existing_rows:

                duplicate_messages.append(
                    (
                        f"{row['NIP']} sudah berada di "
                        f"roster {row['NoUrutTim']} "
                        f"({row['FungsionalTIM']} / "
                        f"Shift {row['Shift']})"
                    )
                )

            return jsonify({
                'success': False,
                'error': (
                    'Pegawai sudah memiliki roster: '
                    + '; '.join(
                        duplicate_messages
                    )
                ),
                'duplicates': [
                    dict(row)
                    for row in existing_rows
                ]
            }), 409

        # ============================================================
        # TENTUKAN NOMOR URUT BERIKUTNYA
        #
        # Nomor urut adalah urutan roster dalam kombinasi:
        #   bulan + tahun + unit + fungsional + shift
        #
        # Operator dapat melihat informasi roster terakhir
        # yang tersimpan.
        # ============================================================

        last_roster = db.session.execute(
            db.text("""
                SELECT
                    NoUrutTim,
                    NamaTim,
                    IDUnitKerja,
                    FungsionalTIM,
                    Shift
                FROM MF_TIM_SIAGA
                WHERE BulanPeriode = :bulan
                  AND TahunPeriode = :tahun
                  AND IDUnitKerja = :unit_id
                  AND FungsionalTIM = :fungsional
                  AND Shift = :shift
                  AND IsAktif = 'Y'
                ORDER BY NoUrutTim DESC
                LIMIT 1
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
                'shift': shift,
            },
        ).mappings().first()

        if last_roster:
            no_urut = (
                int(last_roster['NoUrutTim'] or 0)
                + 1
            )
        else:
            no_urut = 1

        # ============================================================
        # INFORMASI DATA TERAKHIR UNTUK OPERATOR
        # ============================================================

        last_saved = db.session.execute(
            db.text("""
                SELECT
                    t.NoUrutTim,
                    t.NamaTim,
                    t.IDUnitKerja,
                    u.UnitKerjaName,
                    t.FungsionalTIM,
                    t.Shift,
                    t.BulanPeriode,
                    t.TahunPeriode
                FROM MF_TIM_SIAGA t
                LEFT JOIN MF_UNIT_KERJA u
                    ON u.IDUnitKerja = t.IDUnitKerja
                WHERE t.BulanPeriode = :bulan
                  AND t.TahunPeriode = :tahun
                  AND t.IsAktif = 'Y'
                ORDER BY
                    t.UpdateDate DESC,
                    t.NoUrutTim DESC
                LIMIT 1
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
            },
        ).mappings().first()

        # ============================================================
        # BUAT GUID
        # ============================================================

        import uuid

        guid_tim = str(
            uuid.uuid4()
        )

        nama_tim = (
            f"{fungsional} "
            f"{unit['UnitKerjaName']} "
            f"#{no_urut} "
            f"{bulan}/{tahun}"
        )[:50]

        now = datetime.now()

        update_by = (
            getattr(
                getattr(g, 'user', None),
                'NIP',
                None,
            )
            or 'HRIS'
        )

        # ============================================================
        # INSERT ROSTER
        # ============================================================

        db.session.execute(
            db.text("""
                INSERT INTO MF_TIM_SIAGA (
                    NoUrutTim,
                    GUIDTim,
                    NamaTim,
                    IDUnitKerja,
                    IsAktif,
                    UpdateBy,
                    UpdateDate,
                    BulanPeriode,
                    TahunPeriode,
                    FungsionalTIM,
                    Shift
                )
                VALUES (
                    :no_urut,
                    :guid_tim,
                    :nama_tim,
                    :unit_id,
                    'Y',
                    :update_by,
                    :update_date,
                    :bulan,
                    :tahun,
                    :fungsional,
                    :shift
                )
            """),
            {
                'no_urut': no_urut,
                'guid_tim': guid_tim,
                'nama_tim': nama_tim,
                'unit_id': unit_id,
                'update_by': update_by,
                'update_date': now,
                'bulan': bulan,
                'tahun': tahun,
                'fungsional': fungsional,
                'shift': shift,
            },
        )

        # ============================================================
        # INSERT ANGGOTA
        # ============================================================

        for nomor, nip in enumerate(
            nip_list,
            start=1
        ):

            db.session.execute(
                db.text("""
                    INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                        GUIDTim,
                        NIP,
                        Fungsional,
                        IsAktif,
                        IDUnitKerja,
                        Nourut,
                        UpdateDate,
                        UpdateBy,
                        BulanPeriode,
                        TahunPeriode,
                        Shift
                    )
                    VALUES (
                        :guid_tim,
                        :nip,
                        :fungsional,
                        'Y',
                        :unit_id,
                        :nomor,
                        :update_date,
                        :update_by,
                        :bulan,
                        :tahun,
                        :shift
                    )
                """),
                {
                    'guid_tim': guid_tim,
                    'nip': nip,
                    'fungsional': fungsional,
                    'unit_id': unit_id,
                    'nomor': nomor,
                    'update_date': now,
                    'update_by': update_by,
                    'bulan': bulan,
                    'tahun': tahun,
                    'shift': shift,
                },
            )

        # ============================================================
        # SHIFT 1 = SHIFT 2
        # ============================================================

        pasangan_guid = None

        if (
            shift == '1'
            and shift1_sama_shift2
        ):

            pasangan_guid = str(
                uuid.uuid4()
            )

            pasangan_nama_tim = (
                f"{fungsional} "
                f"{unit['UnitKerjaName']} "
                f"#{no_urut} "
                f"{bulan}/{tahun}"
            )[:50]

            db.session.execute(
                db.text("""
                    INSERT INTO MF_TIM_SIAGA (
                        NoUrutTim,
                        GUIDTim,
                        NamaTim,
                        IDUnitKerja,
                        IsAktif,
                        UpdateBy,
                        UpdateDate,
                        BulanPeriode,
                        TahunPeriode,
                        FungsionalTIM,
                        Shift
                    )
                    VALUES (
                        :no_urut,
                        :guid_tim,
                        :nama_tim,
                        :unit_id,
                        'Y',
                        :update_by,
                        :update_date,
                        :bulan,
                        :tahun,
                        :fungsional,
                        '2'
                    )
                """),
                {
                    'no_urut': no_urut,
                    'guid_tim': pasangan_guid,
                    'nama_tim': pasangan_nama_tim,
                    'unit_id': unit_id,
                    'update_by': update_by,
                    'update_date': now,
                    'bulan': bulan,
                    'tahun': tahun,
                    'fungsional': fungsional,
                },
            )

            for nomor, nip in enumerate(
                nip_list,
                start=1
            ):

                db.session.execute(
                    db.text("""
                        INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                            GUIDTim,
                            NIP,
                            Fungsional,
                            IsAktif,
                            IDUnitKerja,
                            Nourut,
                            UpdateDate,
                            UpdateBy,
                            BulanPeriode,
                            TahunPeriode,
                            Shift
                        )
                        VALUES (
                            :guid_tim,
                            :nip,
                            :fungsional,
                            'Y',
                            :unit_id,
                            :nomor,
                            :update_date,
                            :update_by,
                            :bulan,
                            :tahun,
                            '2'
                        )
                    """),
                    {
                        'guid_tim': pasangan_guid,
                        'nip': nip,
                        'fungsional': fungsional,
                        'unit_id': unit_id,
                        'nomor': nomor,
                        'update_date': now,
                        'update_by': update_by,
                        'bulan': bulan,
                        'tahun': tahun,
                    },
                )

        # ============================================================
        # COMMIT
        # ============================================================

        db.session.commit()

        # ============================================================
        # RESPONSE
        # ============================================================

        response = {
            'success': True,
            'message': (
                f"Roster #{no_urut} berhasil disimpan."
            ),
            'roster': {
                'guid_tim': guid_tim,
                'no_urut': no_urut,
                'bulan': bulan,
                'tahun': tahun,
                'shift': shift,
                'unit_kerja_id': unit_id,
                'unit_kerja': unit['UnitKerjaName'],
                'fungsional': fungsional,
                'jumlah_pegawai': len(nip_list),
                'pegawai': [
                    {
                        'nip': nip,
                        'nama': (
                            pegawai_map[nip]['Nama']
                            or ''
                        ),
                    }
                    for nip in nip_list
                ],
            },
            'shift2_created': bool(
                pasangan_guid
            ),
            'last_saved_before': (
                dict(last_saved)
                if last_saved
                else None
            ),
        }

        return jsonify(response), 200

    except Exception as exc:

        db.session.rollback()

        current_app.logger.exception(
            "Gagal menyimpan jadwal piket siaga"
        )

        return jsonify({
            'success': False,
            'error': (
                'Gagal menyimpan jadwal piket siaga: '
                + str(exc)
            )
        }), 500


def data_siaga_cetak_daftar_lembur_siaga():
    """Render halaman Data Siaga Cetak Daftar Lembur Siaga."""
    return render_template('pages/dashboard_2/Data_Siaga_Cetak_Daftar_Lembur_Siaga.html')

def data_siaga_cetak_rekap_siaga():
    """Render halaman Data Siaga Cetak Rekap Siaga."""
    return render_template('pages/dashboard_2/Data_Siaga_Cetak_Rekap_Siaga.html')

def data_siaga_cetak_uang_siaga():
    """Render halaman Data Siaga Cetak Uang Siaga."""
    return render_template('pages/dashboard_2/Data_Siaga_Cetak_Uang_Siaga.html')

def data_siaga_jadwal_ulang():
    """Render halaman Data Siaga Jadwal Ulang."""
    return render_template('pages/dashboard_2/Data_Siaga_Jadwal_Ulang.html')

def api_rejadwal_siaga_get_jadwal():
    """
    API: Get data jadwal piket siaga berdasarkan Unit, Tanggal, Shift
    """
    try:
        unit_kerja_id = request.args.get('unit_kerja_id', '')
        tgl = request.args.get('tgl', '')
        shift = request.args.get('shift', '')
        
        if not unit_kerja_id or not tgl or not shift:
            return jsonify({'success': False, 'error': 'Unit, Tanggal, dan Shift harus diisi'})
        
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        
        # Cari GUID_LOG
        guid_log_result = db.session.query(LogActivity.GUID_LOG).filter(
            LogActivity.ACTIVITY == 'Piket Siaga',
            db.func.date(LogActivity.ACTIVITY_DATE) == tgl_date.date(),
            LogActivity.UNIT_KERJA_ID == int(unit_kerja_id),
            LogActivity.SHIFT == shift
        ).first()
        
        if not guid_log_result:
            return jsonify({'success': False, 'error': 'Jadwal tidak ditemukan'})
        
        guid_log = guid_log_result[0]
        
        # Query jadwal
        try:
            jadwal_list = db.session.query(
                LogActivity, Pegawai, MfUnitKerja, MfOrgzSiaga, MfStatus
            ).join(
                Pegawai, LogActivity.NIP == Pegawai.NIP
            ).join(
                MfUnitKerja, LogActivity.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID
            ).join(
                MfOrgzSiaga, LogActivity.FUNGSIONAL == MfOrgzSiaga.FUNGSIONAL
            ).outerjoin(
                MfStatus, LogActivity.STATUS_ID == MfStatus.STATUS_ID
            ).filter(
                LogActivity.ACTIVITY == 'Piket Siaga',
                LogActivity.GUID_LOG == guid_log,
                db.func.date(LogActivity.ACTIVITY_DATE) == tgl_date.date(),
                LogActivity.UNIT_KERJA_ID == int(unit_kerja_id),
                LogActivity.SHIFT == shift
            ).order_by(MfOrgzSiaga.URUT_FUNGSIONAL).all()
        except Exception:
            jadwal_list = db.session.query(
                LogActivity, Pegawai, MfUnitKerja
            ).join(
                Pegawai, LogActivity.NIP == Pegawai.NIP
            ).join(
                MfUnitKerja, LogActivity.UNIT_KERJA_ID == MfUnitKerja.UNIT_KERJA_ID
            ).filter(
                LogActivity.ACTIVITY == 'Piket Siaga',
                LogActivity.GUID_LOG == guid_log,
                db.func.date(LogActivity.ACTIVITY_DATE) == tgl_date.date(),
                LogActivity.UNIT_KERJA_ID == int(unit_kerja_id),
                LogActivity.SHIFT == shift
            ).all()
        
        # ✅ Query rollback - gunakan NIP_PENGGANTI untuk join ke Pegawai
        # karena model LogActivityBackup tidak punya field NIP
        rollback_list = db.session.query(
            LogActivityBackup, Pegawai
        ).outerjoin(
            Pegawai, LogActivityBackup.NIP_PENGGANTI == Pegawai.NIP
        ).filter(
            LogActivityBackup.ACTIVITY == 'Piket Siaga',
            LogActivityBackup.TRANSAKSI_FORM == 'Delete Rejadwal',
            LogActivityBackup.GUID_LOG == guid_log,
            db.func.date(LogActivityBackup.ACTIVITY_DATE) == tgl_date.date(),
            LogActivityBackup.SHIFT == shift
        ).all()
        
        # Format jadwal
        jadwal_data = []
        for i, item in enumerate(jadwal_list, 1):
            if len(item) == 5:
                log, peg, unit, orgz, status = item
                status_text = status.STATUS if status else '-'
                bg_status = status.BG_STATUS if status else ''
            else:
                log, peg, unit = item
                orgz = None
                status_text = 'Hadir' if log.STATUS_ID == 3 else ('Pending' if log.STATUS_ID == 2 else '-')
                bg_status = ''
            
            jadwal_data.append({
                'no': i,
                'guid_log': log.GUID_LOG,
                'nip': log.NIP,
                'nama': peg.NAMA if peg else '-',
                'fungsional': log.FUNGSIONAL or '',
                'status_id': log.STATUS_ID,
                'status': status_text,
                'bg_status': bg_status,
                'unit_kerja': unit.NAMA_UNIT_KERJA if unit else '',
                'shift': log.SHIFT or '',
                'act_date': log.ACTIVITY_DATE.strftime('%Y.%m.%d') if log.ACTIVITY_DATE else '',
                'status_trx': log.STATUS_TRX or '',
                'pengganti': log.PENGGANTI or '0',
            })
        
        # Format rollback
        rollback_data = []
        for i, (lb, peg) in enumerate(rollback_list, 1):
            rollback_data.append({
                'no': i,
                'guid_log_backup': lb.GUID_LOG_BACKUP,  # ✅ PK untuk identifikasi
                'guid_log': lb.GUID_LOG,
                'nip': lb.NIP_PENGGANTI or '-',  # ✅ NIP disimpan di NIP_PENGGANTI
                'nama': peg.NAMA if peg else (lb.NIP_PENGGANTI or '-'),
                'fungsional': lb.FUNGSIONAL or '',
                'shift': lb.SHIFT or '',
                'act_date': lb.ACTIVITY_DATE.strftime('%Y.%m.%d') if lb.ACTIVITY_DATE else '',
            })
        
        return jsonify({
            'success': True,
            'guid_log': guid_log,
            'jadwal': jadwal_data,
            'rollback': rollback_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_rejadwal_siaga_delete_personil():
    """
    API: Hapus personil dari jadwal
    """
    try:
        data = request.get_json()
        print("📥 Delete Personil:", data)
        
        guid_log = data.get('guid_log', '')
        nip = data.get('nip', '')
        act_date = data.get('act_date', '')
        shift = data.get('shift', '')
        
        if not guid_log or not nip:
            return jsonify({'success': False, 'error': 'Data tidak lengkap'})
        
        act_date_fixed = act_date.replace('.', '-')
        act_date_obj = datetime.strptime(act_date_fixed, '%Y-%m-%d')
        
        log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == act_date_obj.date(),
            LogActivity.SHIFT == shift
        ).first()
        
        if not log:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        # ✅ Backup - simpan NIP di NIP_PENGGANTI, tandai di TRANSAKSI_FORM
        backup = LogActivityBackup(
            GUID_LOG_BACKUP=f"BACKUP_{log.GUID_LOG}_{log.NIP}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            GUID_LOG=log.GUID_LOG,
            TRX=log.TRX,
            ACTIVITY=log.ACTIVITY,
            ACTIVITY_DATE=log.ACTIVITY_DATE,
            NOTE=log.NOTE,
            TEMPAT=log.TEMPAT,
            PERIHAL=log.PERIHAL,
            UPDATE_BY='admin',
            UPDATE_DATE=datetime.now(),
            FUNGSIONAL=log.FUNGSIONAL,
            SHIFT_1=log.SHIFT_1,
            SHIFT_2=log.SHIFT_2,
            PENGGANTI=log.PENGGANTI,
            STATUS_TRX=log.STATUS_TRX,
            KET_UPDATE=f"Delete Rejadwal - {log.NIP}",
            NIP_PENGGANTI=log.NIP,  # ✅ Simpan NIP asli di sini
            SHIFT=log.SHIFT,
            TRANSAKSI_FORM='Delete Rejadwal',  # ✅ Tanda bahwa ini data delete
        )
        db.session.add(backup)
        db.session.delete(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Personil {nip} berhasil dihapus'})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_rejadwal_siaga_cancel_request():
    """
    API: Cancel request (ViewData) - Update StatusID = 2, StatusTrx = '-'
    """
    try:
        data = request.get_json()
        guid_log = data.get('guid_log', '')
        nip = data.get('nip', '')
        act_date = data.get('act_date', '')
        shift = data.get('shift', '')
        
        if not guid_log or not nip:
            return jsonify({'success': False, 'error': 'Data tidak lengkap'})
        
        act_date_fixed = act_date.replace('.', '-')
        act_date_obj = datetime.strptime(act_date_fixed, '%Y-%m-%d')
        
        log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == act_date_obj.date(),
            LogActivity.SHIFT == shift
        ).first()
        
        if not log:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        log.STATUS_ID = 2
        log.STATUS_TRX = '-'
        log.UPDATE_BY = 'admin'
        log.UPDATE_DATE = datetime.now()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Request berhasil dicancel'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


def api_rejadwal_siaga_batal_piket():
    """
    API: Batal piket (CloseData dari gridfind) - Update StatusID = 0
    """
    try:
        data = request.get_json()
        guid_log = data.get('guid_log', '')
        nip = data.get('nip', '')
        act_date = data.get('act_date', '')
        shift = data.get('shift', '')
        
        if not guid_log or not nip:
            return jsonify({'success': False, 'error': 'Data tidak lengkap'})
        
        act_date_fixed = act_date.replace('.', '-')
        act_date_obj = datetime.strptime(act_date_fixed, '%Y-%m-%d')
        
        log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == act_date_obj.date(),
            LogActivity.SHIFT == shift
        ).first()
        
        if not log:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        log.STATUS_ID = 0
        log.UPDATE_BY = 'admin'
        log.UPDATE_DATE = datetime.now()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Piket berhasil dibatalkan'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


def api_rejadwal_siaga_ubah_status():
    """
    API: Ubah status (Ubahstatus) - Update StatusID = 2, StatusTrx = '-'
    """
    try:
        data = request.get_json()
        guid_log = data.get('guid_log', '')
        nip = data.get('nip', '')
        act_date = data.get('act_date', '')
        shift = data.get('shift', '')
        
        if not guid_log or not nip:
            return jsonify({'success': False, 'error': 'Data tidak lengkap'})
        
        act_date_fixed = act_date.replace('.', '-')
        act_date_obj = datetime.strptime(act_date_fixed, '%Y-%m-%d')
        
        log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == act_date_obj.date(),
            LogActivity.SHIFT == shift
        ).first()
        
        if not log:
            return jsonify({'success': False, 'error': 'Data tidak ditemukan'})
        
        log.STATUS_ID = 2
        log.STATUS_TRX = '-'
        log.UPDATE_BY = 'admin'
        log.UPDATE_DATE = datetime.now()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Status berhasil diubah'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


def api_rejadwal_siaga_rollback():
    """
    API: Rollback personil yang terdelete
    """
    try:
        data = request.get_json()
        print("📥 Rollback:", data)
        
        guid_log = data.get('guid_log', '')
        nip = data.get('nip', '')
        guid_log_backup = data.get('guid_log_backup', '')  # ✅ PK
        
        if not guid_log or not nip or not guid_log_backup:
            return jsonify({'success': False, 'error': 'Data tidak lengkap'})
        
        # ✅ Cari by GUID_LOG_BACKUP (Primary Key)
        backup = LogActivityBackup.query.get(guid_log_backup)
        
        if not backup:
            return jsonify({'success': False, 'error': 'Data backup tidak ditemukan'})
        
        # Insert ke LogActivity
        new_log = LogActivity(
            GUID_LOG=backup.GUID_LOG,
            TRAKSAKSI_ID=0,
            UNIT_KERJA_ID=0,
            GUID_LOG_BACKUP=backup.GUID_LOG_BACKUP or '',
            GUID_TIM='',
            STATUS_ID=2,
            NIP=backup.NIP_PENGGANTI,  # ✅ Ambil NIP dari NIP_PENGGANTI
            TRX=backup.TRX,
            ACTIVITY=backup.ACTIVITY,
            ACTIVITY_DATE=backup.ACTIVITY_DATE,
            NOTE=backup.NOTE,
            TEMPAT=backup.TEMPAT,
            PERIHAL=backup.PERIHAL,
            UPDATE_BY='admin',
            UPDATE_DATE=datetime.now(),
            FUNGSIONAL=backup.FUNGSIONAL,
            PENGGANTI=backup.PENGGANTI,
            KET_UPDATE=backup.KET_UPDATE,
            NIP_PENGGANTI=backup.NIP_PENGGANTI,
            SHIFT=backup.SHIFT,
            SHIFT_1=backup.SHIFT_1,
            SHIFT_2=backup.SHIFT_2
        )
        db.session.add(new_log)
        db.session.delete(backup)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Rollback berhasil'})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def api_rejadwal_siaga_get_fungsional():
    """API: Get list Fungsional dari MfOrgzSiaga"""
    try:
        fungsional_list = db.session.query(MfOrgzSiaga.FUNGSIONAL).distinct().order_by(MfOrgzSiaga.URUT_FUNGSIONAL).all()
        data = [f[0] for f in fungsional_list if f[0]]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []})


def api_rejadwal_siaga_get_shift():
    """API: Get list Shift"""
    try:
        shift_list = MfShift.query.filter(MfShift.NAMA_SHIFT != '').order_by(MfShift.SHIFT_ID).all()
        data = [{'id': s.SHIFT_ID, 'nama': s.NAMA_SHIFT} for s in shift_list]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'data': []})

def api_rejadwal_siaga_add_personil():
    """
    API: Tambah personil ke jadwal yang sudah ada
    """
    try:
        data = request.get_json()
        print("📥 Tambah Personil:", data)
        
        guid_log = data.get('guid_log', '')
        nip = data.get('nip', '')
        fungsional = data.get('fungsional', '')
        unit_kerja_id = data.get('unit_kerja_id', '')
        tgl = data.get('tgl', '')
        shift = data.get('shift', '')
        
        if not guid_log or not nip:
            return jsonify({'success': False, 'error': 'Data tidak lengkap'})
        
        # Konversi tanggal
        tgl_date = datetime.strptime(tgl, '%Y-%m-%d')
        
        # Cek apakah personil sudah ada di jadwal
        existing = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log,
            LogActivity.NIP == nip,
            db.func.date(LogActivity.ACTIVITY_DATE) == tgl_date.date(),
            LogActivity.SHIFT == shift
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': f'Personil {nip} sudah ada di jadwal ini'})
        
        # Ambil data pegawai
        pegawai = Pegawai.query.filter(Pegawai.NIP == nip).first()
        if not pegawai:
            return jsonify({'success': False, 'error': 'Pegawai tidak ditemukan'})
        
        # Ambil data log yang sudah ada
        existing_log = LogActivity.query.filter(
            LogActivity.GUID_LOG == guid_log
        ).first()
        
        if not existing_log:
            return jsonify({'success': False, 'error': 'Jadwal induk tidak ditemukan'})
        
        # ✅ Ambil TRAKSAKSI_ID dengan fallback
        traksaksi_id = existing_log.TRAKSAKSI_ID if existing_log.TRAKSAKSI_ID else 0
        
        # ✅ Ambil UNIT_KERJA_ID dengan fallback
        final_unit_kerja_id = int(unit_kerja_id) if unit_kerja_id else (pegawai.UNIT_KERJA_ID or 0)
        
        # Insert personil baru
        new_log = LogActivity(
            GUID_LOG=guid_log,
            NIP=nip,
            TRAKSAKSI_ID=traksaksi_id,  # ✅ WAJIB DIISI
            UNIT_KERJA_ID=final_unit_kerja_id,
            GUID_LOG_BACKUP='',
            GUID_TIM=existing_log.GUID_TIM or '',
            ACTIVITY='Piket Siaga',
            ACTIVITY_DATE=tgl_date,
            NOTE=existing_log.NOTE or '',
            TEMPAT=existing_log.TEMPAT or '',
            PERIHAL=existing_log.PERIHAL or '',
            TRX=existing_log.TRX or 'Jadwal Piket',
            UPDATE_BY='admin',
            UPDATE_DATE=datetime.now(),
            FUNGSIONAL=fungsional,
            SHIFT=shift,
            SHIFT_1=0,
            SHIFT_2=0,
            PENGGANTI=0,
            STATUS_ID=2,
            STATUS_TRX='-',
            KET_UPDATE=f'Tambah personil by admin - {nip}',
            NIP_PENGGANTI=nip,
            TGL_CLOSING=None
        )
        
        db.session.add(new_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Personil {nip} berhasil ditambahkan ke jadwal'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

def data_siaga_membuat_jadwal_piket_siaga():
    """Render halaman Data Siaga Membuat Jadwal Piket Siaga."""
    return render_template('pages/dashboard_2/Data_Siaga_Membuat_Jadwal_Piket_Siaga.html')

def data_siaga_view_jadwal():
    return render_template(
        'pages/dashboard_2/Data_Siaga_View_Jadwal.html'
    )

def api_siaga_view_jadwal_get():
    """
    API READ-ONLY VIEW JADWAL SIAGA.

    Sumber:
        MF_TIM_SIAGA
        MF_TIM_SIAGA_ANGGOTA
        MF_UNIT_KERJA
        PEGAWAI

    Tidak melakukan INSERT / UPDATE / DELETE.
    """

    try:
        bulan = str(
            request.args.get('bulan') or ''
        ).strip().zfill(2)

        tahun = str(
            request.args.get('tahun') or ''
        ).strip()

        unit_id = str(
            request.args.get('unit_kerja_id') or ''
        ).strip()

        fungsional = str(
            request.args.get('fungsional') or ''
        ).strip()

        if bulan not in {
            '01', '02', '03', '04', '05', '06',
            '07', '08', '09', '10', '11', '12'
        }:
            return jsonify({
                'success': False,
                'error': 'Bulan tidak valid.'
            }), 400

        if len(tahun) != 4 or not tahun.isdigit():
            return jsonify({
                'success': False,
                'error': 'Tahun tidak valid.'
            }), 400

        if not unit_id:
            return jsonify({
                'success': False,
                'error': 'Unit kerja wajib dipilih.'
            }), 400

        if not fungsional:
            return jsonify({
                'success': False,
                'error': 'Jabatan siaga wajib dipilih.'
            }), 400

        rows = db.session.execute(
            db.text("""
                SELECT
                    t.NoUrutTim,
                    t.GUIDTim,
                    t.NamaTim,
                    t.IDUnitKerja,
                    u.UnitKerjaName,
                    t.FungsionalTIM,
                    t.Shift AS RosterShift,
                    t.BulanPeriode,
                    t.TahunPeriode,
                    t.IsAktif AS RosterAktif,
                    a.Nourut,
                    a.NIP,
                    p.Nama AS NamaPegawai,
                    a.Fungsional AS FungsionalAnggota,
                    a.Shift AS AnggotaShift,
                    a.IsAktif AS AnggotaAktif
                FROM MF_TIM_SIAGA t
                LEFT JOIN MF_TIM_SIAGA_ANGGOTA a
                    ON a.GUIDTim = t.GUIDTim
                LEFT JOIN PEGAWAI p
                    ON p.NIP = a.NIP
                LEFT JOIN MF_UNIT_KERJA u
                    ON u.IDUnitKerja = t.IDUnitKerja
                WHERE t.BulanPeriode = :bulan
                  AND t.TahunPeriode = :tahun
                  AND t.IDUnitKerja = :unit_id
                  AND t.FungsionalTIM = :fungsional
                ORDER BY
                    t.NoUrutTim ASC,
                    t.Shift ASC,
                    a.Nourut ASC
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
            }
        ).mappings().all()

        data = []

        for row in rows:
            data.append({
                'no_urut': row['NoUrutTim'],
                'guid_tim': row['GUIDTim'],
                'nama_tim': row['NamaTim'],
                'unit_id': row['IDUnitKerja'],
                'unit_name': row['UnitKerjaName'],
                'fungsional': row['FungsionalTIM'],
                'shift': row['RosterShift'],
                'bulan': row['BulanPeriode'],
                'tahun': row['TahunPeriode'],
                'roster_aktif': row['RosterAktif'],
                'nourut': row['Nourut'],
                'nip': row['NIP'],
                'nama_pegawai': row['NamaPegawai'],
                'fungsional_anggota':
                    row['FungsionalAnggota'],
                'shift_anggota':
                    row['AnggotaShift'],
                'anggota_aktif':
                    row['AnggotaAktif'],
            })

        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e),
        }), 500

def api_siaga_view_jadwal_edit():
    """
    API EDIT SATU ROSTER JADWAL SIAGA.

    BUSINESS RULE FINAL:

    1. Satu request = satu roster logis.
    2. Identitas roster:
           bulan
           tahun
           unit_kerja_id
           fungsional
           no_urut
    3. NIP harus valid di PEGAWAI.
    4. NIP duplicate dalam roster ditolak.
    5. NIP yang sudah aktif pada roster lain ditolak.
    6. Jika roster memiliki Shift 1 + Shift 2:
           kedua shift diperbarui.
    7. Jika roster hanya memiliki Shift 1:
           Shift 1 diperbarui
           DAN Shift 2 otomatis dibuat.
    8. Anggota Shift 2 selalu sama dengan anggota
       roster yang disimpan.
    9. Shift 1 tidak pernah dihapus.
   10. Shift 2 yang sudah ada tidak dibuat ulang.
   11. Tidak mengubah struktur database.
   12. Transactional.
    """

    try:

        data = request.get_json(silent=True) or {}

        bulan = str(
            data.get('bulan') or ''
        ).strip().zfill(2)

        tahun = str(
            data.get('tahun') or ''
        ).strip()

        unit_id = str(
            data.get('unit_kerja_id') or ''
        ).strip()

        fungsional = str(
            data.get('fungsional') or ''
        ).strip()

        no_urut = data.get('no_urut')

        pegawai = data.get('pegawai') or []

        # ========================================================
        # VALIDASI IDENTITAS
        # ========================================================

        if bulan not in {
            '01', '02', '03', '04', '05', '06',
            '07', '08', '09', '10', '11', '12'
        }:
            return jsonify({
                'success': False,
                'error': 'Bulan tidak valid.'
            }), 400

        if (
            len(tahun) != 4
            or not tahun.isdigit()
        ):
            return jsonify({
                'success': False,
                'error': 'Tahun tidak valid.'
            }), 400

        if not unit_id:
            return jsonify({
                'success': False,
                'error': 'Unit kerja wajib diisi.'
            }), 400

        if not fungsional:
            return jsonify({
                'success': False,
                'error': 'Jabatan siaga wajib diisi.'
            }), 400

        try:
            no_urut = int(no_urut)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'error': 'Nomor roster tidak valid.'
            }), 400

        if no_urut < 1:
            return jsonify({
                'success': False,
                'error': 'Nomor roster tidak valid.'
            }), 400

        # ========================================================
        # NORMALISASI NIP
        # ========================================================

        nip_list = []

        for item in pegawai:

            if isinstance(item, dict):
                nip = str(
                    item.get('nip') or ''
                ).strip()
            else:
                nip = str(item or '').strip()

            if nip:
                nip_list.append(nip)

        if not nip_list:
            return jsonify({
                'success': False,
                'error': 'Minimal satu pegawai harus dipilih.'
            }), 400

        if len(nip_list) != len(set(nip_list)):
            return jsonify({
                'success': False,
                'error': 'Terdapat NIP yang sama dalam roster.'
            }), 400

        # ========================================================
        # LOCK ROSTER
        # ========================================================

        rows = db.session.execute(
            db.text("""
                SELECT
                    GUIDTim,
                    Shift,
                    NoUrutTim,
                    NamaTim,
                    IDUnitKerja,
                    IsAktif,
                    UpdateBy,
                    UpdateDate,
                    FungsionalTIM,
                    BulanPeriode,
                    TahunPeriode
                FROM MF_TIM_SIAGA
                WHERE BulanPeriode = :bulan
                  AND TahunPeriode = :tahun
                  AND IDUnitKerja = :unit_id
                  AND FungsionalTIM = :fungsional
                  AND NoUrutTim = :no_urut
                ORDER BY Shift
                FOR UPDATE
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
                'no_urut': no_urut,
            }
        ).mappings().all()

        if not rows:
            return jsonify({
                'success': False,
                'error': 'Roster tidak ditemukan.'
            }), 404

        shift_map = {
            str(row['Shift']): row
            for row in rows
            if row['Shift'] is not None
        }

        if '1' not in shift_map:
            return jsonify({
                'success': False,
                'error': 'Shift 1 pada roster tidak ditemukan.'
            }), 400

        # ========================================================
        # VALIDASI MASTER PEGAWAI
        # ========================================================

        placeholders = ','.join(
            f':nip_{i}'
            for i in range(len(nip_list))
        )

        pegawai_params = {
            f'nip_{i}': nip
            for i, nip in enumerate(nip_list)
        }

        pegawai_rows = db.session.execute(
            db.text(f"""
                SELECT
                    NIP,
                    Nama
                FROM PEGAWAI
                WHERE NIP IN ({placeholders})
            """),
            pegawai_params
        ).mappings().all()

        pegawai_map = {
            str(row['NIP']).strip(): row['Nama']
            for row in pegawai_rows
        }

        missing = [
            nip
            for nip in nip_list
            if nip not in pegawai_map
        ]

        if missing:
            return jsonify({
                'success': False,
                'error': (
                    'Pegawai tidak ditemukan: '
                    + ', '.join(missing)
                )
            }), 400

        # ========================================================
        # VALIDASI DUPLIKASI DI ROSTER LAIN
        # ========================================================

        duplicate_rows = db.session.execute(
            db.text("""
                SELECT
                    a.NIP,
                    t.NoUrutTim,
                    t.Shift
                FROM MF_TIM_SIAGA_ANGGOTA a
                INNER JOIN MF_TIM_SIAGA t
                    ON t.GUIDTim = a.GUIDTim
                WHERE t.BulanPeriode = :bulan
                  AND t.TahunPeriode = :tahun
                  AND t.IDUnitKerja = :unit_id
                  AND t.FungsionalTIM = :fungsional
                  AND a.NIP IN :nip_list
                  AND t.NoUrutTim <> :no_urut
                  AND a.IsAktif = 'Y'
            """).bindparams(
                db.bindparam(
                    'nip_list',
                    expanding=True
                )
            ),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
                'nip_list': nip_list,
                'no_urut': no_urut,
            }
        ).mappings().all()

        if duplicate_rows:

            duplicate_nips = sorted({
                str(row['NIP'])
                for row in duplicate_rows
            })

            return jsonify({
                'success': False,
                'error': (
                    'Pegawai sudah berada pada roster lain: '
                    + ', '.join(duplicate_nips)
                )
            }), 400

        # ========================================================
        # USER / AUDIT
        # ========================================================

        update_by = (
            getattr(
                getattr(g, 'user', None),
                'username',
                None
            )
            or 'HRIS'
        )

        update_date = datetime.now()

        # ========================================================
        # TENTUKAN SHIFT YANG AKAN DIPROSES
        # ========================================================

        shift1 = shift_map['1']

        if '2' in shift_map:
            target_shifts = [
                shift1,
                shift_map['2']
            ]
            shift2_created = False

        else:
            target_shifts = [
                shift1
            ]
            shift2_created = True

        # ========================================================
        # UPDATE ANGGOTA SHIFT YANG SUDAH ADA
        #
        # Tidak DELETE fisik.
        # Record lama dibuat tidak aktif.
        # Jika record NIP sudah pernah ada tetapi tidak aktif,
        # record tersebut diaktifkan kembali agar aman terhadap
        # PRIMARY KEY (GUIDTim, NIP).
        # ========================================================

        for row in target_shifts:

            guid_tim = str(row['GUIDTim'])
            shift = str(row['Shift'])

            db.session.execute(
                db.text("""
                    UPDATE MF_TIM_SIAGA_ANGGOTA
                    SET
                        IsAktif = 'N',
                        UpdateDate = :update_date,
                        UpdateBy = :update_by
                    WHERE GUIDTim = :guid_tim
                      AND IsAktif = 'Y'
                """),
                {
                    'guid_tim': guid_tim,
                    'update_date': update_date,
                    'update_by': update_by,
                }
            )

            for nomor, nip in enumerate(
                nip_list,
                start=1
            ):

                existing = db.session.execute(
                    db.text("""
                        SELECT
                            GUIDTim,
                            NIP
                        FROM MF_TIM_SIAGA_ANGGOTA
                        WHERE GUIDTim = :guid_tim
                          AND NIP = :nip
                        LIMIT 1
                    """),
                    {
                        'guid_tim': guid_tim,
                        'nip': nip,
                    }
                ).mappings().first()

                if existing:

                    db.session.execute(
                        db.text("""
                            UPDATE MF_TIM_SIAGA_ANGGOTA
                            SET
                                Fungsional = :fungsional,
                                IsAktif = 'Y',
                                IDUnitKerja = :unit_id,
                                Nourut = :nomor,
                                UpdateDate = :update_date,
                                UpdateBy = :update_by,
                                BulanPeriode = :bulan,
                                TahunPeriode = :tahun,
                                Shift = :shift
                            WHERE GUIDTim = :guid_tim
                              AND NIP = :nip
                        """),
                        {
                            'guid_tim': guid_tim,
                            'nip': nip,
                            'fungsional': fungsional,
                            'unit_id': unit_id,
                            'nomor': nomor,
                            'update_date': update_date,
                            'update_by': update_by,
                            'bulan': bulan,
                            'tahun': tahun,
                            'shift': shift,
                        }
                    )

                else:

                    db.session.execute(
                        db.text("""
                            INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                                GUIDTim,
                                NIP,
                                Fungsional,
                                IsAktif,
                                IDUnitKerja,
                                Nourut,
                                UpdateDate,
                                UpdateBy,
                                BulanPeriode,
                                TahunPeriode,
                                Shift
                            )
                            VALUES (
                                :guid_tim,
                                :nip,
                                :fungsional,
                                'Y',
                                :unit_id,
                                :nomor,
                                :update_date,
                                :update_by,
                                :bulan,
                                :tahun,
                                :shift
                            )
                        """),
                        {
                            'guid_tim': guid_tim,
                            'nip': nip,
                            'fungsional': fungsional,
                            'unit_id': unit_id,
                            'nomor': nomor,
                            'update_date': update_date,
                            'update_by': update_by,
                            'bulan': bulan,
                            'tahun': tahun,
                            'shift': shift,
                        }
                    )

        # ========================================================
        # BUAT SHIFT 2 JIKA BELUM ADA
        # ========================================================

        if shift2_created:

            new_guid_row = db.session.execute(
                db.text("""
                    SELECT UUID() AS GUIDTim
                """)
            ).mappings().first()

            new_guid = str(
                new_guid_row['GUIDTim']
            )

            db.session.execute(
                db.text("""
                    INSERT INTO MF_TIM_SIAGA (
                        NoUrutTim,
                        GUIDTim,
                        NamaTim,
                        IDUnitKerja,
                        IsAktif,
                        UpdateBy,
                        UpdateDate,
                        BulanPeriode,
                        TahunPeriode,
                        FungsionalTIM,
                        Shift
                    )
                    VALUES (
                        :no_urut,
                        :guid_tim,
                        :nama_tim,
                        :unit_id,
                        :is_aktif,
                        :update_by,
                        :update_date,
                        :bulan,
                        :tahun,
                        :fungsional,
                        '2'
                    )
                """),
                {
                    'no_urut': no_urut,
                    'guid_tim': new_guid,
                    'nama_tim': shift1['NamaTim'],
                    'unit_id': unit_id,
                    'is_aktif': shift1['IsAktif'] or 'Y',
                    'update_by': update_by,
                    'update_date': update_date,
                    'bulan': bulan,
                    'tahun': tahun,
                    'fungsional': fungsional,
                }
            )

            for nomor, nip in enumerate(
                nip_list,
                start=1
            ):

                db.session.execute(
                    db.text("""
                        INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                            GUIDTim,
                            NIP,
                            Fungsional,
                            IsAktif,
                            IDUnitKerja,
                            Nourut,
                            UpdateDate,
                            UpdateBy,
                            BulanPeriode,
                            TahunPeriode,
                            Shift
                        )
                        VALUES (
                            :guid_tim,
                            :nip,
                            :fungsional,
                            'Y',
                            :unit_id,
                            :nomor,
                            :update_date,
                            :update_by,
                            :bulan,
                            :tahun,
                            '2'
                        )
                    """),
                    {
                        'guid_tim': new_guid,
                        'nip': nip,
                        'fungsional': fungsional,
                        'unit_id': unit_id,
                        'nomor': nomor,
                        'update_date': update_date,
                        'update_by': update_by,
                        'bulan': bulan,
                        'tahun': tahun,
                    }
                )

        # ========================================================
        # COMMIT
        # ========================================================

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Roster #{no_urut} berhasil diperbarui.'
            ),
            'data': {
                'bulan': bulan,
                'tahun': tahun,
                'unit_kerja_id': unit_id,
                'fungsional': fungsional,
                'no_urut': no_urut,
                'shift_1': True,
                'shift_2': True,
                'shift_2_created': shift2_created,
                'pegawai': [
                    {
                        'nip': nip,
                        'nama': pegawai_map.get(nip, '')
                    }
                    for nip in nip_list
                ]
            }
        })

    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            'Gagal edit roster jadwal siaga'
        )

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def api_siaga_view_jadwal_lengkapi_shift2():
    """
    API LENGKAPI SHIFT 2 ROSTER JADWAL SIAGA.

    Digunakan untuk roster yang sudah memiliki Shift 1
    tetapi belum memiliki Shift 2.

    Business Rule:

        1. Identitas roster:
               bulan
               tahun
               unit_kerja_id
               fungsional
               no_urut

        2. Shift 1 wajib tersedia.

        3. Shift 2 wajib belum tersedia.

        4. Anggota Shift 2 dibuat sama persis dengan
           anggota Shift 1.

        5. GUIDTim baru dibuat untuk Shift 2.

        6. Nourut mengikuti anggota Shift 1.

        7. Tidak mengubah anggota Shift 1.

        8. Tidak membuat Shift 2 jika sudah ada.

        9. Transactional.

       10. Struktur database tidak diubah.
    """

    try:

        data = request.get_json(silent=True) or {}

        bulan = str(
            data.get('bulan') or ''
        ).strip().zfill(2)

        tahun = str(
            data.get('tahun') or ''
        ).strip()

        unit_id = str(
            data.get('unit_kerja_id') or ''
        ).strip()

        fungsional = str(
            data.get('fungsional') or ''
        ).strip()

        no_urut = data.get('no_urut')

        if bulan not in {
            '01', '02', '03', '04', '05', '06',
            '07', '08', '09', '10', '11', '12'
        }:
            return jsonify({
                'success': False,
                'error': 'Bulan tidak valid.'
            }), 400

        if (
            len(tahun) != 4
            or not tahun.isdigit()
        ):
            return jsonify({
                'success': False,
                'error': 'Tahun tidak valid.'
            }), 400

        if not unit_id:
            return jsonify({
                'success': False,
                'error': 'Unit kerja wajib diisi.'
            }), 400

        if not fungsional:
            return jsonify({
                'success': False,
                'error': 'Jabatan siaga wajib diisi.'
            }), 400

        try:
            no_urut = int(no_urut)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'error': 'Nomor roster tidak valid.'
            }), 400

        if no_urut < 1:
            return jsonify({
                'success': False,
                'error': 'Nomor roster tidak valid.'
            }), 400

        # ============================================================
        # AMBIL ROSTER DAN KUNCI TRANSAKSI
        # ============================================================

        rows = db.session.execute(
            db.text("""
                SELECT
                    GUIDTim,
                    Shift,
                    NoUrutTim,
                    NamaTim,
                    IDUnitKerja,
                    IsAktif,
                    UpdateBy,
                    FungsionalTIM,
                    BulanPeriode,
                    TahunPeriode
                FROM MF_TIM_SIAGA
                WHERE BulanPeriode = :bulan
                  AND TahunPeriode = :tahun
                  AND IDUnitKerja = :unit_id
                  AND FungsionalTIM = :fungsional
                  AND NoUrutTim = :no_urut
                ORDER BY Shift
                FOR UPDATE
            """),
            {
                'bulan': bulan,
                'tahun': tahun,
                'unit_id': unit_id,
                'fungsional': fungsional,
                'no_urut': no_urut,
            }
        ).mappings().all()

        if not rows:
            return jsonify({
                'success': False,
                'error': 'Roster tidak ditemukan.'
            }), 404

        shifts = {
            str(row['Shift'])
            for row in rows
            if row['Shift'] is not None
        }

        if '1' not in shifts:
            return jsonify({
                'success': False,
                'error': 'Shift 1 pada roster tidak ditemukan.'
            }), 400

        if '2' in shifts:
            return jsonify({
                'success': False,
                'error': 'Shift 2 pada roster sudah tersedia.'
            }), 409

        # ============================================================
        # AMBIL ANGGOTA SHIFT 1
        # ============================================================

        shift1 = next(
            row for row in rows
            if str(row['Shift']) == '1'
        )

        anggota = db.session.execute(
            db.text("""
                SELECT
                    NIP,
                    Fungsional,
                    IsAktif,
                    IDUnitKerja,
                    Nourut,
                    UpdateBy
                FROM MF_TIM_SIAGA_ANGGOTA
                WHERE GUIDTim = :guid_tim
                ORDER BY Nourut
            """),
            {
                'guid_tim': shift1['GUIDTim']
            }
        ).mappings().all()

        if not anggota:
            return jsonify({
                'success': False,
                'error': 'Shift 1 tidak memiliki anggota.'
            }), 400

        # ============================================================
        # BUAT GUID SHIFT 2
        # ============================================================

        pasangan_guid = str(
            uuid.uuid4()
        )

        now = datetime.now()

        update_by = (
            getattr(g, 'username', None)
            or getattr(g, 'user', None)
            or 'system'
        )

        if hasattr(update_by, 'username'):
            update_by = update_by.username

        update_by = str(update_by)[:50]

        # ============================================================
        # NAMA TIM SHIFT 2
        # ============================================================

        nama_tim = shift1['NamaTim']

        # ============================================================
        # INSERT MASTER SHIFT 2
        # ============================================================

        db.session.execute(
            db.text("""
                INSERT INTO MF_TIM_SIAGA (
                    NoUrutTim,
                    GUIDTim,
                    NamaTim,
                    IDUnitKerja,
                    IsAktif,
                    UpdateBy,
                    UpdateDate,
                    BulanPeriode,
                    TahunPeriode,
                    FungsionalTIM,
                    Shift
                )
                VALUES (
                    :no_urut,
                    :guid_tim,
                    :nama_tim,
                    :unit_id,
                    :is_aktif,
                    :update_by,
                    :update_date,
                    :bulan,
                    :tahun,
                    :fungsional,
                    '2'
                )
            """),
            {
                'no_urut': no_urut,
                'guid_tim': pasangan_guid,
                'nama_tim': nama_tim,
                'unit_id': unit_id,
                'is_aktif': shift1['IsAktif'] or 'Y',
                'update_by': update_by,
                'update_date': now,
                'bulan': bulan,
                'tahun': tahun,
                'fungsional': fungsional,
            }
        )

        # ============================================================
        # SALIN ANGGOTA SHIFT 1 -> SHIFT 2
        # ============================================================

        for anggota_row in anggota:

            db.session.execute(
                db.text("""
                    INSERT INTO MF_TIM_SIAGA_ANGGOTA (
                        GUIDTim,
                        NIP,
                        Fungsional,
                        IsAktif,
                        IDUnitKerja,
                        Nourut,
                        UpdateDate,
                        UpdateBy,
                        BulanPeriode,
                        TahunPeriode,
                        Shift
                    )
                    VALUES (
                        :guid_tim,
                        :nip,
                        :fungsional,
                        :is_aktif,
                        :unit_id,
                        :nourut,
                        :update_date,
                        :update_by,
                        :bulan,
                        :tahun,
                        '2'
                    )
                """),
                {
                    'guid_tim': pasangan_guid,
                    'nip': anggota_row['NIP'],
                    'fungsional': anggota_row['Fungsional'] or fungsional,
                    'is_aktif': anggota_row['IsAktif'] or 'Y',
                    'unit_id': anggota_row['IDUnitKerja'] or unit_id,
                    'nourut': anggota_row['Nourut'],
                    'update_date': now,
                    'update_by': update_by,
                    'bulan': bulan,
                    'tahun': tahun,
                }
            )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': (
                f'Shift 2 Roster #{no_urut} berhasil '
                'dilengkapi dari Shift 1.'
            ),
            'data': {
                'bulan': bulan,
                'tahun': tahun,
                'unit_kerja_id': unit_id,
                'fungsional': fungsional,
                'no_urut': no_urut,
                'shift': '2',
                'jumlah_anggota': len(anggota),
            }
        })

    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            'Gagal melengkapi Shift 2 roster siaga'
        )

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

