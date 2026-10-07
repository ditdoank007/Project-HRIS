# HRIS Reborn — Database Access Standard

> PENTING: Dokumen ini adalah acuan CLI/database untuk pekerjaan HRIS Reborn. Jangan menebak host database dari konteks lain. Untuk database HRIS gunakan parameter di bawah ini.

## Database HRIS

- Database Server: `192.168.100.128`
- Port: `3306`
- Database: `HRIS`
- Application User: `hris_app`
- Password: JANGAN disimpan di repository / file ini. Gunakan prompt password dari MySQL (`-p`) atau environment variable yang sudah tersedia di server.

## Standar CLI

### Login interaktif

    mysql -h 192.168.100.128 -P 3306 -uhris_app -p HRIS

### Menjalankan SQL file

    mysql -h 192.168.100.128 -P 3306 -uhris_app -p HRIS < /path/to/file.sql

### Menjalankan query langsung

    mysql -h 192.168.100.128 -P 3306 -uhris_app -p HRIS -e "SELECT 1;"

### Contoh cek tabel

    mysql -h 192.168.100.128 -P 3306 -uhris_app -p HRIS -e "SHOW TABLES;"

## Aturan Penting untuk ChatGPT / Pengembang

1. Database HRIS selalu menggunakan `192.168.100.128:3306`.
2. Database name adalah `HRIS`.
3. User aplikasi adalah `hris_app`.
4. Jangan memberikan CLI dengan host database lain kecuali user secara eksplisit meminta perubahan.
5. Jangan pernah menuliskan password database ke file Git, source code, commit, atau chat.
6. Jika menjalankan SQL dari SERVER-HRIS, pastikan file SQL memang ada terlebih dahulu:

       ls -lah /opt/hris/app/development/schema_usecase/sql/

7. Jika file SQL belum ada karena branch belum di-pull, jangan menebak path lain. Periksa branch dan lakukan pull terlebih dahulu.

## Struktur Server

- HRIS application: `/opt/hris/app`
- Service: `hris.service`
- Database: remote MySQL/MariaDB di `192.168.100.128:3306`

## Buku Tamu

SQL schema Buku Tamu berada di:

    /opt/hris/app/development/schema_usecase/sql/buku_tamu.sql

Setelah branch yang berisi file tersebut sudah di-pull, jalankan:

    cd /opt/hris/app
    ls -lah development/schema_usecase/sql/buku_tamu.sql
    mysql -h 192.168.100.128 -P 3306 -uhris_app -p HRIS < development/schema_usecase/sql/buku_tamu.sql
