# HRIS 2013 Backup Migration — Working Notes & Design

> Status: **IN PROGRESS**
>
> This document records the verified migration path from the legacy MSSQL HRIS backup into HRIS Reborn MariaDB, plus the planned reusable operator workflow.

## 1. Current Architecture

- Source backup: `Backup-HRIS-2013.bak`
- Restored SQL Server database: `HRIS_2013_BACKUP`
- SQL Server container: `sqlserver-migration`
- Target database: MariaDB `HRIS`
- Target application server/database environment: HRIS-DB
- Migration workspace: `/opt/sqlserver-migration/hris`

The `.bak` file is the actual HRIS 2013 database backup used as the source of the HRIS Reborn migration. It is **not** limited to Dinas Luar data.

## 2. Verified Restore

The backup was restored successfully as:

`HRIS_2013_BACKUP`

Verified:

- Database status: ONLINE
- Source tables: 59
- `sysdiagrams`: excluded from application migration
- Application tables to process: 58

The source database can be accessed with:

`sqlcmd -S localhost -U sa -d HRIS_2013_BACKUP -C`

The working non-interactive pattern that was verified successfully is:

```bash
docker exec -i \
  -e SQLCMDPASSWORD="$SQL_PASS" \
  sqlserver-migration \
  /opt/mssql-tools18/bin/sqlcmd \
  -S localhost \
  -U sa \
  -d HRIS_2013_BACKUP \
  -C \
  -h -1 \
  -W \
  -Q "SET NOCOUNT ON; SELECT name FROM sys.tables WHERE name <> 'sysdiagrams' ORDER BY name;"
```

This returned all 58 application tables and exit code 0.

## 3. Important Migration Principle

The migration must be **MERGE / INSERT-ONLY**.

Never:

- DROP target tables
- TRUNCATE target tables
- DELETE existing HRIS Reborn records
- overwrite existing records in bulk
- assume source row count equals records that must be inserted

Existing HRIS Reborn data must remain intact.

The migration engine must first determine which source records are already present in MariaDB and insert only records that are genuinely missing.

## 4. Verified Example

For `Absensi -> ABSENSI`:

- SQL Server source: 346,473 records
- MariaDB target: 345,617 records
- Difference in row counts: 856

The 856-row difference is only a **count difference**. It must not automatically be treated as 856 new records until record-level matching is performed.

## 5. Source → Target Table Mapping

Known mapping:

| SQL Server | MariaDB |
|---|---|
| Absensi | ABSENSI |
| Absensibackup | ABSENSI_BACKUP |
| AbsensiTemp | ABSENSI_TEMP |
| BukuHarianHead | BUKU_HARIAN_HEAD |
| DinasLuar | DINAS_LUAR |
| DRH | DRH |
| HakAksesForm | HAK_AKSES_FORM |
| HakAksesTypeSprin | HAK_AKSES_TYPE_SPRIN |
| Kalender | KALENDER |
| Lembur | LEMBUR |
| LogActivity | LOG_ACTIVITIY |
| LogActivityBackUp | LOG_ACTIVITIY_BACKUP |
| LogTransaksi | LOG_TRANSAKSI |
| MediaInformasi | MEDIA_INFORMASI |
| MFClass | MF_CLASS |
| MFConfig | MF_CONFIG |
| MFEmailSend | MF_EMAIL_SEND |
| MFEselon | MF_ESELON |
| MFFieldCari | MF_FIELD_CARI |
| MFForm | MF_FORM |
| NewMFForm | MF_FORM_NEW |
| MFGol | MF_GOL |
| MFGroupJabatan | MF_GROUP_JABATAN |
| MFHostNameFP | MF_HOST_NAME_FP |
| MFJabatan | MF_JABATAN |
| MFJabatanKegiatan | MF_JABATAN_KEGIATAN |
| MFJamKerja | MF_JAM_KERJA |
| MFJobList | MF_JOBLIST |
| MFKlasifikasiSurat | MF_KLASIFIKASI_SURAT |
| MFLoadFinger | MF_LOAD_FINGER |
| MFOrgzSiaga | MF_ORGZ_SIAGA |
| MFPot | MF_POT |
| MFPotongan | MF_POTONGAN |
| MFPriorityTransaksi | MF_PRIORITY_TRANSAKSI |
| MFSatuan | MF_SATUAN |
| MFShift | MF_SHIFT |
| MFStatus | MF_STATUS |
| MFSU | MF_SU |
| MFSubGroupJabatan | MF_SUB_GROUP_JABATAN |
| MFTimSiaga | MF_TIM_SIAGA |
| MFTimSiagaAnggota | MF_TIM_SIAGA_ANGGOTA |
| MFTR | MF_TR |
| MFTunjangan | MF_TUNJANGAN |
| MFTypeSprin | mf_type_sprin |
| MFUnitKerja | MF_UNIT_KERJA |
| MFUnsurKegiatan | MF_UNSUR_KEGIATAN |
| MonitoringApp | MONITORING_APP |
| Otorisasi | OTORISASI |
| OtorisasiHistory | OTORISASI_HISTORY |
| Pegawai | PEGAWAI |
| PegMutasiUnit | PEG_MUTASI_UNIT |
| PerubahanJabatan | PERUBAHAN_JABATAN |
| Saran | SARAN |
| SKPPegawai | SKP_PEGAWAI |
| SKPPegawaiHead | SKP_PEGAWAI_HEAD |
| SPrinHeader | SPRIN_HEADER |
| TimeRecorder | TIME_RECORDER |
| UserAccount | USER_ACCOUNT |

## 6. Migration Stages

### Stage A — Restore

Restore the operator-uploaded MSSQL backup into an isolated SQL Server database.

Do not restore directly over the production/source database.

### Stage B — Inspect

Read:

- table list
- column count/order
- primary keys
- unique keys where applicable
- source row counts
- target row counts
- date columns that can support a requested date range

### Stage C — Record-Level Matching

For each mapped table, determine the actual record identity.

Preferred order:

1. matching primary key
2. matching unique key
3. explicit business key agreed for that table
4. deterministic composite key when required

Do not use a blind whole-row comparison as the universal identity rule.

### Stage D — Date Filtering

The future operator page must allow a date range.

The migration engine must identify the correct date field(s) per table before applying the date filter.

A date filter must not be applied blindly to every table because not every table necessarily has the same temporal field.

### Stage E — Dry Run

Show the operator:

- source database
- target database
- selected date range
- source rows in range
- existing matching rows
- new rows to insert
- rows skipped
- tables requiring special handling
- validation/errors

No target data changes occur during dry run.

### Stage F — Import

After explicit operator confirmation:

- insert only missing records
- preserve existing target data
- use transaction/batch processing where practical
- record inserted/skipped/error counts
- produce an audit log

### Stage G — Validation

After import:

- compare expected vs inserted counts
- verify no duplicate keys were introduced
- verify source/target integrity
- store an import history record

## 7. Future HRIS Reborn Operator Page

Planned menu/page for HRIS operators:

**Menu:** HRIS 2013 / Import Backup MSSQL

Operator workflow:

1. Upload `.bak`
2. System validates the backup
3. System restores it into an isolated temporary SQL Server database
4. System reads available tables and date ranges
5. Operator selects **Tanggal Mulai**
6. Operator selects **Tanggal Akhir**
7. System performs dry-run analysis
8. Operator reviews the migration summary
9. Operator confirms **IMPORT**
10. System merges missing records into MariaDB `HRIS`
11. System displays import result and audit history

The page must use the **Global UI Standard HRIS Reborn**, including:

`app/static/css/hris-ui.css`

The operator page should not require manual SQL Server commands.

## 8. Future Backend Requirements

The application should eventually expose a controlled migration service rather than executing arbitrary SQL from the browser.

Required controls:

- upload size/type validation
- isolated restore database name per job
- job status/progress
- date-range validation
- table mapping configuration
- record matching rules
- dry-run before import
- explicit confirmation before write
- audit trail
- cleanup of temporary restore database/files
- protection against concurrent destructive jobs
- no storage of database passwords in Git
- no `.bak` files committed to Git

## 9. Current Working Files

Infrastructure migration scripts are currently being developed in:

`/opt/sqlserver-migration/hris/`

The temporary scripts created during troubleshooting include:

- `migrate_reborn_dry_run.sh`
- `migrate_hris_2013_to_reborn.sh`

These are working-area scripts. The application repository should contain the reusable migration design/documentation and, once finalized, the application implementation.

## 10. Current Checkpoint

As of 2026-10-02:

- [x] MSSQL backup copied to HRIS-DB
- [x] Backup verified with FILELISTONLY
- [x] Backup restored to `HRIS_2013_BACKUP`
- [x] Restore verified ONLINE
- [x] 59 source tables verified
- [x] 58 application tables identified for migration
- [x] MariaDB `HRIS` connection verified
- [x] Source/target structure checks started
- [x] `Absensi` source/target row counts observed
- [ ] Complete 58-table record-level migration analysis
- [ ] Define per-table matching keys
- [ ] Build safe MERGE/INSERT engine
- [ ] Execute first controlled migration
- [ ] Validate migrated data
- [ ] Build operator upload/date-range page
- [ ] Add migration history/audit UI
- [ ] Add cleanup and safety controls

## 11. Critical Security Note

The SQL Server SA credential used during this development session is a temporary credential. It must not be committed to GitHub, application source, documentation, or logs. Rotate the credential after migration development/testing is complete.

## 12. Next Immediate Step

Continue from the verified direct `docker exec -e SQLCMDPASSWORD` connection method and build a **clean 58-table analysis engine**.

Do not start the operator page yet. Complete and validate the migration engine first.
