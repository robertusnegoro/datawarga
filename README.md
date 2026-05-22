# DataWarga

Data warga adalah aplikasi sumber terbuka (_open source_) web berbasis python Django web-framework yang dipergunakan untuk perekaman data warga ditingkat RT atau RW.

## Quick Start

Persiapan : 
- postgresql versi >= 14 ;  buat database e.g `datawarga`

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

Buat file `.env-dev.sh` yang isinya e.g :

```bash
export DATA_WARGA_SECRET="<isi dengan generated secret>"
export DB_HOST="localhost"
export DB_NAME="datawarga"
export DB_PASS="katasandi-postgres-anda"
export DB_PORT="5432"
export DB_USER="database-user-postgres-anda"
```

untuk DATA_WARGA_SECRET, dapat mengikuti [tutorial ini](https://www.educative.io/answers/how-to-generate-a-django-secretkey).

kemudian :
```bash
source .env.sh
cd datawarga
python manage.py migrate
python manage.py runserver 18000
```

Buka browser dan akses http://localhost:18000

### 4. Konfigurasi Sistem via Django Admin

Beberapa pengaturan sistem hanya dapat dikonfigurasi melalui halaman **Django Admin** (`/admin`). Untuk mengaksesnya, pastikan Anda telah membuat akun *superuser*:

```bash
python manage.py createsuperuser
```

Masuk ke `http://localhost:18000/admin` menggunakan akun tersebut. Berikut adalah konfigurasi penting yang perlu disiapkan:

#### A. Warga Permission Group (Hak Akses Data)
Sistem mendukung pembatasan akses data warga. Fitur ini digunakan untuk mengatur agar pengguna (user) tertentu hanya dapat mengelola data warga di wilayah/kompleks tertentu.
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

## Docker

Untuk menjalankan dengan Docker, **Google Sheets export** membutuhkan file JSON service account yang di-**mount** ke dalam container. `GOOGLE_CRED_PATH` harus mengacu ke **path di dalam container**, bukan path di host.

Contoh:

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

## Production Deployment

Untuk melakukan deployment production, mohon ikuti best practice dari Django sendiri. Referesi : 
- https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/
- https://docs.djangoproject.com/en/4.1/howto/static-files/deployment/#serving-static-files-in-production
- https://www.freecodecamp.org/news/django-in-the-wild-tips-for-deployment-survival-9b491081c2e4/


## Kontribusi
Anda dapat berkontribusi dengan melakukan fork dan / atau mengajukan Pull Request. Jika ada bug atau sesuatu yang ingin diimprove, sila mengisi "Issue".
