/* MariaDB-compatible fixed script generated from basarnas_db_3.sql */
SET FOREIGN_KEY_CHECKS = 0;

/*==============================================================*/
/* DBMS name:      Sybase SQL Anywhere 12                       */
/* Created on:     14/04/2026 13:43:17                          */
/*==============================================================*/


drop table if exists ABSENSI;

drop table if exists ABSENSI_BACKUP;

drop table if exists ABSENSI_TEMP;

drop table if exists BUKU_HARIAN_HEAD;

drop table if exists DINAS_LUAR;

drop table if exists DRH;

drop table if exists HAK_AKSES_FORM;

drop table if exists HAK_AKSES_TYPE_SPRIN;

drop table if exists KALENDER;

drop table if exists LEMBUR;

drop table if exists LOG_ACTIVITIY;

drop table if exists LOG_ACTIVITIY_BACKUP;

drop table if exists LOG_TRANSAKSI;

drop table if exists LOG_TRANSAKSI_BACKUP;

drop table if exists MEDIA_INFORMASI;

drop table if exists MF_CLASS;

drop table if exists MF_CONFIG;

drop table if exists MF_EMAIL_SEND;

drop table if exists MF_ESELON;

drop table if exists MF_FIELD_CARI;

drop table if exists MF_FORM;

drop table if exists MF_FORM_NEW;

drop table if exists MF_GOL;

drop table if exists MF_GROUP_JABATAN;

drop table if exists MF_HOST_NAME_FP;

drop table if exists MF_JABATAN;

drop table if exists MF_JABATAN_KEGIATAN;

drop table if exists MF_JAM_KERJA;

drop table if exists MF_JOBLIST;

drop table if exists MF_KLASIFIKASI_SURAT;

drop table if exists MF_LOAD_FINGER;

drop table if exists MF_ORGZ_SIAGA;

drop table if exists MF_POT;

drop table if exists MF_POTONGAN;

drop table if exists MF_PRIORITY_TRANSAKSI;

drop table if exists MF_SATUAN;

drop table if exists MF_SHIFT;

drop table if exists MF_STATUS;

drop table if exists MF_SU;

drop table if exists MF_TIM_SIAGA;

drop table if exists MF_TIM_SIAGA_ANGGOTA;

drop table if exists MF_TR;

drop table if exists MF_TUNJANGAN;

drop table if exists MF_TYPE_SPRIN;

drop table if exists MF_UNIT_KERJA;

drop table if exists MF_UNSUR_KEGIATAN;

drop table if exists MF_SUB_GROUP_JABATAN;

drop table if exists MONITORING_APP;

drop table if exists OTORISASI;

drop table if exists OTORISASI_HISTORY;

drop table if exists PEGAWAI;

drop table if exists PEG_MUTASI_UNIT;

drop table if exists PERUBAHAN_JABATAN;

drop table if exists SARAN;

drop table if exists SKP_PEGAWAI;

drop table if exists SKP_PEGAWAI_HEAD;

drop table if exists SPRIN_HEADER;

drop table if exists TIME_RECORDER;

drop table if exists USER_ACCOUNT;

/*==============================================================*/
/* Table: ABSENSI                                               */
/*==============================================================*/
create table ABSENSI 
(
   ABSENSI_ID           integer                        not null,
   POTONGAN_ID          integer                        not null,
   TGL_KERJA            timestamp                      not null,
   ABSENSI_BACKUP_ID    integer                        not null,
   ABSENSI_TEMP_ID      integer                        not null,
   FINGER_ID            integer                        not null,
   TGL_JAM_IN           timestamp                      null,
   TGL_JAM_OUT          timestamp                      null,
   KET_IN               varchar(850)                   null,
   TRANSAKSI_IN         char(50)                       null,
   UPDATE_IN_BY         varchar(50)                    null,
   UPDATE_IN_DATE       timestamp                      null,
   KET_OUT              varchar(850)                   null,
   TRANSAKSI_OUT        varchar(50)                    null,
   UPDATE_OUT_BY        varchar(50)                    null,
   UPDATE_OUT_DATE      timestamp                      null,
   TINGKAT_TLM          varchar(50)                    null,
   TOTAL_TLM            float                          null,
   TOTAL_PSW            float                          null,
   TINGKAT_PSW          varchar(50)                    null,
   IS_INVALID           varchar(1)                     null,
   IS_OUTVALID          varchar(1)                     null,
   AWAL_TLM             float                          null,
   PERSEN_POT_TLM       float                          null,
   PERSEN_POT_PSW       float                          null,
   TGL_JAM_BAKU_IN      timestamp                      null,
   TGL_JAM_BAKU_OUT     timestamp                      null,
   TRAKSAKSI_ID_FROM    varchar(250)                   null,
   PENDUKUNG_IN         varchar(50)                    null,
   PENDUKUNG_OUT        varchar(50)                    null,
   HISTORY_TRANSAKSI_IN varchar(450)                   null,
   HISTORY_TRANSAKSI_OUT varchar(450)                   null,
   STATUS_UM            integer                        null,
   constraint PK_ABSENSI primary key (ABSENSI_ID)
);

/*==============================================================*/
/* Index: ABSENSI_PK                                            */
/*==============================================================*/
create unique index ABSENSI_PK on ABSENSI (
ABSENSI_ID ASC
);

/*==============================================================*/
/* Index: MENJADI_SUMBER_DATA_FK                                */
/*==============================================================*/
create index MENJADI_SUMBER_DATA_FK on ABSENSI (
FINGER_ID ASC
);

/*==============================================================*/
/* Index: TERJADI_PADA_TANGGAL_FK                               */
/*==============================================================*/
create index TERJADI_PADA_TANGGAL_FK on ABSENSI (
TGL_KERJA ASC
);

/*==============================================================*/
/* Index: DITERAPKAN_PADA_FK                                    */
/*==============================================================*/
create index DITERAPKAN_PADA_FK on ABSENSI (
POTONGAN_ID ASC
);

/*==============================================================*/
/* Index: DATA_BACKUP_ABSENSI_FK                                */
/*==============================================================*/
create index DATA_BACKUP_ABSENSI_FK on ABSENSI (
ABSENSI_BACKUP_ID ASC
);

/*==============================================================*/
/* Index: DATA_TEMP_ABSENSI_FK                                  */
/*==============================================================*/
create index DATA_TEMP_ABSENSI_FK on ABSENSI (
ABSENSI_TEMP_ID ASC
);

/*==============================================================*/
/* Table: ABSENSI_BACKUP                                        */
/*==============================================================*/
create table ABSENSI_BACKUP 
(
   ABSENSI_BACKUP_ID    integer                        not null,
   ABSENSI_ID           integer                        null,
   TGL_JAM_IN           timestamp                      null,
   TGL_JAM_OUT          timestamp                      null,
   KET_IN               varchar(850)                   null,
   TRANSAKSI_IN         char(50)                       null,
   UPDATE_IN_BY         varchar(50)                    null,
   UPDATE_IN_DATE       timestamp                      null,
   KET_OUT              varchar(850)                   null,
   TRANSAKSI_OUT        varchar(50)                    null,
   UPDATE_OUT_BY        varchar(50)                    null,
   UPDATE_OUT_DATE      timestamp                      null,
   TINGKAT_TLM          varchar(50)                    null,
   TOTAL_TLM            float                          null,
   TOTAL_PSW            float                          null,
   TINGKAT_PSW          varchar(50)                    null,
   IS_INVALID           varchar(1)                     null,
   IS_OUTVALID          varchar(1)                     null,
   AWAL_TLM             float                          null,
   PERSEN_POT_TLM       float                          null,
   PERSEN_POT_PSW       float                          null,
   TGL_JAM_BAKU_IN      timestamp                      null,
   TGL_JAM_BAKU_OUT     timestamp                      null,
   TRAKSAKSI_ID_FROM    varchar(250)                   null,
   PENDUKUNG_IN         varchar(50)                    null,
   PENDUKUNG_OUT        varchar(50)                    null,
   HISTORY_TRANSAKSI_IN varchar(450)                   null,
   HISTORY_TRANSAKSI_OUT varchar(450)                   null,
   STATUS_UM            integer                        null,
   constraint PK_ABSENSI_BACKUP primary key (ABSENSI_BACKUP_ID)
);

/*==============================================================*/
/* Index: ABSENSI_BACKUP_PK                                     */
/*==============================================================*/
create unique index ABSENSI_BACKUP_PK on ABSENSI_BACKUP (
ABSENSI_BACKUP_ID ASC
);

/*==============================================================*/
/* Index: DATA_BACKUP_ABSENSI2_FK                               */
/*==============================================================*/
create index DATA_BACKUP_ABSENSI2_FK on ABSENSI_BACKUP (
ABSENSI_ID ASC
);

/*==============================================================*/
/* Table: ABSENSI_TEMP                                          */
/*==============================================================*/
create table ABSENSI_TEMP 
(
   ABSENSI_TEMP_ID      integer                        not null,
   ABSENSI_ID           integer                        null,
   TGL_JAM_IN           timestamp                      null,
   TGL_JAM_OUT          timestamp                      null,
   KET_IN               varchar(850)                   null,
   TRANSAKSI_IN         char(50)                       null,
   UPDATE_IN_BY         varchar(50)                    null,
   UPDATE_IN_DATE       timestamp                      null,
   KET_OUT              varchar(850)                   null,
   TRANSAKSI_OUT        varchar(50)                    null,
   UPDATE_OUT_BY        varchar(50)                    null,
   UPDATE_OUT_DATE      timestamp                      null,
   TINGKAT_TLM          varchar(50)                    null,
   TOTAL_TLM            float                          null,
   TOTAL_PSW            float                          null,
   TINGKAT_PSW          varchar(50)                    null,
   IS_INVALID           varchar(1)                     null,
   IS_OUTVALID          varchar(1)                     null,
   AWAL_TLM             float                          null,
   PERSEN_POT_TLM       float                          null,
   PERSEN_POT_PSW       float                          null,
   TGL_JAM_BAKU_IN      timestamp                      null,
   TGL_JAM_BAKU_OUT     timestamp                      null,
   TRAKSAKSI_ID_FROM    varchar(250)                   null,
   PENDUKUNG_IN         varchar(50)                    null,
   PENDUKUNG_OUT        varchar(50)                    null,
   HISTORY_TRANSAKSI_IN varchar(450)                   null,
   HISTORY_TRANSAKSI_OUT varchar(450)                   null,
   STATUS_UM            integer                        null,
   constraint PK_ABSENSI_TEMP primary key (ABSENSI_TEMP_ID)
);

/*==============================================================*/
/* Index: ABSENSI_TEMP_PK                                       */
/*==============================================================*/
create unique index ABSENSI_TEMP_PK on ABSENSI_TEMP (
ABSENSI_TEMP_ID ASC
);

/*==============================================================*/
/* Index: DATA_TEMP_ABSENSI2_FK                                 */
/*==============================================================*/
create index DATA_TEMP_ABSENSI2_FK on ABSENSI_TEMP (
ABSENSI_ID ASC
);

/*==============================================================*/
/* Table: BUKU_HARIAN_HEAD                                      */
/*==============================================================*/
create table BUKU_HARIAN_HEAD 
(
   GUID                 varchar(100)                   not null,
   JABATAN_ID           integer                        not null,
   NIP                  varchar(50)                    not null,
   ITEM_ID              varchar(50)                    not null,
   GUID_SKP_PEG         varchar(100)                   not null,
   DESKRIPSI            varchar(350)                   null,
   AK                   float                          null,
   QTY                  float                          null,
   GOL                  varchar(10)                    null,
   GOL_PARENT           varchar(10)                    null,
   BIAYA                float                          null,
   UNSUR                varchar(50)                    null,
   TGL_MULAI            date                           null,
   SATUAN_QTY           varchar(50)                    null,
   KETERANGAN           varchar(350)                   null,
   UPDATE_DATE          timestamp                      null,
   CREATE_DATE          timestamp                      null,
   NIP_PARENT           varchar(50)                    null,
   JABATAN_ID_PARENT    integer                        null,
   STATUS               integer                        null,
   KETERANGAN_PENGAJUAN varchar(150)                   null,
   constraint PK_BUKU_HARIAN_HEAD primary key (GUID)
);

/*==============================================================*/
/* Index: BUKU_HARIAN_HEAD_PK                                   */
/*==============================================================*/
create unique index BUKU_HARIAN_HEAD_PK on BUKU_HARIAN_HEAD (
GUID ASC
);

/*==============================================================*/
/* Index: DIBUAT_OLEH_FK                                        */
/*==============================================================*/
create index DIBUAT_OLEH_FK on BUKU_HARIAN_HEAD (
NIP ASC
);

/*==============================================================*/
/* Index: TERKAIT_JABATAN_FK                                    */
/*==============================================================*/
create index TERKAIT_JABATAN_FK on BUKU_HARIAN_HEAD (
JABATAN_ID ASC
);

/*==============================================================*/
/* Index: TERKAIT_JABATAN_KEGIATAN_FK                           */
/*==============================================================*/
create index TERKAIT_JABATAN_KEGIATAN_FK on BUKU_HARIAN_HEAD (
ITEM_ID ASC
);

/*==============================================================*/
/* Index: TERKAIT_DENGAN_FK                                     */
/*==============================================================*/
create index TERKAIT_DENGAN_FK on BUKU_HARIAN_HEAD (
GUID_SKP_PEG ASC
);

/*==============================================================*/
/* Table: DINAS_LUAR                                            */
/*==============================================================*/
create table DINAS_LUAR 
(
   DINAS_TRANSAKSI_ID   varchar(50)                    not null,
   GUID_SPRIN           varchar(50)                    not null,
   NIP                  varchar(50)                    not null,
   TGL_AWAL_DINAS_LUAR  timestamp                      null,
   TGL_AKHIR_DINAS_LUAR timestamp                      null,
   KETERANGAN_DINAS_LUAR varchar(450)                   null,
   PENEMPATAN_DINAS_LUAR varchar(350)                   null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   TRANSAKSI            varchar(50)                    null,
   PENDUKUNG            varchar(50)                    null,
   NO_SURAT             varchar(250)                   null,
   STATUS_UM            integer                        null,
   JENIS                varchar(10)                    null,
   TGL_AWAL_SURAT       date                           null,
   TGL_AKHIR_SURAT      date                           null,
   NAMA_FILE            varchar(100)                   null,
   TGL_EMAIL            timestamp                      null,
   TIPE                 integer                        null,
   constraint PK_DINAS_LUAR primary key (DINAS_TRANSAKSI_ID)
);

/*==============================================================*/
/* Index: DINAS_LUAR_PK                                         */
/*==============================================================*/
create unique index DINAS_LUAR_PK on DINAS_LUAR (
DINAS_TRANSAKSI_ID ASC
);

/*==============================================================*/
/* Index: BERDASARKAN_SPRIN_FK                                  */
/*==============================================================*/
create index BERDASARKAN_SPRIN_FK on DINAS_LUAR (
GUID_SPRIN ASC
);

/*==============================================================*/
/* Index: MELAKUKAN_FK                                          */
/*==============================================================*/
create index MELAKUKAN_FK on DINAS_LUAR (
NIP ASC
);

/*==============================================================*/
/* Table: DRH                                                   */
/*==============================================================*/
create table DRH 
(
   NIP                  varchar(50)                    not null,
   JABATAN_ID           integer                        not null,
   TRAKSAKSI_ID         integer                        not null,
   GUID_TRANSAKSI       varchar(50)                    null,
   TGL_MULAI            date                           null,
   NO_SK                varchar(150)                   null
);

/*==============================================================*/
/* Index: JABATAN_DRH_FK                                        */
/*==============================================================*/
create index JABATAN_DRH_FK on DRH (
JABATAN_ID ASC
);

/*==============================================================*/
/* Index: MEREKAM_DRH_FK                                        */
/*==============================================================*/
create index MEREKAM_DRH_FK on DRH (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Index: PEGAWAI_DRH_FK                                        */
/*==============================================================*/
create index PEGAWAI_DRH_FK on DRH (
NIP ASC
);

/*==============================================================*/
/* Table: HAK_AKSES_FORM                                        */
/*==============================================================*/
create table HAK_AKSES_FORM 
(
   FORM_ID              varchar(50)                    not null,
   NIP                  varchar(50)                    not null,
   IS_AKSES             varchar(5)                     null,
   TYPE_AKSES           varchar(5)                     null,
   MODUL                varchar(50)                    null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null
);

/*==============================================================*/
/* Index: DIBERIKAN_KEPADA_FK                                   */
/*==============================================================*/
create index DIBERIKAN_KEPADA_FK on HAK_AKSES_FORM (
NIP ASC
);

/*==============================================================*/
/* Index: UNTUK_FORM_FK                                         */
/*==============================================================*/
create index UNTUK_FORM_FK on HAK_AKSES_FORM (
FORM_ID ASC
);

/*==============================================================*/
/* Table: HAK_AKSES_TYPE_SPRIN                                  */
/*==============================================================*/
create table HAK_AKSES_TYPE_SPRIN 
(
   TYPE_SPRIN_ID        char(20)                       not null,
   NIP                  varchar(50)                    not null,
   TYPE_AKSES           char(10)                       null,
   UPDATE_BY            char(10)                       null,
   UPDATE_DATE          char(10)                       null
);

/*==============================================================*/
/* Index: USER_SPRIN_FK                                         */
/*==============================================================*/
create index USER_SPRIN_FK on HAK_AKSES_TYPE_SPRIN (
NIP ASC
);

/*==============================================================*/
/* Index: AKSES_SPRIN_FK                                        */
/*==============================================================*/
create index AKSES_SPRIN_FK on HAK_AKSES_TYPE_SPRIN (
TYPE_SPRIN_ID ASC
);

/*==============================================================*/
/* Table: KALENDER                                              */
/*==============================================================*/
create table KALENDER 
(
   TGL_KERJA            timestamp                      not null,
   IS_LIBUR             varchar(1)                     null,
   KET                  varchar(50)                    null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   constraint PK_KALENDER primary key (TGL_KERJA)
);

/*==============================================================*/
/* Index: KALENDER_PK                                           */
/*==============================================================*/
create unique index KALENDER_PK on KALENDER (
TGL_KERJA ASC
);

/*==============================================================*/
/* Table: LEMBUR                                                */
/*==============================================================*/
create table LEMBUR 
(
   NIP                  varchar(50)                    null,
   TGL_KERJA            timestamp                      null,
   JAM_IN               timestamp                      null,
   JAM_OUT              timestamp                      null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   KETERANGAN           varchar(50)                    null,
   NO_SURAT             varchar(250)                   null,
   JAM_BAKU_IN          timestamp                      null,
   JAM_BAKU_OUT         timestamp                      null
);

/*==============================================================*/
/* Index: TERJADI_TANGGAL_LEMBUR_FK                             */
/*==============================================================*/
create index TERJADI_TANGGAL_LEMBUR_FK on LEMBUR (
TGL_KERJA ASC
);

/*==============================================================*/
/* Index: DILAKUKAN_LEMBUR_FK                                   */
/*==============================================================*/
create index DILAKUKAN_LEMBUR_FK on LEMBUR (
NIP ASC
);

/*==============================================================*/
/* Table: LOG_ACTIVITIY                                         */
/*==============================================================*/
create table LOG_ACTIVITIY 
(
   GUID_LOG             varchar(50)                    not null,
   TRAKSAKSI_ID         integer                        not null,
   UNIT_KERJA_ID        integer                        not null,
   GUID_LOG_BACKUP      varchar(50)                    not null,
   GUID_TIM             varchar(50)                    not null,
   STATUS_ID            integer                        not null,
   NIP                  varchar(50)                    not null,
   TRX                  varchar(50)                    null,
   ACTIVITY             varchar(50)                    null,
   ACTIVITY_DATE        date                           null,
   NOTE                 varchar(150)                   null,
   TEMPAT               varchar(150)                   null,
   PERIHAL              varchar(150)                   null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   FUNGSIONAL           varchar(50)                    null,
   TGL_CLOSING          date                           null,
   SHIFT_1              integer                        null,
   SHIFT_2              integer                        null,
   PENGGANTI            integer                        null,
   STATUS_TRX           varchar(50)                    null,
   KET_UPDATE           varchar(250)                   null,
   NIP_PENGGANTI        varchar(50)                    null,
   BIAYA                float                          null,
   QTY                  float                          null,
   SATUAN_QTY           varchar(50)                    null,
   SHIFT                varchar(5)                     null,
   TRANSAKSI_FORM       varchar(50)                    null,
   TGL_JAM_IN           timestamp                      null,
   TGL_JAM_OUT          timestamp                      null,
   TGL_JAM_BAKU_IN      timestamp                      null,
   TGL_JAM_BAKU_OUT     timestamp                      null,
   constraint PK_LOG_ACTIVITIY primary key (GUID_LOG)
);

/*==============================================================*/
/* Index: LOG_ACTIVITIY_PK                                      */
/*==============================================================*/
create unique index LOG_ACTIVITIY_PK on LOG_ACTIVITIY (
GUID_LOG ASC
);

/*==============================================================*/
/* Index: DILAKUKAN_OLEH_USER_FK                                */
/*==============================================================*/
create index DILAKUKAN_OLEH_USER_FK on LOG_ACTIVITIY (
NIP ASC
);

/*==============================================================*/
/* Index: MEMILIKI_STATUS_FK                                    */
/*==============================================================*/
create index MEMILIKI_STATUS_FK on LOG_ACTIVITIY (
STATUS_ID ASC
);

/*==============================================================*/
/* Index: DILAKUKAN_TIM_FK                                      */
/*==============================================================*/
create index DILAKUKAN_TIM_FK on LOG_ACTIVITIY (
GUID_TIM ASC
);

/*==============================================================*/
/* Index: UNIT_MELAKUKAN_FK                                     */
/*==============================================================*/
create index UNIT_MELAKUKAN_FK on LOG_ACTIVITIY (
UNIT_KERJA_ID ASC
);

/*==============================================================*/
/* Index: TRANSAKSI_TEREKAM_FK                                  */
/*==============================================================*/
create index TRANSAKSI_TEREKAM_FK on LOG_ACTIVITIY (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Index: MEMBACKUP_LOG_ACTIVITIY_FK                            */
/*==============================================================*/
create index MEMBACKUP_LOG_ACTIVITIY_FK on LOG_ACTIVITIY (
GUID_LOG_BACKUP ASC
);

/*==============================================================*/
/* Table: LOG_ACTIVITIY_BACKUP                                  */
/*==============================================================*/
create table LOG_ACTIVITIY_BACKUP 
(
   GUID_LOG_BACKUP      varchar(50)                    not null,
   GUID_LOG             varchar(50)                    null,
   TRX                  varchar(50)                    null,
   ACTIVITY             varchar(50)                    null,
   ACTIVITY_DATE        date                           null,
   NOTE                 varchar(150)                   null,
   TEMPAT               varchar(150)                   null,
   PERIHAL              varchar(150)                   null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   FUNGSIONAL           varchar(50)                    null,
   TGL_CLOSING          date                           null,
   SHIFT_1              integer                        null,
   SHIFT_2              integer                        null,
   PENGGANTI            integer                        null,
   STATUS_TRX           varchar(50)                    null,
   KET_UPDATE           varchar(250)                   null,
   NIP_PENGGANTI        varchar(50)                    null,
   BIAYA                float                          null,
   QTY                  float                          null,
   SATUAN_QTY           varchar(50)                    null,
   SHIFT                varchar(5)                     null,
   TRANSAKSI_FORM       varchar(50)                    null,
   TGL_JAM_IN           timestamp                      null,
   TGL_JAM_OUT          timestamp                      null,
   TGL_JAM_BAKU_IN      timestamp                      null,
   TGL_JAM_BAKU_OUT     timestamp                      null,
   constraint PK_LOG_ACTIVITIY_BACKUP primary key (GUID_LOG_BACKUP)
);

/*==============================================================*/
/* Index: LOG_ACTIVITIY_BACKUP_PK                               */
/*==============================================================*/
create unique index LOG_ACTIVITIY_BACKUP_PK on LOG_ACTIVITIY_BACKUP (
GUID_LOG_BACKUP ASC
);

/*==============================================================*/
/* Index: MEMBACKUP_LOG_ACTIVITIY2_FK                           */
/*==============================================================*/
create index MEMBACKUP_LOG_ACTIVITIY2_FK on LOG_ACTIVITIY_BACKUP (
GUID_LOG ASC
);

/*==============================================================*/
/* Table: LOG_TRANSAKSI                                         */
/*==============================================================*/
create table LOG_TRANSAKSI 
(
   TRAKSAKSI_ID         integer                        not null,
   NIP                  varchar(50)                    not null,
   TRAKSAKSI_BACKUP_ID  integer                        not null,
   GUID_SKP_PEG         varchar(100)                   null,
   TRANSAKSI            varchar(50)                    null,
   ACTIVITY             varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   constraint PK_LOG_TRANSAKSI primary key (TRAKSAKSI_ID)
);

/*==============================================================*/
/* Index: LOG_TRANSAKSI_PK                                      */
/*==============================================================*/
create unique index LOG_TRANSAKSI_PK on LOG_TRANSAKSI (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Index: TRANSAKSI_DILAKUKAN_OLEH_FK                           */
/*==============================================================*/
create index TRANSAKSI_DILAKUKAN_OLEH_FK on LOG_TRANSAKSI (
NIP ASC
);

/*==============================================================*/
/* Index: DATA_BACKUP_TRANSAKSI_FK                              */
/*==============================================================*/
create index DATA_BACKUP_TRANSAKSI_FK on LOG_TRANSAKSI (
TRAKSAKSI_BACKUP_ID ASC
);

/*==============================================================*/
/* Table: LOG_TRANSAKSI_BACKUP                                  */
/*==============================================================*/
create table LOG_TRANSAKSI_BACKUP 
(
   TRAKSAKSI_BACKUP_ID  integer                        not null,
   TRAKSAKSI_ID         integer                        null,
   GUID_SKP_PEG         varchar(100)                   null,
   TRANSAKSI            varchar(50)                    null,
   ACTIVITY             varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   constraint PK_LOG_TRANSAKSI_BACKUP primary key (TRAKSAKSI_BACKUP_ID)
);

/*==============================================================*/
/* Index: LOG_TRANSAKSI_BACKUP_PK                               */
/*==============================================================*/
create unique index LOG_TRANSAKSI_BACKUP_PK on LOG_TRANSAKSI_BACKUP (
TRAKSAKSI_BACKUP_ID ASC
);

/*==============================================================*/
/* Index: DATA_BACKUP_TRANSAKSI2_FK                             */
/*==============================================================*/
create index DATA_BACKUP_TRANSAKSI2_FK on LOG_TRANSAKSI_BACKUP (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Table: MEDIA_INFORMASI                                       */
/*==============================================================*/
create table MEDIA_INFORMASI 
(
   MED_INFOR_ID         integer                        not null,
   UPDATE_DATE          timestamp                      null,
   UPDATE_BY            varchar(50)                    null,
   TRX                  varchar(50)                    null,
   NAMA_FILE            varchar(100)                   null,
   DESKRIPSI            varchar(250)                   null,
   PUBLISH_DATE_START   date                           null,
   PUBLISH_DATE_END     date                           null,
   IS_AKTIF             varchar(5)                     null,
   PIC                  varchar(150)                   null,
   ALAMAT               varchar(250)                   null,
   constraint PK_MEDIA_INFORMASI primary key (MED_INFOR_ID)
);

/*==============================================================*/
/* Index: MEDIA_INFORMASI_PK                                    */
/*==============================================================*/
create unique index MEDIA_INFORMASI_PK on MEDIA_INFORMASI (
MED_INFOR_ID ASC
);

/*==============================================================*/
/* Table: MF_CLASS                                              */
/*==============================================================*/
create table MF_CLASS 
(
   CLASS_ID             integer                        not null,
   TUNJANGAN            float                          null,
   ID                   integer                        null,
   TGL_MULAI            timestamp                      null,
   UPDATE_IN_BY         varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   DOKREFF              varchar(250)                   null,
   constraint PK_MF_CLASS primary key (CLASS_ID)
);

/*==============================================================*/
/* Index: MF_CLASS_PK                                           */
/*==============================================================*/
create unique index MF_CLASS_PK on MF_CLASS (
CLASS_ID ASC
);

/*==============================================================*/
/* Table: MF_CONFIG                                             */
/*==============================================================*/
create table MF_CONFIG 
(
   TRAKSAKSI_ID         integer                        not null,
   CONFIG_NAME          varchar(50)                    null,
   TGL_JAM1             timestamp                      null,
   TGL_JAM2             timestamp                      null
);

/*==============================================================*/
/* Index: MENCATAT_CONFIG_FK                                    */
/*==============================================================*/
create index MENCATAT_CONFIG_FK on MF_CONFIG (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Table: MF_EMAIL_SEND                                         */
/*==============================================================*/
create table MF_EMAIL_SEND 
(
   EMAIL_SEND           varchar(50)                    null,
   PASS_SEND            varchar(50)                    null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   SMTP_SEND            varchar(50)                    null,
   PORT_SENT            varchar(10)                    null
);

/*==============================================================*/
/* Table: MF_ESELON                                             */
/*==============================================================*/
create table MF_ESELON 
(
   ESELON               varchar(50)                    not null,
   URUT_ESELON          integer                        null,
   constraint PK_MF_ESELON primary key (ESELON)
);

/*==============================================================*/
/* Index: MF_ESELON_PK                                          */
/*==============================================================*/
create unique index MF_ESELON_PK on MF_ESELON (
ESELON ASC
);

/*==============================================================*/
/* Table: MF_FIELD_CARI                                         */
/*==============================================================*/
create table MF_FIELD_CARI 
(
   FIELD_ID             varchar(50)                    not null,
   TRAKSAKSI_ID         integer                        not null,
   FIELD_NAME           varchar(50)                    null,
   TYPE_CARI            varchar(50)                    null,
   IS_CMB               varchar(5)                     null,
   NO_URUT              integer                        null,
   APLIKASI             varchar(50)                    null,
   constraint PK_MF_FIELD_CARI primary key (FIELD_ID)
);

/*==============================================================*/
/* Index: MF_FIELD_CARI_PK                                      */
/*==============================================================*/
create unique index MF_FIELD_CARI_PK on MF_FIELD_CARI (
FIELD_ID ASC
);

/*==============================================================*/
/* Index: MENCATAT_PENCARIAN_FK                                 */
/*==============================================================*/
create index MENCATAT_PENCARIAN_FK on MF_FIELD_CARI (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Table: MF_FORM                                               */
/*==============================================================*/
create table MF_FORM 
(
   FORM_ID              varchar(50)                    not null,
   FORM_NAME            varchar(70)                    null,
   FORM_TYPE            varchar(20)                    null,
   NO_URUT              integer                        null,
   BERKAS               varchar(50)                    null,
   PANEL_PAGE           varchar(50)                    null,
   IMG_URL              varchar(50)                    null,
   NO_URUT_PANEL        integer                        null,
   MODUL                varchar(50)                    null,
   PARENT_FORM          varchar(50)                    null,
   MODEL                integer                        null,
   ICON_FA              varchar(50)                    null,
   HIRARKI_LV           integer                        null,
   TRANSAKSI_ID         integer                        null,
   constraint PK_MF_FORM primary key (FORM_ID)
);

/*==============================================================*/
/* Index: MF_FORM_PK                                            */
/*==============================================================*/
create unique index MF_FORM_PK on MF_FORM (
FORM_ID ASC
);

/*==============================================================*/
/* Table: MF_FORM_NEW                                           */
/*==============================================================*/
create table MF_FORM_NEW 
(
   NEW_FORM_ID          varchar(50)                    not null,
   NEW_FORM_NAME        varchar(70)                    null,
   NEW_FORM_TYPE        varchar(20)                    null,
   NO_URUT              integer                        null,
   BERKAS               varchar(50)                    null,
   PANEL_PAGE           varchar(50)                    null,
   IMG_URL              varchar(50)                    null,
   NO_URUT_PANEL        integer                        null,
   MODUL                varchar(50)                    null,
   PARENT_FORM          varchar(50)                    null,
   MODEL                integer                        null,
   ICONFA               varchar(50)                    null,
   HIRARKI_LV           integer                        null,
   constraint PK_MF_FORM_NEW primary key (NEW_FORM_ID)
);

/*==============================================================*/
/* Index: MF_FORM_NEW_PK                                        */
/*==============================================================*/
create unique index MF_FORM_NEW_PK on MF_FORM_NEW (
NEW_FORM_ID ASC
);

/*==============================================================*/
/* Table: MF_GOL                                                */
/*==============================================================*/
create table MF_GOL 
(
   GOL_ID               integer                        not null,
   NAMA_GOL             varchar(50)                    null,
   PANGKAT_GOL          varchar(50)                    null,
   URUT_GOL             integer                        null,
   TRANSAC_ID           integer                        null,
   GROUP_GOL            varchar(2)                     null,
   constraint PK_MF_GOL primary key (GOL_ID)
);

/*==============================================================*/
/* Index: MF_GOL_PK                                             */
/*==============================================================*/
create unique index MF_GOL_PK on MF_GOL (
GOL_ID ASC
);

/*==============================================================*/
/* Table: MF_GROUP_JABATAN                                      */
/*==============================================================*/
create table MF_GROUP_JABATAN 
(
   GROUP_JABATAN_ID     integer                        not null,
   NAMA_GROUP_JABATAN   varchar(50)                    not null,
   constraint PK_MF_GROUP_JABATAN primary key (GROUP_JABATAN_ID)
);

/*==============================================================*/
/* Index: MF_GROUP_JABATAN_PK                                   */
/*==============================================================*/
create unique index MF_GROUP_JABATAN_PK on MF_GROUP_JABATAN (
GROUP_JABATAN_ID ASC
);

/*==============================================================*/
/* Table: MF_HOST_NAME_FP                                       */
/*==============================================================*/
create table MF_HOST_NAME_FP 
(
   UNIT_KERJA_ID        integer                        not null,
   HOST_NAME_FP         varchar(50)                    null
);

/*==============================================================*/
/* Index: HOST_DARI_UNIT_FK                                     */
/*==============================================================*/
create index HOST_DARI_UNIT_FK on MF_HOST_NAME_FP (
UNIT_KERJA_ID ASC
);

/*==============================================================*/
/* Table: MF_JABATAN                                            */
/*==============================================================*/
create table MF_JABATAN 
(
   JABATAN_ID           integer                        not null,
   JABATAN_ID_BARU      integer                        not null,
   GROUP_JABATAN_ID     integer                        not null,
   SUB_GROUP_JABATAN_ID integer                        not null,
   JABATAN_MANAGE       integer                        null,
   JABATAN_ID_OLD       integer                        null,
   NAMA_JABATAN         varchar(100)                   not null,
   URUT_JABATAN         integer                        not null,
   TYPE_JABATAN         varchar(10)                    not null,
   IS_USE               smallint                       not null,
   UPDATE_IN_BY         varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   constraint PK_MF_JABATAN primary key (JABATAN_ID)
);

/*==============================================================*/
/* Index: MF_JABATAN_PK                                         */
/*==============================================================*/
create unique index MF_JABATAN_PK on MF_JABATAN (
JABATAN_ID ASC
);

/*==============================================================*/
/* Index: TERMASUK_DALAM_GROUP_FK                               */
/*==============================================================*/
create index TERMASUK_DALAM_GROUP_FK on MF_JABATAN (
GROUP_JABATAN_ID ASC
);

/*==============================================================*/
/* Index: TERMASUK_DALAM_SUBGROUP_FK                            */
/*==============================================================*/
create index TERMASUK_DALAM_SUBGROUP_FK on MF_JABATAN (
SUB_GROUP_JABATAN_ID ASC
);

/*==============================================================*/
/* Index: MERUBAH_JABATAN_FK                                    */
/*==============================================================*/
create index MERUBAH_JABATAN_FK on MF_JABATAN (
JABATAN_ID_BARU ASC
);

/*==============================================================*/
/* Table: MF_JABATAN_KEGIATAN                                   */
/*==============================================================*/
create table MF_JABATAN_KEGIATAN 
(
   ITEM_ID              varchar(50)                    not null,
   JABATAN_ID           integer                        not null,
   DESKRIPSI            varchar(500)                   null,
   AK                   float                          null,
   QTY                  float                          null,
   MUTU                 float                          null,
   WAKTU                timestamp                      null,
   BIAYA                float                          null,
   TYPE                 integer                        null,
   UNSUR                varchar(50)                    null,
   SATUAN_QTY           varchar(50)                    null,
   SATUAN_MUTU          varchar(50)                    null,
   SATUAN_WAKTU         varchar(50)                    null,
   constraint PK_MF_JABATAN_KEGIATAN primary key (ITEM_ID)
);

/*==============================================================*/
/* Index: MF_JABATAN_KEGIATAN_PK                                */
/*==============================================================*/
create unique index MF_JABATAN_KEGIATAN_PK on MF_JABATAN_KEGIATAN (
ITEM_ID ASC
);

/*==============================================================*/
/* Index: DIBUAT_UNTUK_FK                                       */
/*==============================================================*/
create index DIBUAT_UNTUK_FK on MF_JABATAN_KEGIATAN (
JABATAN_ID ASC
);

/*==============================================================*/
/* Table: MF_JAM_KERJA                                          */
/*==============================================================*/
create table MF_JAM_KERJA 
(
   JAM_KERJA_ID         integer                        not null,
   STD_JAM_IN           timestamp                      null,
   STD_JAM_OUT          timestamp                      null,
   TGL_MULAI_BERLAKU    timestamp                      null,
   SHIFT                varchar(50)                    null,
   AGENDA               varchar(50)                    null,
   PENGGANTIAN_TLM1     varchar(5)                     null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   SHIFT_KERJA          varchar(2)                     null,
   constraint PK_MF_JAM_KERJA primary key (JAM_KERJA_ID)
);

/*==============================================================*/
/* Index: MF_JAM_KERJA_PK                                       */
/*==============================================================*/
create unique index MF_JAM_KERJA_PK on MF_JAM_KERJA (
JAM_KERJA_ID ASC
);

/*==============================================================*/
/* Table: MF_JOBLIST                                            */
/*==============================================================*/
create table MF_JOBLIST 
(
   GROUP_JABATAN_ID     integer                        not null,
   ITEM_ID              varchar(50)                    not null,
   DESKRIPSI            varchar(500)                   null,
   AK                   float                          null,
   QTY                  float                          null,
   MUTU                 float                          null,
   WAKTU                timestamp                      null,
   BIAYA                float                          null,
   constraint PK_MF_JOBLIST primary key (GROUP_JABATAN_ID, ITEM_ID)
);

/*==============================================================*/
/* Index: MF_JOBLIST_PK                                         */
/*==============================================================*/
create unique index MF_JOBLIST_PK on MF_JOBLIST (
GROUP_JABATAN_ID ASC,
ITEM_ID ASC
);

/*==============================================================*/
/* Index: MEMILIKI_JOB_FK                                       */
/*==============================================================*/
create index MEMILIKI_JOB_FK on MF_JOBLIST (
GROUP_JABATAN_ID ASC
);

/*==============================================================*/
/* Index: MENGACU_KE_FK                                         */
/*==============================================================*/
create index MENGACU_KE_FK on MF_JOBLIST (
ITEM_ID ASC
);

/*==============================================================*/
/* Table: MF_KLASIFIKASI_SURAT                                  */
/*==============================================================*/
create table MF_KLASIFIKASI_SURAT 
(
   KLASIFIKASI_ID       varchar(5)                     not null,
   TYPE_SPRIN_ID        char(20)                       not null,
   KLASIFIKASI_NAME     varchar(50)                    null,
   constraint PK_MF_KLASIFIKASI_SURAT primary key (KLASIFIKASI_ID)
);

/*==============================================================*/
/* Index: MF_KLASIFIKASI_SURAT_PK                               */
/*==============================================================*/
create unique index MF_KLASIFIKASI_SURAT_PK on MF_KLASIFIKASI_SURAT (
KLASIFIKASI_ID ASC
);

/*==============================================================*/
/* Index: MENGAKLSIFIKASI_SURAT_FK                              */
/*==============================================================*/
create index MENGAKLSIFIKASI_SURAT_FK on MF_KLASIFIKASI_SURAT (
TYPE_SPRIN_ID ASC
);

/*==============================================================*/
/* Table: MF_LOAD_FINGER                                        */
/*==============================================================*/
create table MF_LOAD_FINGER 
(
   TRAKSAKSI_ID         integer                        not null,
   START_FINGER         timestamp                      null,
   END_FINGER           timestamp                      null,
   TGL_MULAI_BERLAKU    date                           null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   SHIFT_KERJA          varchar(2)                     null,
   START_FINGER_OUT     timestamp                      null,
   END_FINGER_OUT       timestamp                      null
);

/*==============================================================*/
/* Index: MENCATAT_FINGER_FK                                    */
/*==============================================================*/
create index MENCATAT_FINGER_FK on MF_LOAD_FINGER (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Table: MF_ORGZ_SIAGA                                         */
/*==============================================================*/
create table MF_ORGZ_SIAGA 
(
   ORGZ_SIAGA_ID        integer                        not null,
   FUNGSIONAL           varchar(50)                    null,
   PARENT_ID            integer                        null,
   URUT_FUNGSIONAL      float                          null,
   DESKRIPSI            varchar(50)                    null,
   INISIAL              varchar(2)                     null,
   FLAG                 varchar(50)                    null,
   constraint PK_MF_ORGZ_SIAGA primary key (ORGZ_SIAGA_ID)
);

/*==============================================================*/
/* Index: MF_ORGZ_SIAGA_PK                                      */
/*==============================================================*/
create unique index MF_ORGZ_SIAGA_PK on MF_ORGZ_SIAGA (
ORGZ_SIAGA_ID ASC
);

/*==============================================================*/
/* Table: MF_POT                                                */
/*==============================================================*/
create table MF_POT 
(
   POTONGAN_ID          integer                        not null,
   KATEGORI             varchar(50)                    null,
   TINGKAT              varchar(50)                    null,
   PERSEN_POT           float                          null,
   TGL_MULAI            timestamp                      null,
   RANGE_AWAL           float                          null,
   RANGE_AKHIR          float                          null,
   NAMA_POT             varchar(50)                    null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   IS_PENDUKUNG         varchar(2)                     null,
   TINDAKAN             varchar(250)                   null,
   DURASI_POT           float                          null,
   SATUAN_DURASI        varchar(10)                    null,
   constraint PK_MF_POT primary key (POTONGAN_ID)
);

/*==============================================================*/
/* Index: MF_POT_PK                                             */
/*==============================================================*/
create unique index MF_POT_PK on MF_POT (
POTONGAN_ID ASC
);

/*==============================================================*/
/* Table: MF_POTONGAN                                           */
/*==============================================================*/
create table MF_POTONGAN 
(
   POT_ID               integer                        not null,
   KATEGORI             varchar(50)                    null,
   TINGKAT              varchar(50)                    null,
   PERSEN_POT           float                          null,
   TGL_MULAI            timestamp                      null,
   RANGE_AWAL           float                          null,
   RANGE_AKHIR          float                          null,
   NAMA_POT             varchar(50)                    null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   IS_PENDUKUNG         varchar(2)                     null,
   constraint PK_MF_POTONGAN primary key (POT_ID)
);

/*==============================================================*/
/* Index: MF_POTONGAN_PK                                        */
/*==============================================================*/
create unique index MF_POTONGAN_PK on MF_POTONGAN (
POT_ID ASC
);

/*==============================================================*/
/* Table: MF_PRIORITY_TRANSAKSI                                 */
/*==============================================================*/
create table MF_PRIORITY_TRANSAKSI 
(
   MODUL                varchar(50)                    null,
   PRIORITY_TRANSAKSI   integer                        null,
   TRANSAKSI            varchar(50)                    null,
   INISIAL_TRANSAKSI    varchar(5)                     null
);

/*==============================================================*/
/* Table: MF_SATUAN                                             */
/*==============================================================*/
create table MF_SATUAN 
(
   SATUAN_ID            integer                        not null,
   ACTIVITY             varchar(50)                    null,
   SATUAN               varchar(50)                    null,
   PARAMETER            varchar(50)                    null,
   URUT_SATUAN          integer                        null,
   constraint PK_MF_SATUAN primary key (SATUAN_ID)
);

/*==============================================================*/
/* Index: MF_SATUAN_PK                                          */
/*==============================================================*/
create unique index MF_SATUAN_PK on MF_SATUAN (
SATUAN_ID ASC
);

/*==============================================================*/
/* Table: MF_SHIFT                                              */
/*==============================================================*/
create table MF_SHIFT 
(
   SHIFT_ID             varchar(10)                    not null,
   TRAKSAKSI_ID         integer                        not null,
   NAMA_SHIFT           varchar(50)                    null,
   JADWAL               varchar(50)                    null,
   START_SHIFT          timestamp                      null,
   END_SHIFT            timestamp                      null,
   TGL_MULAI_BERLAKU    date                           null,
   constraint PK_MF_SHIFT primary key (SHIFT_ID)
);

/*==============================================================*/
/* Index: MF_SHIFT_PK                                           */
/*==============================================================*/
create unique index MF_SHIFT_PK on MF_SHIFT (
SHIFT_ID ASC
);

/*==============================================================*/
/* Index: MENCATAT_SHIFT_FK                                     */
/*==============================================================*/
create index MENCATAT_SHIFT_FK on MF_SHIFT (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Table: MF_STATUS                                             */
/*==============================================================*/
create table MF_STATUS 
(
   STATUS_ID            integer                        not null,
   STATUS               varchar(50)                    null,
   BG_STATUS            varchar(50)                    null,
   ALERT_STATUS         varchar(50)                    null,
   SPAN_STATUS_LOG_JOB  varchar(50)                    null,
   STATUS_LOG_JOB       varchar(50)                    null,
   constraint PK_MF_STATUS primary key (STATUS_ID)
);

/*==============================================================*/
/* Index: MF_STATUS_PK                                          */
/*==============================================================*/
create unique index MF_STATUS_PK on MF_STATUS (
STATUS_ID ASC
);

/*==============================================================*/
/* Table: MF_SU                                                 */
/*==============================================================*/
create table MF_SU 
(
   NIP                  varchar(50)                    not null,
   NAMA                 varchar(50)                    null,
   PASS                 varchar(50)                    null
);

/*==============================================================*/
/* Index: MENYIMPAN_USER_FK                                     */
/*==============================================================*/
create index MENYIMPAN_USER_FK on MF_SU (
NIP ASC
);

/*==============================================================*/
/* Table: MF_TIM_SIAGA                                          */
/*==============================================================*/
create table MF_TIM_SIAGA 
(
   GUID_TIM             varchar(50)                    not null,
   NO_URUT_TIM          integer                        null,
   NAMA_TIM             varchar(50)                    null,
   ID_UNIT_KERJA        varchar(50)                    null,
   BULAN_PERIODE        varchar(2)                     null,
   TAHUN_PERIODE        varchar(4)                     null,
   FUNGSIONAL_TIM       varchar(50)                    null,
   SHIFT                varchar(5)                     null,
   IS_AKTIF             varchar(1)                     null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   constraint PK_MF_TIM_SIAGA primary key (GUID_TIM)
);

/*==============================================================*/
/* Index: MF_TIM_SIAGA_PK                                       */
/*==============================================================*/
create unique index MF_TIM_SIAGA_PK on MF_TIM_SIAGA (
GUID_TIM ASC
);

/*==============================================================*/
/* Table: MF_TIM_SIAGA_ANGGOTA                                  */
/*==============================================================*/
create table MF_TIM_SIAGA_ANGGOTA 
(
   NIP                  varchar(50)                    not null,
   GUID_TIM             varchar(50)                    not null,
   FUNGSIONAL           varchar(50)                    null,
   IS_AKTIF             varchar(1)                     null,
   ID_UNIT_KERJA        varchar(50)                    null,
   NO_URUT              integer                        null,
   BULAN_PERIODE        varchar(2)                     null,
   TAHUN_PERIODE        varchar(4)                     null,
   SHIFT                varchar(5)                     null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null
);

/*==============================================================*/
/* Index: BERANGGOTAKAN_FK                                      */
/*==============================================================*/
create index BERANGGOTAKAN_FK on MF_TIM_SIAGA_ANGGOTA (
GUID_TIM ASC
);

/*==============================================================*/
/* Index: DIISI_OLEH_FK                                         */
/*==============================================================*/
create index DIISI_OLEH_FK on MF_TIM_SIAGA_ANGGOTA (
NIP ASC
);

/*==============================================================*/
/* Table: MF_TR                                                 */
/*==============================================================*/
create table MF_TR 
(
   TRAKSAKSI_ID         integer                        not null,
   JAM_LOAD             timestamp                      null
);

/*==============================================================*/
/* Index: MENCATAT_TR_FK                                        */
/*==============================================================*/
create index MENCATAT_TR_FK on MF_TR (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Table: MF_TUNJANGAN                                          */
/*==============================================================*/
create table MF_TUNJANGAN 
(
   TUNJANGAN_ID         integer                        not null,
   JENIS_TUNJANGAN      varchar(50)                    null,
   ACTIVITY             varchar(50)                    null,
   NOMINAL              float                          null,
   TGL_MULAI            date                           null,
   HARI_KERJA           integer                        null,
   FUNGSIONAL           varchar(50)                    null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   DOKREFF              varchar(250)                   null,
   STATUS_PEG           integer                        null,
   SHIFT                varchar(5)                     null,
   UNIT_KERJA_ID        varchar(50)                    null,
   constraint PK_MF_TUNJANGAN primary key (TUNJANGAN_ID)
);

/*==============================================================*/
/* Index: MF_TUNJANGAN_PK                                       */
/*==============================================================*/
create unique index MF_TUNJANGAN_PK on MF_TUNJANGAN (
TUNJANGAN_ID ASC
);

/*==============================================================*/
/* Table: MF_TYPE_SPRIN                                         */
/*==============================================================*/
create table MF_TYPE_SPRIN 
(
   TYPE_SPRIN_ID        char(20)                       not null,
   TYPE_SPRIN_NAME      varchar(50)                    null,
   constraint PK_MF_TYPE_SPRIN primary key (TYPE_SPRIN_ID)
);

/*==============================================================*/
/* Index: MF_TYPE_SPRIN_PK                                      */
/*==============================================================*/
create unique index MF_TYPE_SPRIN_PK on MF_TYPE_SPRIN (
TYPE_SPRIN_ID ASC
);

/*==============================================================*/
/* Table: MF_UNIT_KERJA                                         */
/*==============================================================*/
create table MF_UNIT_KERJA 
(
   UNIT_KERJA_ID        integer                        not null,
   NAMA_UNIT_KERJA      varchar(50)                    null,
   URUT_REPORT          integer                        null,
   IS_PUSAT             integer                        null,
   TRANSAC_ID           integer                        null,
   UPDATE_IN_BY         varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   constraint PK_MF_UNIT_KERJA primary key (UNIT_KERJA_ID)
);

/*==============================================================*/
/* Index: MF_UNIT_KERJA_PK                                      */
/*==============================================================*/
create unique index MF_UNIT_KERJA_PK on MF_UNIT_KERJA (
UNIT_KERJA_ID ASC
);

/*==============================================================*/
/* Table: MF_UNSUR_KEGIATAN                                     */
/*==============================================================*/
create table MF_UNSUR_KEGIATAN 
(
   UNSUR_ID             integer                        not null,
   DESKRIPSI_UNSUR      varchar(50)                    null,
   constraint PK_MF_UNSUR_KEGIATAN primary key (UNSUR_ID)
);

/*==============================================================*/
/* Index: MF_UNSUR_KEGIATAN_PK                                  */
/*==============================================================*/
create unique index MF_UNSUR_KEGIATAN_PK on MF_UNSUR_KEGIATAN (
UNSUR_ID ASC
);

/*==============================================================*/
/* Table: MF_SUB_GROUP_JABATAN                                 */
/*==============================================================*/
create table MF_SUB_GROUP_JABATAN 
(
   SUB_GROUP_JABATAN_ID integer                        not null,
   NAMA_SUB_GROUP_JABATAN varchar(150)                   not null,
   constraint PK_MF_SUB_GROUP_JABATAN primary key (SUB_GROUP_JABATAN_ID)
);

/*==============================================================*/
/* Index: MF_SUB_GROUP_JABATAN_PK                              */
/*==============================================================*/
create unique index MF_SUB_GROUP_JABATAN_PK on MF_SUB_GROUP_JABATAN (
SUB_GROUP_JABATAN_ID ASC
);

/*==============================================================*/
/* Table: MONITORING_APP                                        */
/*==============================================================*/
create table MONITORING_APP 
(
   TRAKSAKSI_ID         integer                        not null,
   APLICATION           varchar(50)                    null,
   USER_NAME            varchar(50)                    null,
   COMPUTER_IP          varchar(50)                    null,
   LOGIN_TIME           timestamp                      null,
   LOGIN_DATE           timestamp                      null,
   IS_ON                varchar(5)                     null
);

/*==============================================================*/
/* Index: MENCATAT_LOG_APP_FK                                   */
/*==============================================================*/
create index MENCATAT_LOG_APP_FK on MONITORING_APP (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Table: OTORISASI                                             */
/*==============================================================*/
create table OTORISASI 
(
   GUID_OTO             varchar(100)                   not null,
   NIP                  varchar(50)                    null,
   TRX                  varchar(50)                    null,
   LEVEL_OTO            integer                        null,
   JABATAN              varchar(100)                   null,
   ACT                  integer                        null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   PERIHAL              varchar(150)                   null,
   KETERANGAN           varchar(150)                   null,
   BULAN                integer                        null,
   TAHUN                integer                        null,
   TGL_PENGAJUAN        timestamp                      null,
   constraint PK_OTORISASI primary key (GUID_OTO)
);

/*==============================================================*/
/* Index: OTORISASI_PK                                          */
/*==============================================================*/
create unique index OTORISASI_PK on OTORISASI (
GUID_OTO ASC
);

/*==============================================================*/
/* Index: DIAJUKAN_OLEH_FK                                      */
/*==============================================================*/
create index DIAJUKAN_OLEH_FK on OTORISASI (
NIP ASC
);

/*==============================================================*/
/* Table: OTORISASI_HISTORY                                     */
/*==============================================================*/
create table OTORISASI_HISTORY 
(
   OTO_HISTORY_ID       integer                        not null,
   GUID_OTO             varchar(100)                   not null,
   NIP                  varchar(50)                    not null,
   UNIT_KERJA_ID        integer                        not null,
   TRX                  varchar(50)                    null,
   LEVEL_OTO            integer                        null,
   JABATAN              varchar(100)                   null,
   ACT                  integer                        null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   PERIHAL              varchar(150)                   null,
   KETERANGAN           varchar(150)                   null,
   BULAN                integer                        null,
   TAHUN                integer                        null,
   SHIFT_1              integer                        null,
   SHIFT_2              integer                        null,
   REC_DATE             timestamp                      null,
   TGL_PENGAJUAN        timestamp                      null,
   constraint PK_OTORISASI_HISTORY primary key (OTO_HISTORY_ID)
);

/*==============================================================*/
/* Index: OTORISASI_HISTORY_PK                                  */
/*==============================================================*/
create unique index OTORISASI_HISTORY_PK on OTORISASI_HISTORY (
OTO_HISTORY_ID ASC
);

/*==============================================================*/
/* Index: USER_OTORISASI_HISTORY_FK                             */
/*==============================================================*/
create index USER_OTORISASI_HISTORY_FK on OTORISASI_HISTORY (
NIP ASC
);

/*==============================================================*/
/* Index: OTORISASI_HISTORY_UNIT_FK                             */
/*==============================================================*/
create index OTORISASI_HISTORY_UNIT_FK on OTORISASI_HISTORY (
UNIT_KERJA_ID ASC
);

/*==============================================================*/
/* Index: OTORISASI_SEBELUMNYA_FK                               */
/*==============================================================*/
create index OTORISASI_SEBELUMNYA_FK on OTORISASI_HISTORY (
GUID_OTO ASC
);

/*==============================================================*/
/* Table: PEGAWAI                                               */
/*==============================================================*/
create table PEGAWAI 
(
   NIP                  varchar(50)                    not null,
   ABSENSI_ID           integer                        not null,
   ESELON               varchar(50)                    not null,
   TUNJANGAN_ID         integer                        not null,
   CLASS_ID             integer                        not null,
   UNIT_KERJA_ID        integer                        not null,
   JABATAN_ID           integer                        not null,
   GOL_ID               integer                        not null,
   NIP_MANAGER          varchar(50)                    null,
   NAMA                 varchar(70)                    not null,
   NO_TELP              varchar(50)                    not null,
   PANGKAT              varchar(50)                    null,
   JABATAN              varchar(50)                    null,
   MAIL                 varchar(100)                   null,
   PASS                 varchar(50)                    not null,
   ALAMAT               varchar(50)                    null,
   JENIS_KEL            varchar(15)                    null,
   TGL_LAHIR            timestamp                      null,
   KELURAHAN            varchar(50)                    null,
   KECAMATAN            varchar(50)                    null,
   KOTA                 varchar(50)                    null,
   TEMPAT_LAHIR         varchar(100)                   null,
   AGAMA                varchar(100)                   null,
   STATUS_PERKAWINAN    smallint                       null,
   NO_KTP               varchar(50)                    null,
   NO_NPWP              varchar(50)                    null,
   HOBI                 varchar(150)                   null,
   IS_VIP               smallint                       null,
   TMT_PANGKAT          timestamp                      null,
   IS_KELUAR            smallint                       null,
   TGL_KELUAR           timestamp                      null,
   ALASAN_KELUAR        varchar(250)                   null,
   TGL_MASUK            timestamp                      null,
   TMT_PNS              date                           null,
   TMT_CPNS             date                           null,
   GOL_RECRUIT          varchar(10)                    null,
   STATUS_PEG           smallint                       null,
   TMT_CLASS            date                           null,
   TMT_JABATAN          date                           null,
   UPDATE_IN_BY         varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   constraint PK_PEGAWAI primary key (NIP)
);

/*==============================================================*/
/* Index: PEGAWAI_PK                                            */
/*==============================================================*/
create unique index PEGAWAI_PK on PEGAWAI (
NIP ASC
);

/*==============================================================*/
/* Index: MENDUDUKI_JABATAN_FK                                  */
/*==============================================================*/
create index MENDUDUKI_JABATAN_FK on PEGAWAI (
JABATAN_ID ASC
);

/*==============================================================*/
/* Index: MEMILIKI_GOLONGAN_FK                                  */
/*==============================================================*/
create index MEMILIKI_GOLONGAN_FK on PEGAWAI (
GOL_ID ASC
);

/*==============================================================*/
/* Index: BEKERJA_DI_UNIT_FK                                    */
/*==============================================================*/
create index BEKERJA_DI_UNIT_FK on PEGAWAI (
UNIT_KERJA_ID ASC
);

/*==============================================================*/
/* Index: TERMASUK_KELAS_FK                                     */
/*==============================================================*/
create index TERMASUK_KELAS_FK on PEGAWAI (
CLASS_ID ASC
);

/*==============================================================*/
/* Index: DILAKUKAN_OLEH_FK                                     */
/*==============================================================*/
create index DILAKUKAN_OLEH_FK on PEGAWAI (
ABSENSI_ID ASC
);

/*==============================================================*/
/* Index: MEMILIKI_ESELON_FK                                    */
/*==============================================================*/
create index MEMILIKI_ESELON_FK on PEGAWAI (
ESELON ASC
);

/*==============================================================*/
/* Index: UNTUK_STATUS_TUNJANGAN_FK                             */
/*==============================================================*/
create index UNTUK_STATUS_TUNJANGAN_FK on PEGAWAI (
TUNJANGAN_ID ASC
);

/*==============================================================*/
/* Table: PEG_MUTASI_UNIT                                       */
/*==============================================================*/
create table PEG_MUTASI_UNIT 
(
   TRAKSAKSI_ID         integer                        not null,
   NIP                  varchar(50)                    not null,
   TGL_MUTASI           date                           null,
   UNIT_KERJA           varchar(50)                    null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   NO_SK                varchar(50)                    null,
   KETERANGAN           varchar(250)                   null
);

/*==============================================================*/
/* Index: USER_PINDAH_UNIT_FK                                   */
/*==============================================================*/
create index USER_PINDAH_UNIT_FK on PEG_MUTASI_UNIT (
NIP ASC
);

/*==============================================================*/
/* Index: MENCATAT_MUTASI_UNIT_FK                               */
/*==============================================================*/
create index MENCATAT_MUTASI_UNIT_FK on PEG_MUTASI_UNIT (
TRAKSAKSI_ID ASC
);

/*==============================================================*/
/* Table: PERUBAHAN_JABATAN                                     */
/*==============================================================*/
create table PERUBAHAN_JABATAN 
(
   JABATAN_ID_BARU      integer                        not null,
   JABATAN_ID           integer                        null,
   constraint PK_PERUBAHAN_JABATAN primary key (JABATAN_ID_BARU)
);

/*==============================================================*/
/* Index: PERUBAHAN_JABATAN_PK                                  */
/*==============================================================*/
create unique index PERUBAHAN_JABATAN_PK on PERUBAHAN_JABATAN (
JABATAN_ID_BARU ASC
);

/*==============================================================*/
/* Index: MERUBAH_JABATAN2_FK                                   */
/*==============================================================*/
create index MERUBAH_JABATAN2_FK on PERUBAHAN_JABATAN (
JABATAN_ID ASC
);

/*==============================================================*/
/* Table: SARAN                                                 */
/*==============================================================*/
create table SARAN 
(
   ID_SARAN             integer                        not null,
   NIP                  varchar(50)                    not null,
   SARAN                varchar(350)                   not null,
   INSTANSI             varchar(100)                   not null,
   constraint PK_SARAN primary key (ID_SARAN)
);

/*==============================================================*/
/* Index: SARAN_PK                                              */
/*==============================================================*/
create unique index SARAN_PK on SARAN (
ID_SARAN ASC
);

/*==============================================================*/
/* Index: MENYAMPAIKAN_FK                                       */
/*==============================================================*/
create index MENYAMPAIKAN_FK on SARAN (
NIP ASC
);

/*==============================================================*/
/* Table: SKP_PEGAWAI                                           */
/*==============================================================*/
create table SKP_PEGAWAI 
(
   GUID_SKP_PEG         varchar(100)                   not null,
   NIP                  varchar(50)                    not null,
   JABATAN_ID           integer                        not null,
   DESKRIPSI            varchar(500)                   null,
   AK                   float                          null,
   QTY                  float                          null,
   MUTU                 float                          null,
   WAKTU                timestamp                      null,
   BIAYA                float                          null,
   UNSUR                varchar(50)                    null,
   TYPE                 integer                        null,
   TGL_MULAI            timestamp                      null,
   SATUAN_QTY           varchar(50)                    null,
   SATUAN_MUTU          varchar(50)                    null,
   SATUAN_WAKTU         varchar(50)                    null,
   constraint PK_SKP_PEGAWAI primary key (GUID_SKP_PEG)
);

/*==============================================================*/
/* Index: SKP_PEGAWAI_PK                                        */
/*==============================================================*/
create unique index SKP_PEGAWAI_PK on SKP_PEGAWAI (
GUID_SKP_PEG ASC
);

/*==============================================================*/
/* Index: DILAKSANAKAN_DI_FK                                    */
/*==============================================================*/
create index DILAKSANAKAN_DI_FK on SKP_PEGAWAI (
JABATAN_ID ASC
);

/*==============================================================*/
/* Index: TERKAIT_OLEH_FK                                       */
/*==============================================================*/
create index TERKAIT_OLEH_FK on SKP_PEGAWAI (
NIP ASC
);

/*==============================================================*/
/* Table: SKP_PEGAWAI_HEAD                                      */
/*==============================================================*/
create table SKP_PEGAWAI_HEAD 
(
   SKP_PEGAWAI_HEAD_ID  integer                        not null,
   GUID_SKP_PEG         varchar(100)                   not null,
   NIP                  varchar(50)                    not null,
   GOL_ID               integer                        not null,
   JABATAN_ID           integer                        not null,
   TGL_MULAI            timestamp                      null,
   NIP_PARENT           varchar(50)                    null,
   JABATAN_ID_PARENT    varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   TGL_PEMBUATAN        timestamp                      null,
   GOL_PARENT           varchar(10)                    null,
   constraint PK_SKP_PEGAWAI_HEAD primary key (SKP_PEGAWAI_HEAD_ID)
);

/*==============================================================*/
/* Index: SKP_PEGAWAI_HEAD_PK                                   */
/*==============================================================*/
create unique index SKP_PEGAWAI_HEAD_PK on SKP_PEGAWAI_HEAD (
SKP_PEGAWAI_HEAD_ID ASC
);

/*==============================================================*/
/* Index: JABATAN_PEGAWAI_HEAD_FK                               */
/*==============================================================*/
create index JABATAN_PEGAWAI_HEAD_FK on SKP_PEGAWAI_HEAD (
JABATAN_ID ASC
);

/*==============================================================*/
/* Index: USER_HEAD_FK                                          */
/*==============================================================*/
create index USER_HEAD_FK on SKP_PEGAWAI_HEAD (
NIP ASC
);

/*==============================================================*/
/* Index: GOL_PEGAWAI_HEAD_FK                                   */
/*==============================================================*/
create index GOL_PEGAWAI_HEAD_FK on SKP_PEGAWAI_HEAD (
GOL_ID ASC
);

/*==============================================================*/
/* Index: BAWAHAN_USER_SKP_FK                                   */
/*==============================================================*/
create index BAWAHAN_USER_SKP_FK on SKP_PEGAWAI_HEAD (
GUID_SKP_PEG ASC
);

/*==============================================================*/
/* Table: SPRIN_HEADER                                          */
/*==============================================================*/
create table SPRIN_HEADER 
(
   GUID_SPRIN           varchar(50)                    not null,
   TYPE_SPRIN_ID        char(20)                       not null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   ROLE_NUMBER          integer                        null,
   ABSENSI_FINGER       varchar(2)                     null,
   TGL_SPRIN            date                           null,
   PERIHAL_SPRIN        varchar(250)                   null,
   MENIMBANG_1          varchar(250)                   null,
   MENIMBANG_2          varchar(250)                   null,
   MENIMBANG_3          varchar(250)                   null,
   DASAR_1              varchar(250)                   null,
   DASAR_2              varchar(250)                   null,
   DASAR_3              varchar(250)                   null,
   UNTUK_1              varchar(250)                   null,
   UNTUK_2              varchar(250)                   null,
   UNTUK_3              varchar(250)                   null,
   UNTUK_4              varchar(250)                   null,
   UNTUK_5              varchar(250)                   null,
   JABATAN_OTO          varchar(100)                   null,
   NIP_OTO              varchar(50)                    null,
   NO_URUT_SPRIN        varchar(5)                     null,
   NO_SISIPAN           varchar(50)                    null,
   NO_SPRIN             varchar(50)                    null,
   TGL_AWAL_SPRIN       date                           null,
   TGL_AKHIR_SPRIN      varchar(50)                    null,
   PENEMPATAN           varchar(150)                   null,
   STATUS_UM            integer                        null,
   constraint PK_SPRIN_HEADER primary key (GUID_SPRIN)
);

/*==============================================================*/
/* Index: SPRIN_HEADER_PK                                       */
/*==============================================================*/
create unique index SPRIN_HEADER_PK on SPRIN_HEADER (
GUID_SPRIN ASC
);

/*==============================================================*/
/* Index: BERTIPE_FK                                            */
/*==============================================================*/
create index BERTIPE_FK on SPRIN_HEADER (
TYPE_SPRIN_ID ASC
);

/*==============================================================*/
/* Table: TIME_RECORDER                                         */
/*==============================================================*/
create table TIME_RECORDER 
(
   FINGER_ID            integer                        not null,
   WAKTU                timestamp                      null,
   STATUS               varchar(3)                     null,
   MESIN                varchar(100)                   null,
   KET                  varchar(50)                    null,
   TRANSAKSI            varchar(50)                    null,
   KET_INJECT           varchar(150)                   null,
   REF_INJECT           varchar(150)                   null,
   TRX                  varchar(50)                    null,
   UPDATE_IN_BY         varchar(50)                    null,
   UPDATE_DATE          timestamp                      null,
   constraint PK_TIME_RECORDER primary key (FINGER_ID)
);

/*==============================================================*/
/* Index: TIME_RECORDER_PK                                      */
/*==============================================================*/
create unique index TIME_RECORDER_PK on TIME_RECORDER (
FINGER_ID ASC
);

/*==============================================================*/
/* Table: USER_ACCOUNT                                          */
/*==============================================================*/
create table USER_ACCOUNT 
(
   NIP                  varchar(50)                    not null,
   INIT_LEVEL           integer                        null,
   MODUL                varchar(50)                    null,
   UPDATE_BY            varchar(50)                    null,
   UPDATE_DATE          timestamp                      null
);

/*==============================================================*/
/* Index: DIMILIKI_OLEH_USER_FK                                 */
/*==============================================================*/
create index DIMILIKI_OLEH_USER_FK on USER_ACCOUNT (
NIP ASC
);

alter table ABSENSI
   add constraint FK_ABSENSI_DATA_BACK_ABSENSI_ foreign key (ABSENSI_BACKUP_ID)
      references ABSENSI_BACKUP (ABSENSI_BACKUP_ID)
      on update restrict
      on delete restrict;

alter table ABSENSI
   add constraint FK_ABSENSI_DATA_TEMP_ABSENSI_ foreign key (ABSENSI_TEMP_ID)
      references ABSENSI_TEMP (ABSENSI_TEMP_ID)
      on update restrict
      on delete restrict;

alter table ABSENSI
   add constraint FK_ABSENSI_DITERAPKA_MF_POT foreign key (POTONGAN_ID)
      references MF_POT (POTONGAN_ID)
      on update restrict
      on delete restrict;

alter table ABSENSI
   add constraint FK_ABSENSI_MENJADI_S_TIME_REC foreign key (FINGER_ID)
      references TIME_RECORDER (FINGER_ID)
      on update restrict
      on delete restrict;

alter table ABSENSI
   add constraint FK_ABSENSI_TERJADI_P_KALENDER foreign key (TGL_KERJA)
      references KALENDER (TGL_KERJA)
      on update restrict
      on delete restrict;

alter table ABSENSI_BACKUP
   add constraint FK_ABSENSI__DATA_BACK_ABSENSI foreign key (ABSENSI_ID)
      references ABSENSI (ABSENSI_ID)
      on update restrict
      on delete restrict;

alter table ABSENSI_TEMP
   add constraint FK_ABSENSI__DATA_TEMP_ABSENSI foreign key (ABSENSI_ID)
      references ABSENSI (ABSENSI_ID)
      on update restrict
      on delete restrict;

alter table BUKU_HARIAN_HEAD
   add constraint FK_BUKU_HAR_DIBUAT_OL_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table BUKU_HARIAN_HEAD
   add constraint FK_BUKU_HAR_TERKAIT_D_SKP_PEGA foreign key (GUID_SKP_PEG)
      references SKP_PEGAWAI (GUID_SKP_PEG)
      on update restrict
      on delete restrict;

alter table BUKU_HARIAN_HEAD
   add constraint FK_BUKU_HAR_TERKAIT_J_MF_JABAT2 foreign key (JABATAN_ID)
      references MF_JABATAN (JABATAN_ID)
      on update restrict
      on delete restrict;

alter table BUKU_HARIAN_HEAD
   add constraint FK_BUKU_HAR_TERKAIT_J_MF_JABAT foreign key (ITEM_ID)
      references MF_JABATAN_KEGIATAN (ITEM_ID)
      on update restrict
      on delete restrict;

alter table DINAS_LUAR
   add constraint FK_DINAS_LU_BERDASARK_SPRIN_HE foreign key (GUID_SPRIN)
      references SPRIN_HEADER (GUID_SPRIN)
      on update restrict
      on delete restrict;

alter table DINAS_LUAR
   add constraint FK_DINAS_LU_MELAKUKAN_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table DRH
   add constraint FK_DRH_JABATAN_D_MF_JABAT foreign key (JABATAN_ID)
      references MF_JABATAN (JABATAN_ID)
      on update restrict
      on delete restrict;

alter table DRH
   add constraint FK_DRH_MEREKAM_D_LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table DRH
   add constraint FK_DRH_PEGAWAI_D_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table HAK_AKSES_FORM
   add constraint FK_HAK_AKSE_DIBERIKAN_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table HAK_AKSES_FORM
   add constraint FK_HAK_AKSE_UNTUK_FOR_MF_FORM foreign key (FORM_ID)
      references MF_FORM (FORM_ID)
      on update restrict
      on delete restrict;

alter table HAK_AKSES_TYPE_SPRIN
   add constraint FK_HAK_AKSE_AKSES_SPR_MF_TYPE_ foreign key (TYPE_SPRIN_ID)
      references MF_TYPE_SPRIN (TYPE_SPRIN_ID)
      on update restrict
      on delete restrict;

alter table HAK_AKSES_TYPE_SPRIN
   add constraint FK_HAK_AKSE_USER_SPRI_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table LEMBUR
   add constraint FK_LEMBUR_DILAKUKAN_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table LEMBUR
   add constraint FK_LEMBUR_TERJADI_T_KALENDER foreign key (TGL_KERJA)
      references KALENDER (TGL_KERJA)
      on update restrict
      on delete restrict;

alter table LOG_ACTIVITIY
   add constraint FK_LOG_ACTI_DILAKUKAN_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table LOG_ACTIVITIY
   add constraint FK_LOG_ACTI_DILAKUKAN_MF_TIM_S foreign key (GUID_TIM)
      references MF_TIM_SIAGA (GUID_TIM)
      on update restrict
      on delete restrict;

alter table LOG_ACTIVITIY
   add constraint FK_LOG_ACTI_MEMBACKUP_LOG_ACTI foreign key (GUID_LOG_BACKUP)
      references LOG_ACTIVITIY_BACKUP (GUID_LOG_BACKUP)
      on update restrict
      on delete restrict;

alter table LOG_ACTIVITIY
   add constraint FK_LOG_ACTI_MEMILIKI__MF_STATU foreign key (STATUS_ID)
      references MF_STATUS (STATUS_ID)
      on update restrict
      on delete restrict;

alter table LOG_ACTIVITIY
   add constraint FK_LOG_ACTI_TRANSAKSI_LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table LOG_ACTIVITIY
   add constraint FK_LOG_ACTI_UNIT_MELA_MF_UNIT_ foreign key (UNIT_KERJA_ID)
      references MF_UNIT_KERJA (UNIT_KERJA_ID)
      on update restrict
      on delete restrict;

alter table LOG_ACTIVITIY_BACKUP
   add constraint FK_LOG_ACTI_MEMBACKUP_LOG_BKP foreign key (GUID_LOG)
      references LOG_ACTIVITIY (GUID_LOG)
      on update restrict
      on delete restrict;

alter table LOG_TRANSAKSI
   add constraint FK_LOG_TRAN_DATA_BACK_LOG_TRAN foreign key (TRAKSAKSI_BACKUP_ID)
      references LOG_TRANSAKSI_BACKUP (TRAKSAKSI_BACKUP_ID)
      on update restrict
      on delete restrict;

alter table LOG_TRANSAKSI
   add constraint FK_LOG_TRAN_TRANSAKSI_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table LOG_TRANSAKSI_BACKUP
   add constraint FK_LOG_TRAN_DATA_BACK_LOG_BKP foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table MF_CONFIG
   add constraint FK_MF_CONFI_MENCATAT__LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table MF_FIELD_CARI
   add constraint FK_MF_FIELD_MENCATAT__LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table MF_HOST_NAME_FP
   add constraint FK_MF_HOST__HOST_DARI_MF_UNIT_ foreign key (UNIT_KERJA_ID)
      references MF_UNIT_KERJA (UNIT_KERJA_ID)
      on update restrict
      on delete restrict;

alter table MF_JABATAN
   add constraint FK_MF_JABAT_MERUBAH_J_PERUBAHA foreign key (JABATAN_ID_BARU)
      references PERUBAHAN_JABATAN (JABATAN_ID_BARU)
      on update restrict
      on delete restrict;

alter table MF_JABATAN
   add constraint FK_MF_JABAT_TERMASUK__MF_GROUP foreign key (GROUP_JABATAN_ID)
      references MF_GROUP_JABATAN (GROUP_JABATAN_ID)
      on update restrict
      on delete restrict;

alter table MF_JABATAN
   add constraint FK_MF_JABAT_TERMASUK__MF__SUB_ foreign key (SUB_GROUP_JABATAN_ID)
      references MF_SUB_GROUP_JABATAN (SUB_GROUP_JABATAN_ID)
      on update restrict
      on delete restrict;

alter table MF_JABATAN_KEGIATAN
   add constraint FK_MF_JABAT_DIBUAT_UN_MF_JABAT foreign key (JABATAN_ID)
      references MF_JABATAN (JABATAN_ID)
      on update restrict
      on delete restrict;

alter table MF_JOBLIST
   add constraint FK_MF_JOBLI_MEMILIKI__MF_GROUP foreign key (GROUP_JABATAN_ID)
      references MF_GROUP_JABATAN (GROUP_JABATAN_ID)
      on update restrict
      on delete restrict;

alter table MF_JOBLIST
   add constraint FK_MF_JOBLI_MENGACU_K_MF_JABAT foreign key (ITEM_ID)
      references MF_JABATAN_KEGIATAN (ITEM_ID)
      on update restrict
      on delete restrict;

alter table MF_KLASIFIKASI_SURAT
   add constraint FK_MF_KLASI_MENGAKLSI_MF_TYPE_ foreign key (TYPE_SPRIN_ID)
      references MF_TYPE_SPRIN (TYPE_SPRIN_ID)
      on update restrict
      on delete restrict;

alter table MF_LOAD_FINGER
   add constraint FK_MF_LOAD__MENCATAT__LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table MF_SHIFT
   add constraint FK_MF_SHIFT_MENCATAT__LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table MF_SU
   add constraint FK_MF_SU_MENYIMPAN_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table MF_TIM_SIAGA_ANGGOTA
   add constraint FK_MF_TIM_S_BERANGGOT_MF_TIM_S foreign key (GUID_TIM)
      references MF_TIM_SIAGA (GUID_TIM)
      on update restrict
      on delete restrict;

alter table MF_TIM_SIAGA_ANGGOTA
   add constraint FK_MF_TIM_S_DIISI_OLE_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table MF_TR
   add constraint FK_MF_TR_MENCATAT__LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table MONITORING_APP
   add constraint FK_MONITORI_MENCATAT__LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table OTORISASI
   add constraint FK_OTORISAS_DIAJUKAN__PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table OTORISASI_HISTORY
   add constraint FK_OTORISAS_OTORISASI_MF_UNIT_ foreign key (UNIT_KERJA_ID)
      references MF_UNIT_KERJA (UNIT_KERJA_ID)
      on update restrict
      on delete restrict;

alter table OTORISASI_HISTORY
   add constraint FK_OTORISAS_OTORISASI_OTORISAS foreign key (GUID_OTO)
      references OTORISASI (GUID_OTO)
      on update restrict
      on delete restrict;

alter table OTORISASI_HISTORY
   add constraint FK_OTORISAS_USER_OTOR_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table PEGAWAI
   add constraint FK_PEGAWAI_BEKERJA_D_MF_UNIT_ foreign key (UNIT_KERJA_ID)
      references MF_UNIT_KERJA (UNIT_KERJA_ID)
      on update restrict
      on delete restrict;

alter table PEGAWAI
   add constraint FK_PEGAWAI_DILAKUKAN_ABSENSI foreign key (ABSENSI_ID)
      references ABSENSI (ABSENSI_ID)
      on update restrict
      on delete restrict;

alter table PEGAWAI
   add constraint FK_PEGAWAI_MEMILIKI__MF_ESELO foreign key (ESELON)
      references MF_ESELON (ESELON)
      on update restrict
      on delete restrict;

alter table PEGAWAI
   add constraint FK_PEGAWAI_MEMILIKI__MF_GOL foreign key (GOL_ID)
      references MF_GOL (GOL_ID)
      on update restrict
      on delete restrict;

alter table PEGAWAI
   add constraint FK_PEGAWAI_MENDUDUKI_MF_JABAT foreign key (JABATAN_ID)
      references MF_JABATAN (JABATAN_ID)
      on update restrict
      on delete restrict;

alter table PEGAWAI
   add constraint FK_PEGAWAI_TERMASUK__MF_CLASS foreign key (CLASS_ID)
      references MF_CLASS (CLASS_ID)
      on update restrict
      on delete restrict;

alter table PEGAWAI
   add constraint FK_PEGAWAI_UNTUK_STA_MF_TUNJA foreign key (TUNJANGAN_ID)
      references MF_TUNJANGAN (TUNJANGAN_ID)
      on update restrict
      on delete restrict;

alter table PEG_MUTASI_UNIT
   add constraint FK_PEG_MUTA_MENCATAT__LOG_TRAN foreign key (TRAKSAKSI_ID)
      references LOG_TRANSAKSI (TRAKSAKSI_ID)
      on update restrict
      on delete restrict;

alter table PEG_MUTASI_UNIT
   add constraint FK_PEG_MUTA_USER_PIND_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table PERUBAHAN_JABATAN
   add constraint FK_PERUBAHA_MERUBAH_J_MF_JABAT foreign key (JABATAN_ID)
      references MF_JABATAN (JABATAN_ID)
      on update restrict
      on delete restrict;

alter table SARAN
   add constraint FK_SARAN_MENYAMPAI_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table SKP_PEGAWAI
   add constraint FK_SKP_PEGA_DILAKSANA_MF_JABAT foreign key (JABATAN_ID)
      references MF_JABATAN (JABATAN_ID)
      on update restrict
      on delete restrict;

alter table SKP_PEGAWAI
   add constraint FK_SKP_PEGA_TERKAIT_O_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table SKP_PEGAWAI_HEAD
   add constraint FK_SKP_PEGA_BAWAHAN_U_SKP_PEGA foreign key (GUID_SKP_PEG)
      references SKP_PEGAWAI (GUID_SKP_PEG)
      on update restrict
      on delete restrict;

alter table SKP_PEGAWAI_HEAD
   add constraint FK_SKP_PEGA_GOL_PEGAW_MF_GOL foreign key (GOL_ID)
      references MF_GOL (GOL_ID)
      on update restrict
      on delete restrict;

alter table SKP_PEGAWAI_HEAD
   add constraint FK_SKP_PEGA_JABATAN_P_MF_JABAT foreign key (JABATAN_ID)
      references MF_JABATAN (JABATAN_ID)
      on update restrict
      on delete restrict;

alter table SKP_PEGAWAI_HEAD
   add constraint FK_SKP_PEGA_USER_HEAD_PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

alter table SPRIN_HEADER
   add constraint FK_SPRIN_HE_BERTIPE_MF_TYPE_ foreign key (TYPE_SPRIN_ID)
      references MF_TYPE_SPRIN (TYPE_SPRIN_ID)
      on update restrict
      on delete restrict;

alter table USER_ACCOUNT
   add constraint FK_USER_ACC_DIMILIKI__PEGAWAI foreign key (NIP)
      references PEGAWAI (NIP)
      on update restrict
      on delete restrict;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================
-- INSERT DATA DUMMY UNTUK SEMUA TABEL
-- =============================================================

-- Nonaktifkan foreign key check sementara agar bisa insert dengan urutan bebas
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Tabel Master Independen (tanpa FK atau FK ke tabel yg sudah diisi)
