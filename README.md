# DataWarga

DataWarga adalah aplikasi web sumber terbuka (*open source*) berbasis Python Django web-framework yang dirancang khusus untuk mempermudah pencatatan, pengelolaan data warga, keuangan (kas/iuran), pelayanan surat-menyurat, serta interaksi warga di tingkat RT/RW atau komplek perumahan.

Aplikasi ini dilengkapi dengan portal mandiri untuk warga, integrasi Telegram Bot interaktif, serta pemindaian KTP berbasis AI (OCR) untuk kemudahan input data.

---

## Daftar Isi
- [Fitur Utama](#fitur-utama)
- [Arsitektur & Dokumentasi Detail](#arsitektur--dokumentasi-detail)
- [Quick Start](#quick-start)
  - [1. Inisialisasi Environment & Dependensi](#1-inisialisasi-environment--dependensi)
  - [2. Menjalankan Unit Tests (Bebas PostgreSQL)](#2-menjalankan-unit-tests-bebas-postgresql)
  - [3. Menjalankan Server Lokal (Development)](#3-menjalankan-server-lokal-development)
  - [4. Konfigurasi Awal via Django Admin](#4-konfigurasi-awal-via-django-admin)
- [Perintah Command-Line Developer](#perintah-command-line-developer)
- [Konfigurasi Environment Variables](#konfigurasi-environment-variables)
- [Docker](#docker)
- [Production Deployment](#production-deployment)
- [Kontribusi](#kontribusi)

---

## Fitur Utama

1. **Direktori Warga & Kompleks**:
   - Perekaman data lengkap warga (NIK, KK, status pernikahan, agama, pekerjaan, jenis kelamin, status tinggal).
   - Pembagian data per Kompleks (Blok & Nomor Rumah) serta cluster.
   - Hak akses data tersegregasi wilayah menggunakan grup izin warga (`WargaPermissionGroup`).

2. **Sistem Keuangan RT/RW (Iuran & Kas)**:
   - Pencatatan iuran bulanan per rumah beserta matriks pembayaran iuran tahunan.
   - Pencatatan Kas Pemasukan & Pengeluaran serta modul piutang/hutang tagihan (`KasTagihan`).
   - Ekspor laporan bulanan/tahunan keuangan dan kas ke format PDF.

3. **Portal Mandiri Warga**:
   - Warga dapat masuk untuk melihat status iuran rumah mereka sendiri.
   - Warga dapat mengajukan permohonan surat pengantar, mendaftarkan kendaraan pribadi, mengunggah bukti bayar iuran, serta mengajukan pembaruan data profil yang memerlukan persetujuan admin.

4. **Pembuatan Surat Otomatis**:
   - Pembuatan surat pengantar RT, Keterangan Domisili, dan Keterangan Tidak Mampu dengan template resmi.
   - Pencetakan surat langsung ke format PDF dengan pejabat penandatangan yang aktif.

5. **Telegram Bot Interaktif**:
   - Memungkinkan admin/pengurus mencari warga, melihat detail penghuni rumah, mengecek status iuran bulanan langsung dari aplikasi Telegram.
   - Fitur `/bayar` untuk memandu pencatatan pembayaran iuran dan mengunggah foto bukti bayar.

6. **KTP Pemindaian AI (OCR)**:
   - Pemindaian KTP otomatis dengan mengirimkan gambar KTP ke model AI (menggunakan **Ollama** lokal seperti `llama3.2-vision` atau Cloud **OpenRouter** seperti `google/gemini-2.5-flash`).
   - Secara otomatis mengekstrak NIK, Nama, Alamat, Agama, Jenis Kelamin, Tempat/Tanggal Lahir untuk mempercepat pendaftaran warga.

7. **Keamanan & MFA**:
   - Proteksi brute force login dengan pembatasan percobaan login, *shadow ban* (blokir sementara), dan penguncian akun permanen (`LockoutBackend`).
   - Otentikasi dua faktor (MFA) berbasis TOTP/Google Authenticator.
   - Perlindungan file unggahan sensitif (seperti foto KTP) yang hanya dapat diakses oleh pengguna terautentikasi dan berwenang (`protected_serve`).

---

## Arsitektur & Dokumentasi Detail

Untuk mempelajari cara kerja sistem secara mendalam, silakan baca dokumentasi berikut:
1. [Panduan Arsitektur & Model Database](file:///Users/robertusnegoro/workingdir/repo/datawarga/docs/architecture_and_models.md): Menjelaskan arsitektur Django, skema database, relasi antar tabel, dan segregasi data.
2. [Panduan Telegram Bot & Integrasi AI OCR](file:///Users/robertusnegoro/workingdir/repo/datawarga/docs/telegram_bot_and_ai_ocr.md): Menjelaskan setup Telegram Bot, alur percakapan berbasis agent AI, dan konfigurasi engine OCR (Ollama/OpenRouter).
3. [Panduan Keamanan, MFA & Akses Media](file:///Users/robertusnegoro/workingdir/repo/datawarga/docs/security_and_mfa.md): Menjelaskan logika lockout login, setup MFA bagi user, dan sistem perlindungan berkas media sensitif.

---

## Quick Start

### Persiapan:
- PostgreSQL versi >= 14 (buat database baru dengan nama e.g., `datawarga`).
- Python versi >= 3.10.

### 1. Inisialisasi Environment & Dependensi

Proyek ini menggunakan `pip-tools` untuk manajemen dependensi yang lebih aman dan terstruktur (memisahkan *direct* dan *transitive* dependencies).

```bash
cd /path/to/source/datawarga
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip & install pip-tools
pip install --upgrade pip pip-tools

# Sinkronisasi seluruh dependensi (production & development)
pip-sync requirements.txt dev-requirements.txt
```

> **Tips Manajemen Dependensi:**
> - Dependensi utama (*direct dependencies*) didefinisikan di `requirements.in` dan `dev-requirements.in`.
> - Untuk melakukan pembaruan/kompilasi ulang berkas lock (`requirements.txt` / `dev-requirements.txt`):
>   ```bash
>   pip-compile --upgrade requirements.in --output-file requirements.txt
>   pip-compile --upgrade dev-requirements.in --output-file dev-requirements.txt
>   ```

### 2. Menjalankan Unit Tests (Bebas PostgreSQL)

Konfigurasi pengujian telah ditingkatkan secara otomatis menggunakan database **SQLite3** apabila perintah test dipanggil. Sehingga, Anda **tidak memerlukan database Postgres yang aktif** untuk menjalankan rangkaian pengujian (unit tests) lokal.

Untuk menjalankan seluruh test suite:
```bash
cd datawarga
python manage.py test
```

### 3. Menjalankan Server Lokal (Development)

Buat file `.env.sh` (atau setel variable environment Anda) dengan isi contoh sebagai berikut:

```bash
export DATA_WARGA_SECRET="<isi dengan generated secret>"
export DB_HOST="localhost"
export DB_NAME="datawarga"
export DB_USER="database-user-postgres-anda"
export DB_PASS="katasandi-postgres-anda"
export DB_PORT="5432"
export USE_SQLITE="False" # Set True jika ingin menggunakan SQLite lokal daripada Postgres
```

Untuk menjana `DATA_WARGA_SECRET` baru, Anda dapat mengikuti panduan Django Secret Key.

Setelah environment dimuat, jalankan migrasi database dan server lokal:
```bash
source .env.sh
cd datawarga
python manage.py migrate
python manage.py runserver 18000
```

Buka browser Anda dan akses `http://localhost:18000`

### 4. Konfigurasi Awal via Django Admin

Beberapa pengaturan sistem hanya dapat dikonfigurasi melalui halaman **Django Admin** (`/admin`). Untuk mengaksesnya, pastikan Anda telah membuat akun *superuser*:

```bash
python manage.py createsuperuser
```

Masuk ke `http://localhost:18000/admin` menggunakan akun tersebut. Berikut adalah konfigurasi penting yang perlu disiapkan:

#### A. Warga Permission Group (Hak Akses Data)
Sistem mendukung pembatasan akses data warga. Fitur ini digunakan agar pengurus RT/RW tertentu hanya dapat mengelola data warga di wilayah/kompleks tertentu.
1. Buka menu **Warga permission groups** dan buat grup baru (misal: "Pengurus RT 01").
2. Buka menu **Users**, pilih user yang ingin dibatasi, lalu pada bagian paling bawah (inline `Permission Group`), tetapkan grup yang baru dibuat.
3. Buka menu **Kompleks**, dan pada rumah/blok yang sesuai, setel `Permission group` ke grup yang sama agar hak akses saling terhubung.

#### B. Penandatangan Surat
Untuk menggunakan fitur pembuatan surat (Surat Pengantar, Keterangan Domisili, dll), Anda wajib mendaftarkan pejabat/pengurus yang berwenang menandatangani surat.
1. Buka menu **Penandatangans**.
2. Tambahkan data **Nama** dan **Jabatan** (misal: Ketua RT).
3. Pastikan opsi **Aktif** tercentang agar nama tersebut bisa digunakan saat mencetak surat.

#### C. Data Master Kompleks
Data alamat, kluster, dan blok tempat tinggal warga sebaiknya didefinisikan terlebih dahulu untuk memastikan keabsahan data saat pencatatan warga baru.
1. Buka menu **Kompleks**.
2. Tambahkan data alamat rumah, RT/RW, cluster, blok, dan nomor rumah yang valid di lingkungan Anda.

---

## Perintah Command-Line Developer

Django admin menyediakan beberapa *custom management commands* yang mempermudah deployment dan testing:

### A. Pembuatan Data Dummy Realistis
Anda dapat menginisialisasi database lokal dengan data dummy yang heterogen (meliputi Kompleks, Warga terstruktur keluarga, Iuran bulanan, Kas Keuangan, dan Tagihan):
```bash
python manage.py generate_dummy_data --total-kompleks 50 --occupancy-rate 0.85 --years 2 --seed 42
```
*Argumen tersedia:*
- `--total-kompleks` (default: 20): Jumlah rumah/alamat kompleks yang digenerate.
- `--occupancy-rate` (default: 0.8): Rasio rumah yang berpenghuni (0.0 sampai 1.0).
- `--years` (default: 2): Rentang tahun riwayat iuran dan kas keuangan yang dibuat.
- `--seed`: Angka seed generator acak untuk hasil replikatif.
- `--clear`: Menghapus data lama (Kompleks, Warga, Iuran, Kas) sebelum generate data baru.
- `--only-kas`: Hanya menghasilkan data Kas & Tagihan.

### B. Menjalankan Telegram Bot
Untuk menjalankan Telegram Bot agar merespons perintah chat secara *long-polling*:
```bash
python manage.py run_telegram_bot
```
Pastikan Anda sudah mengonfigurasi `TELEGRAM_BOT_TOKEN`, `BOT_API_USER`, `BOT_API_PASS`, dan `SITE_URL` terlebih dahulu di environment.

### C. Pembuatan Matriks Pembayaran Iuran
Untuk memperbarui ringkasan/matriks pembayaran iuran warga tahunan secara offline/cron:
```bash
python manage.py summarize_iuran_bulanan --blok J2 --year 2026
```

---

## Konfigurasi Environment Variables

Aplikasi ini membaca konfigurasi melalui variabel lingkungan (Environment Variables). Berikut daftar lengkap variabel yang didukung:

| Variabel | Tipe | Deskripsi | Default / Contoh |
| --- | --- | --- | --- |
| **Keamanan & Database** | | | |
| `DATA_WARGA_SECRET` | String | Django Secret Key untuk enkripsi session & tokens | `django-insecure-fallback-...` |
| `WG_ENV` | String | Lingkungan aplikasi (`dev` atau `prod`) | `dev` |
| `USE_SQLITE` | Boolean | Paksa aplikasi menggunakan database SQLite lokal | `False` |
| `DB_NAME` | String | Nama database PostgreSQL | `datawarga` |
| `DB_HOST` | String | Host server PostgreSQL | `localhost` |
| `DB_PORT` | Integer | Port database PostgreSQL | `5432` |
| `DB_USER` | String | Username database PostgreSQL | `postgres` |
| `DB_PASS` | String | Password database PostgreSQL | - |
| `DB_SSL` | Boolean | Aktifkan koneksi SSL PostgreSQL (`True`/`False`) | `False` |
| `WG_TRUSTED` | String | Origin tepercaya untuk CSRF (misal: domain prod) | `http://localhost:8000` |
| **Pengaturan Wilayah & Iuran** | | | |
| `WG_RT` | String | Nomor Rukun Tetangga (RT) | `006` |
| `WG_RW` | String | Nomor Rukun Warga (RW) | `012` |
| `WG_ALAMAT` | String | Nama jalan / kompleks utama | `Jalan Nirwana` |
| `WG_KELURAHAN` | String | Kelurahan domisili | `BABAKAN` |
| `WG_KECAMATAN` | String | Kecamatan domisili | `SETU` |
| `WG_KOTA` | String | Kota domisili | `TANGERANG SELATAN` |
| `WG_PROVINSI` | String | Provinsi domisili | `BANTEN` |
| `WG_IURAN_BULANAN` | Integer | Nominal tagihan iuran wajib per bulan (Rupiah) | `150000` |
| `WG_FINANCE_PERIOD_START` | Integer | Tahun awal pelaporan laporan keuangan keuangan | `2018` |
| **Telegram Bot** | | | |
| `TELEGRAM_BOT_TOKEN` | String | Token API dari @BotFather Telegram | - |
| `BOT_API_USER` | String | Username API lokal untuk otentikasi Telegram Bot | `bot_api` |
| `BOT_API_PASS` | String | Password API lokal untuk otentikasi Telegram Bot | - |
| `SITE_URL` | String | Base URL backend Django untuk bot memanggil API | `http://localhost:8000` |
| `TELEGRAM_ALLOWED_USERS`| String | Daftar username telegram yang diizinkan (dipisah koma) | `robert,adinda` |
| **AI OCR KTP** | | | |
| `KTP_AI_PROVIDER` | String | Penyedia model AI OCR (`ollama` atau `openrouter`) | `ollama` |
| `OLLAMA_API_URL` | String | Endpoint API Ollama lokal | `http://localhost:11434` |
| `OLLAMA_MODEL` | String | Model visi Ollama yang dipakai | `llama3.2-vision` |
| `OPENROUTER_API_KEY` | String | API key OpenRouter jika memakai cloud model | - |
| `OPENROUTER_MODEL` | String | Model visi OpenRouter yang dipakai | `google/gemini-2.5-flash` |
| `OPENROUTER_QUOTA_THRESHOLD`| Float | Batas sisa saldo API key OpenRouter untuk peringatan quota | `1.0` |
| **Google Sheets Export** | | | |
| `GOOGLE_CRED_PATH` | String | Path file kredensial JSON Google Service Account | - |
| `GOOGLE_DRIVE_USER` | String | Alamat email user Google Drive tujuan share file export | - |

---

## Docker

Untuk menjalankan dengan Docker, **Google Sheets export** membutuhkan file JSON service account yang di-**mount** ke dalam container. `GOOGLE_CRED_PATH` harus mengacu ke **path di dalam container**, bukan path di host.

Contoh perintah docker run:

```bash
docker run -d \
  --link <dbcontainer>:pgdb \
  -p 8000:8000 \
  --env-file /path/to/your/.env \
  --name datawarga \
  -v /path/to/your/service-account.json:/app/datawarga/google-creds.json \
  -v /path/to/your/media:/app/datawarga/media \
  -e GOOGLE_CRED_PATH=/app/datawarga/google-creds.json \
  robeevanjava/datawarga:2.1.1
```

- `-v /path/to/your/service-account.json:/app/datawarga/google-creds.json` — mount file kredensial ke path di dalam container.
- `-v /path/to/your/media:/app/datawarga/media` — mount direktori media dari host ke container agar file yang di-upload (seperti foto profil, bukti bayar, dan foto KTP) tersimpan secara persisten di host machine.
- `-e GOOGLE_CRED_PATH=/app/datawarga/google-creds.json` — path ini harus path **di dalam container** tempat file JSON ter-mount.

Tanpa mount untuk media, file-file yang di-upload akan hilang setiap kali container di-restart atau di-recreate. Tanpa mount untuk Google credentials, file kredensial tidak ada di dalam container dan export ke Google Sheets akan gagal.

---

## Production Deployment

Untuk melakukan deployment production, mohon ikuti best practice dari Django sendiri. Referensi:
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/)
- [Serving Static Files in Production](https://docs.djangoproject.com/en/4.1/howto/static-files/deployment/#serving-static-files-in-production)
- [Django in the Wild: Tips for Deployment Survival](https://www.freecodecamp.org/news/django-in-the-wild-tips-for-deployment-survival-9b491081c2e4/)

---

## Kontribusi

Anda dapat berkontribusi dengan melakukan fork dan / atau mengajukan Pull Request. Jika ada bug atau sesuatu yang ingin ditingkatkan, silakan mengisi "Issue" di repositori.
