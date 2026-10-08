# HRIS GLOBAL DEVELOPMENT STANDARD

Dokumen ini adalah standar pengembangan global untuk seluruh modul HRIS Reborn.

Dokumen ini WAJIB dibaca dan dijadikan referensi sebelum membuat form,
service, controller, helper, export, PDF, atau modul baru.

---

## 1. TUJUAN

Menjaga agar seluruh modul HRIS:

- konsisten
- tidak memiliki implementasi yang duplikat
- menggunakan helper yang sama
- memiliki pola UI yang seragam
- memiliki pola storage yang seragam
- memiliki pola export yang seragam
- mudah dipelihara
- mudah dikembangkan di masa depan

Prinsip utama:

> REUSE, DON'T DUPLICATE.

Jika helper atau standard sudah tersedia, gunakan helper tersebut.
Jangan membuat implementasi lokal baru tanpa alasan teknis yang jelas.

---

# 2. ATURAN PENGEMBANGAN MODUL BARU

Sebelum membuat modul/form baru WAJIB:

1. Membaca dokumen ini.
2. Mengecek helper yang sudah tersedia.
3. Mengecek Global UI Standard.
4. Mengecek Global Storage Standard.
5. Mengecek Global Export/PDF Standard jika diperlukan.
6. Menggunakan helper yang sudah tersedia.
7. Tidak melakukan copy-paste implementasi dari modul lain.
8. Jika kebutuhan belum tersedia, pertimbangkan membuat atau memperluas helper global.

Prinsip:

> EXTEND, DON'T CLONE.

Jika helper yang ada hampir memenuhi kebutuhan, lebih baik
mengembangkan helper tersebut daripada membuat helper baru.

---

# 3. GLOBAL SIGNATURE / TANDA TANGAN STANDARD

## 3.1 Prinsip

Tanda tangan adalah atribut tambahan dari data pegawai.

Tidak tersedianya file tanda tangan TIDAK BOLEH menyebabkan:

- pegawai hilang dari daftar
- attendance hilang
- data pegawai tidak ditampilkan
- record database dihapus
- attendance dianggap tidak valid

Kehadiran/data pegawai adalah sumber utama.

Tanda tangan hanya atribut tambahan.

---

## 3.2 Tampilan Tanda Tangan

Jika file tanda tangan tersedia:

    tampilkan gambar tanda tangan.

Jika file tanda tangan tidak tersedia:

    --- belum ada ttd ---

Jangan menggunakan:

    -

untuk kondisi "tanda tangan belum tersedia".

Jangan menghilangkan baris pegawai.

Jangan membuat tanda tangan dummy.

---

## 3.3 Global Signature Helper

Seluruh modul yang membutuhkan tanda tangan pegawai
WAJIB menggunakan Global Signature Helper.

Resolver tanda tangan TIDAK BOLEH dibuat ulang secara lokal
di masing-masing controller/service/template apabila helper global
sudah tersedia.

Helper harus menangani:

- lokasi root TTD
- pencarian berdasarkan identifier pegawai
- stored signature path
- validasi bahwa file berada di dalam root TTD
- pengecekan file benar-benar tersedia

---

## 3.4 Pegawai Tanpa Tanda Tangan

Kondisi:

    signature tidak ditemukan

harus diperlakukan sebagai:

    signature unavailable

bukan sebagai:

    employee unavailable

Contoh:

    Nama Pegawai A    [gambar TTD]
    Nama Pegawai B    --- belum ada ttd ---
    Nama Pegawai C    [gambar TTD]

Ketiga pegawai tetap berada di dalam rekap.

---

# 4. GLOBAL UI STANDARD

Seluruh form baru WAJIB mengikuti:

    app/static/css/hris-ui.css

Jangan membuat style global baru apabila style yang dibutuhkan
sudah tersedia pada Global UI Standard.

Jika komponen UI baru dibutuhkan:

1. cek apakah komponen serupa sudah ada
2. gunakan yang sudah ada
3. jika belum ada, pertimbangkan menambahkannya ke standard global

---

# 5. GLOBAL STORAGE STANDARD

File aplikasi harus mengikuti konfigurasi storage HRIS yang telah ditetapkan.

Jangan membuat lokasi penyimpanan baru secara hard-coded
jika sudah tersedia konfigurasi/helper storage global.

Gunakan konfigurasi aplikasi dan helper storage yang berlaku.

---

# 6. GLOBAL PDF STANDARD

PDF yang dibuat oleh modul HRIS harus:

- menggunakan data sumber yang sama dengan preview
- mempertahankan urutan data
- mempertahankan informasi penting dari preview
- menggunakan standard tanda tangan global
- menampilkan "--- belum ada ttd ---" apabila TTD tidak tersedia
- tidak menghilangkan pegawai hanya karena TTD tidak tersedia

---

# 7. GLOBAL EXCEL / EXPORT STANDARD

Export harus menggunakan data yang sama dengan preview.

Jangan membuat logika data kedua yang berbeda dari preview
hanya untuk kebutuhan export.

Jika terdapat kolom TANDA TANGAN:

- TTD tersedia → tampilkan sesuai standard
- TTD tidak tersedia → "--- belum ada ttd ---"

---

# 8. API STANDARD

API harus:

- memberikan response yang konsisten
- membedakan error autentikasi, validasi, not found, dan server error
- tidak menganggap data optional sebagai error bisnis
- tidak menghapus atau menyembunyikan data utama hanya karena
  atribut tambahan tidak tersedia

---

# 9. DATABASE STANDARD

Jangan mengubah database hanya untuk memperbaiki tampilan.

Pisahkan:

- data utama
- data relasi
- atribut optional
- file/storage reference

Ketiadaan file storage tidak otomatis berarti record database
harus diubah atau dihapus.

---

# 10. BACKUP & SAFETY STANDARD

Sebelum perubahan besar:

1. cek git status
2. cek branch
3. cek HEAD
4. buat backup jika diperlukan
5. lakukan perubahan kecil
6. test
7. commit

Jangan menjalankan:

    git clean -fd

atau perintah destruktif lain tanpa pemeriksaan terlebih dahulu.

File backup *.bak-* yang ada di server jangan dihapus otomatis.

---

# 11. MICRO-PATCH STANDARD

Perubahan kode dilakukan sekecil mungkin.

Urutan:

    CHECK
      ↓
    PATCH
      ↓
    SYNTAX CHECK
      ↓
    RESTART SERVICE
      ↓
    TEST
      ↓
    GIT DIFF
      ↓
    COMMIT

Jangan mengubah banyak modul sekaligus tanpa kebutuhan.

---

# 12. NEW FORM CHECKLIST

Sebelum form baru dianggap selesai:

[ ] Sudah membaca HRIS_GLOBAL_DEVELOPMENT_STANDARD.md
[ ] Sudah mengecek helper yang tersedia
[ ] Tidak membuat duplicate helper
[ ] Menggunakan Global UI Standard
[ ] Menggunakan Global Storage Standard
[ ] Menggunakan Global Signature Helper jika membutuhkan TTD
[ ] Menggunakan Global PDF Standard jika membuat PDF
[ ] Menggunakan Global Excel Standard jika membuat Excel
[ ] Preview dan export menggunakan sumber data yang sama
[ ] TTD yang tidak tersedia ditampilkan sebagai:
    --- belum ada ttd ---
[ ] Pegawai tidak dihilangkan karena TTD tidak tersedia
[ ] Tidak ada perubahan database yang tidak diperlukan
[ ] Syntax check berhasil
[ ] Service berhasil restart
[ ] Functional test berhasil
[ ] Git diff sudah diperiksa
[ ] Commit dibuat

---

# 13. GLOBAL HELPER REGISTRY

Helper global akan dicatat di bagian ini.

## 13.1 Signature Helper

Status:

    TO BE IMPLEMENTED

Fungsi:

    Resolving tanda tangan pegawai secara terpusat.

Aturan:

    Semua modul yang membutuhkan TTD pegawai menggunakan helper ini.

---

## 13.2 Date/Time Helper

Status:

    EXISTING / TO BE DOCUMENTED

---

## 13.3 Currency / Rupiah Helper

Status:

    EXISTING / TO BE DOCUMENTED

---

## 13.4 Storage Helper

Status:

    EXISTING / TO BE DOCUMENTED

---

## 13.5 PDF Helper

Status:

    EXISTING / TO BE DOCUMENTED

---

## 13.6 Excel Helper

Status:

    EXISTING / TO BE DOCUMENTED

---

## 13.7 Global Table Alignment Controller

Status:

    EXISTING

Aturan:

    Semua tabel yang menggunakan .hris-table default rata kiri.

Pengecualian alignment harus eksplisit menggunakan:

    .hris-text-center
    .hris-text-right

Jangan membuat alignment controller lokal pada halaman apabila
Global Table Alignment Controller sudah dapat digunakan.

---

## 13.8 Global Agenda / Month Navigation Controller

Status:

    EXISTING

Digunakan untuk halaman daftar kegiatan/agenda yang datanya bersifat periodik,
termasuk Agenda Rapat dan Kesamaptaan.

Aturan:

    - Default membuka bulan berjalan.
    - Navigasi bulan menggunakan tombol bulan sebelumnya / berikutnya.
    - Tampilan mengikuti pola UI AgendaKu pada HRIS Calendar.
    - Warna identitas HRIS Reborn tetap menggunakan aksen orange.
    - Daftar hanya menampilkan data pada bulan yang dipilih.
    - Jangan membuat month picker lokal dengan desain berbeda.

Komponen global:

    .hris-agenda-period-card
    .hris-month-nav
    .hris-month-nav-btn
    .hris-month-nav-label
    .hris-agenda-list-card
    .hris-agenda-list-header
    .hris-agenda-list-title
    .hris-agenda-count

Prinsip:

    ONE MONTH NAVIGATION PATTERN.
    ONE AGENDA LIST PATTERN.

---

# 14. ATURAN PENAMBAHAN HELPER BARU

Helper baru hanya dibuat apabila:

1. kebutuhan digunakan oleh lebih dari satu modul, atau
2. kebutuhan merupakan pola global aplikasi, atau
3. helper tersebut mencegah duplikasi kode yang signifikan.

Setiap helper baru WAJIB ditambahkan ke:

    GLOBAL HELPER REGISTRY

dan didokumentasikan cara penggunaannya.

---

# 15. ATURAN UNTUK CHATGPT / DEVELOPER

Saat mengembangkan modul HRIS:

1. Baca dokumen ini terlebih dahulu.
2. Cari helper yang relevan.
3. Gunakan helper yang sudah ada.
4. Jangan membuat duplicate implementation.
5. Jika membuat helper baru, dokumentasikan.
6. Ikuti Micro-Patch Standard.
7. Jangan mengubah modul yang tidak terkait.
8. Jangan mengubah database tanpa kebutuhan yang jelas.
9. Pertahankan backward compatibility.

Prinsip utama:

> ONE STANDARD.
> ONE HELPER.
> ONE SOURCE OF TRUTH.

---

# 16. CHANGE LOG

## 2026-10-08

Initial version.

Ditambahkan standard:

- Global Development Standard
- Global Signature / Tanda Tangan Standard
- Global UI Standard reference
- Global Storage Standard
- Global PDF Standard
- Global Excel / Export Standard
- API Standard
- Database Standard
- Backup & Safety Standard
- Micro-Patch Standard
- New Form Checklist
- Global Helper Registry

## Change Log — 2026-10-08

Ditambahkan:

- Global Table Alignment Controller
- Global Agenda / Month Navigation Controller
- UI agenda mengikuti pola AgendaKu HRIS Calendar dengan aksen orange
