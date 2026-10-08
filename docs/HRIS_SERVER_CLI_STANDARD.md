# HRIS Reborn — Server & CLI Development Standard

> **Purpose:** catatan wajib untuk pengembangan/debugging HRIS Reborn di SERVER-HRIS agar command CLI yang diberikan selalu sesuai environment server yang sebenarnya.

## 1. Server Aplikasi

- Host aplikasi: **SERVER-HRIS**
- Application path: `/opt/hris/app`
- WorkingDirectory systemd: `/opt/hris/app`
- Virtual environment: `/opt/hris/venv`
- Python aplikasi: `/opt/hris/venv/bin/python3.12`
- Gunicorn: `/opt/hris/venv/bin/gunicorn`
- Bind: `127.0.0.1:8000`
- Workers: `2`
- Timeout: `120`
- Gunicorn application: `app:create_app()`
- Service: `hris.service`
- Service user/group: `root/root`
- Service PATH: `/opt/hris/venv/bin`
- Status saat dokumen dibuat: service aktif/running.

### Systemd service

Source of truth service:

```text
/etc/systemd/system/hris.service
/etc/systemd/system/hris.service.d/override.conf
```

Drop-in saat ini:

```ini
[Service]
Environment="REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt"
```

## 2. ATURAN PALING PENTING: Python

**JANGAN memberikan command menggunakan `python` atau `python3` sistem untuk mengimpor aplikasi HRIS.**

Contoh yang SALAH:

```bash
python -c "..."
python3 -c "..."
```

Pada SERVER-HRIS, `python` tidak tersedia sebagai command global dan `python3` sistem tidak memiliki dependency Flask HRIS.

Gunakan interpreter aplikasi:

```bash
/opt/hris/venv/bin/python3.12
```

atau, bila environment sudah diaktifkan:

```bash
source /opt/hris/venv/bin/activate
python ...
```

Untuk test Flask/app langsung, gunakan:

```bash
cd /opt/hris/app

/opt/hris/venv/bin/python3.12 - <<'PY'
from app import app
print("HRIS app import OK")
PY
```

**Jangan menginstall Flask/dependency baru ke system Python hanya karena `python3` gagal import Flask.**

## 3. Cara Mengecek Service

Gunakan:

```bash
systemctl status hris.service --no-pager -l
```

Untuk melihat konfigurasi service:

```bash
systemctl cat hris.service
```

Untuk proses aktif:

```bash
ps aux | grep '[g]unicorn'
```

Expected process menggunakan:

```text
/opt/hris/venv/bin/python3.12
/opt/hris/venv/bin/gunicorn
```

Restart hanya setelah perubahan kode/config yang memang membutuhkan restart:

```bash
systemctl restart hris.service
systemctl status hris.service --no-pager -l
```

## 4. Struktur Git HRIS Reborn

Repository:

```text
ditdoank007/Project-HRIS
```

Branch pengembangan utama untuk pekerjaan UANG SIAGA:

```text
feature/uang-siaga-v2
```

Contoh pemeriksaan:

```bash
cd /opt/hris/app

git status --short
git branch --show-current
git log -1 --oneline --decorate
```

Untuk sinkronisasi branch:

```bash
cd /opt/hris/app

git fetch origin
git switch feature/uang-siaga-v2
git pull --ff-only origin feature/uang-siaga-v2
```

**Jangan menggunakan `git reset --hard` tanpa persetujuan/diagnosis terlebih dahulu.**

## 5. Backup Files di Working Tree

SERVER-HRIS memiliki banyak file backup lokal dengan pola:

```text
*.bak-YYYYMMDD-...
```

File-file tersebut dapat muncul sebagai `??` pada `git status`.

Contoh:

```text
app/controllers/calendarController.py.bak-...
app/controllers/dashboard_1DataAbsensiController.py.bak-...
...
```

**Jangan menghapus, commit, atau `git add .` file backup tersebut secara massal.**

Saat melakukan commit, stage hanya file yang memang diubah untuk pekerjaan tersebut.

## 6. Database HRIS

Database aplikasi:

```text
DB name : HRIS
DB user : hris_app
DB host : 192.168.100.128
DB port : 3306
```

Contoh query:

```bash
mysql -h 192.168.100.128 -u hris_app -p HRIS -e "SELECT ...;"
```

Jangan menaruh password database secara literal di command yang disimpan di dokumentasi.

## 7. Master Data Pegawai

Source of truth data pegawai adalah tabel:

```text
PEGAWAI
```

Model:

```text
app/models/pegawaiModel.py
```

Import:

```python
from app.models.pegawaiModel import Pegawai
```

Query pegawai berdasarkan NIP:

```python
Pegawai.query.filter(Pegawai.NIP == nip).first()
```

Model `Pegawai.to_dict()` sudah menyediakan serialisasi lengkap dan memiliki formatter tanggal yang menangani nilai string serta `0000-00-00`.

## 8. Profilku — Arsitektur

Alur Profilku Calendar:

```text
HRIS Calendar
    |
    | /api/profilku
    v
HRIS Calendar internal proxy
    |
    | /api/internal/calendar/profile
    v
HRIS Reborn routes.py
    |
    | api_internal_profile()
    v
app/controllers/profilkuController.py
    |
    | _internal_nip()
    v
PEGAWAI berdasarkan NIP
    |
    | _profile_payload()
    v
HRIS Calendar Profilku
```

Route GET:

```python
@main.route('/api/internal/calendar/profile', methods=['GET'])
def api_internal_calendar_profile_route():
    return api_internal_profile()
```

**Catatan penting:** route Profilku menggunakan `api_internal_profile()` dari `profilkuController.py`, bukan `api_calendar_employee_profile_internal()` dari `calendarController.py`.

## 9. Aturan Data Profilku

**Master Data Pegawai HRIS Reborn adalah source of truth.**

Jika data di tabel `PEGAWAI` belum lengkap:

- Profilku Calendar **tetap harus tampil**.
- Field yang belum ada ditampilkan sebagai kosong/`-` sesuai UI.
- Data yang kosong pada satu field **tidak boleh membuat seluruh Profilku gagal tampil**.
- Nilai tanggal `0000-00-00` harus diperlakukan sebagai data kosong.
- Jangan membuat database master pegawai kedua di HRIS Calendar hanya untuk mengatasi data kosong.

### Hak edit Profilku

Profilku Calendar **bukan tempat untuk mengedit seluruh Master Data Pegawai**.

Field master seperti berikut tetap berasal dari HRIS Reborn dan bersifat read-only di Calendar:

- NIP
- Nama
- Finger ID
- Pangkat
- Golongan
- Jabatan
- Unit Kerja
- Eselon
- Tanggal Masuk
- Status Pegawai
- Status Keluar
- Tanggal Lahir
- Jenis Kelamin
- Tempat Lahir
- Agama
- Status Perkawinan
- Hobi
- NIK/KTP
- NPWP
- Golongan Recruit
- TMT CPNS
- TMT PNS
- TMT Class
- TMT Pangkat
- TMT Jabatan
- dan data master lainnya.

Field yang saat ini diizinkan untuk diubah dari Calendar:

- No. Telp
- Email
- Alamat
- Kelurahan
- Kecamatan
- Kota

**Jangan memperluas daftar field editable tanpa keputusan eksplisit.**

## 10. Kesalahan CLI yang Pernah Terjadi

### Kesalahan 1 — memakai `python`

Hasil:

```text
bash: python: command not found
```

### Kesalahan 2 — memakai `python3` system

Hasil:

```text
ModuleNotFoundError: No module named 'flask'
```

Kesimpulan:

```text
python / python3 system != Python environment HRIS
```

Python yang benar:

```text
/opt/hris/venv/bin/python3.12
```

### Kesalahan 3 — salah mengira endpoint Profilku

Terdapat dua fungsi yang namanya mirip:

```text
app/controllers/calendarController.py
    api_calendar_employee_profile_internal()

app/controllers/profilkuController.py
    api_internal_profile()
```

Route Profilku saat ini menggunakan:

```text
api_internal_profile()
```

Jadi sebelum patch, **selalu telusuri route -> controller -> function** terlebih dahulu.

## 11. Debugging Endpoint Internal

Untuk test Flask langsung, gunakan interpreter venv:

```bash
cd /opt/hris/app

/opt/hris/venv/bin/python3.12 - <<'PY'
from app import app
from config import Config

NIP = "ISI_NIP_TEST"

with app.test_client() as client:
    response = client.get(
        "/api/internal/calendar/profile",
        headers={
            "X-Calendar-Internal-Key": Config.CALENDAR_INTERNAL_API_KEY,
            "X-Calendar-NIP": NIP,
        },
    )

    print("HTTP STATUS :", response.status_code)
    print("CONTENT TYPE:", response.content_type)
    print(response.get_json())
PY
```

**Jangan pernah mencetak nilai `CALENDAR_INTERNAL_API_KEY` ke terminal/log.**

## 12. Prinsip Pemberian CLI untuk ChatGPT

Sebelum memberikan command kepada developer/server operator, pastikan:

1. Working directory benar: `/opt/hris/app`.
2. Python command memakai `/opt/hris/venv/bin/python3.12` bila membutuhkan import aplikasi.
3. Gunicorn memakai `/opt/hris/venv/bin/gunicorn`.
4. Service menggunakan `hris.service`.
5. Branch diperiksa sebelum pull/commit.
6. Jangan menghapus file backup lokal.
7. Jangan menggunakan `git reset --hard` tanpa alasan dan persetujuan.
8. Jangan mengubah database hanya karena masalah UI/API sebelum source code dan endpoint diperiksa.
9. Telusuri route sebelum menentukan controller yang harus diperbaiki.
10. Gunakan patch kecil/micro-patch untuk perubahan kode.
11. Setelah perubahan, verifikasi syntax/import sebelum restart bila memungkinkan.
12. Restart service hanya setelah perubahan siap diuji.
13. Untuk query database gunakan host yang benar: `192.168.100.128`.
14. Jangan pernah menampilkan secret/API key/password di output atau dokumentasi.
15. Jangan mengasumsikan executable global tersedia hanya karena nama command umum (`python`, `gunicorn`, dll.).

## 13. Checkpoint Profilku Saat Dokumen Ini Dibuat

Masalah yang sedang diperiksa:

```text
Profilku di HRIS Calendar dapat tampil kosong/tidak lengkap
ketika data Master Pegawai HRIS Reborn belum lengkap.
```

Temuan penting:

- Database `PEGAWAI` tetap menjadi sumber data.
- Endpoint menggunakan NIP untuk mengambil pegawai.
- `_profile_payload()` menghasilkan data Profilku.
- Server mencatat error saat nilai tanggal dari database berupa string:
  `AttributeError: 'str' object has no attribute 'strftime'`.
- Service HRIS tetap aktif, tetapi request endpoint Profilku dapat error ketika menemukan tipe tanggal yang tidak sesuai.
- Perbaikan harus membuat payload tahan terhadap data kosong/`0000-00-00` tanpa mengubah aturan hak edit Profilku.

**Dokumen ini adalah referensi operasional. Jika kondisi server berubah, update dokumen ini sebelum memberikan CLI baru.**
