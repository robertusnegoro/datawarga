# Panduan Telegram Bot & Integrasi AI OCR

Sistem DataWarga dilengkapi dengan Telegram Bot interaktif yang terhubung langsung ke backend Django. Bot ini memungkinkan pengurus RT/RW mengelola data warga secara mobile, serta memanfaatkan teknologi AI (vision model) untuk memindai KTP (OCR) secara instan.

---

## 1. Persiapan & Instalasi Telegram Bot

Ikuti langkah-langkah berikut untuk mengaktifkan Telegram Bot:

### Langkah A: Daftarkan Bot di Telegram
1. Buka aplikasi Telegram dan cari user **@BotFather**.
2. Kirim perintah `/newbot` dan ikuti petunjuknya untuk menentukan nama dan username bot.
3. Catat token API HTTP yang diberikan (misalnya: `1234567890:ABCdefGhIJKlmNoPQRsTUVwXyz`).

### Langkah B: Buat Kredensial API di Django Admin
Telegram Bot berkomunikasi dengan Django melalui REST API menggunakan JWT token. Anda harus mendaftarkan user khusus bot di Django Admin:
1. Jalankan server lokal Django Anda, lalu masuk ke `/admin`.
2. Buka menu **Users** -> **Add user**. Buat user baru (contoh username: `bot_api`) dan tentukan password-nya.
3. Setel environment variables `BOT_API_USER` dan `BOT_API_PASS` pada aplikasi Django sesuai dengan kredensial tersebut agar bot dapat melakukan login otomatis ke API.

### Langkah C: Konfigurasikan Environment Variables
Setel variabel lingkungan berikut sebelum menjalankan bot:
```bash
export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGhIJKlmNoPQRsTUVwXyz"
export BOT_API_USER="bot_api"
export BOT_API_PASS="password_akun_bot_anda"
export SITE_URL="http://localhost:8000" # URL server backend Django Anda
export TELEGRAM_ALLOWED_USERS="username1,username2" # Username Telegram pengurus tanpa simbol '@' (pisahkan dengan koma)
```
> [!IMPORTANT]
> Fitur keamanan `TELEGRAM_ALLOWED_USERS` wajib diisi. Bot akan secara otomatis menolak dan memblokir seluruh perintah dari pengguna Telegram yang namanya tidak terdaftar di daftar ini.

### Langkah D: Jalankan Proses Bot
Untuk menjalankan Telegram Bot agar mendengarkan perintah masuk (*long polling*), jalankan perintah berikut:
```bash
python manage.py run_telegram_bot
```

---

## 2. Panduan Perintah Telegram Bot

Telegram Bot mendukung perintah manual berbasis teks dan sesi percakapan terpadu:

### A. Perintah Pencarian Data
- **/start**: Menampilkan salam pembuka dan daftar menu panduan penggunaan bot.
- **/cari `<kata kunci>`**: Mencari warga berdasarkan nama, NIK, No KK, atau alamat.
  *Contoh:* `/cari John` atau `/cari 367406xxx`
- **/rumah `<blok/nomor>`**: Menampilkan daftar seluruh nama anggota keluarga yang tinggal di alamat tersebut.
  *Contoh:* `/rumah J2/5`
- **/iuran `<blok/nomor> [tahun]`**: Memeriksa status riwayat pembayaran iuran bulanan untuk unit rumah tersebut pada tahun yang dipilih. Jika tahun tidak ditulis, sistem otomatis memakai tahun berjalan.
  *Contoh:* `/iuran J2/5 2026`

### B. Pencatatan Iuran Interaktif (`/bayar`)
Perintah `/bayar` akan memulai sesi *State Machine* (percakapan interaktif) untuk memandu pengurus mencatat pembayaran:
1. Bot meminta memasukkan alamat rumah (contoh: `J2/5`).
2. Bot menyajikan pilihan bulan (Januari - Desember) menggunakan tombol menu cepat.
3. Bot meminta memasukkan tahun pembayaran (contoh: `2026`).
4. Bot meminta memasukkan jumlah nominal pembayaran (otomatis menampilkan nominal default e.g. `150000`).
5. Bot meminta pengurus mengunggah/mengirim **foto bukti pembayaran** (transfer bank/kwitansi).
6. Bot menampilkan ringkasan data dan meminta konfirmasi. Pengurus mengetik `ya` untuk menyimpan atau `tidak` untuk membatalkan.
- Perintah **/cancel** dapat diketikkan kapan saja selama proses ini berlangsung untuk membatalkan sesi.

---

## 3. Asisten Chat AI & OCR Scan KTP

Jika pengguna mengirim pesan teks biasa (tanpa diawali garis miring `/`), pesan tersebut akan ditangkap oleh **`AgentService`** kecerdasan buatan.

### A. Cara Kerja Chat Agent AI
1. Pesan dikirimkan ke model AI (menggunakan prompt instruksi khusus [agent.py](file:///Users/robertusnegoro/workingdir/repo/datawarga/datawarga/kependudukan/ai/agent.py)).
2. **Batasan Ruang Lingkup**: AI Agent didesain khusus hanya untuk memproses hal kependudukan dan keuangan DataWarga. Jika pengguna mengajukan pertanyaan di luar konteks (seperti resep masakan, kode pemrograman, matematika umum), agen akan menolak dengan sopan.
3. **Penyusunan Perintah (Tool Use)**: AI model dapat menggunakan fungsi sistem backend (*tools*) secara mandiri untuk mengambil data, seperti:
   - `search_warga` & `get_warga_detail`
   - `search_kompleks` & `get_kompleks_detail`
   - `check_iuran`
   - `add_warga` & `update_warga`
4. Agen memproses hasil tool-use dan membalas chat ke pengguna Telegram dengan bahasa yang santun.

### B. Pemindaian OCR KTP Otomatis
Pengurus dapat memotret KTP warga baru dan mengirimkannya ke Telegram Bot. Alur yang terjadi adalah:
1. Bot mendeteksi kiriman foto dan mengirimkannya ke API OCR AI ([ai_service.py](file:///Users/robertusnegoro/workingdir/repo/datawarga/datawarga/kependudukan/ai/ai_service.py)).
2. Model AI memindai gambar KTP dan mengekstrak field: **NIK, Nama Lengkap, Alamat KTP, Agama, Jenis Kelamin, Tempat Lahir, Tanggal Lahir** dalam bentuk struktur JSON.
3. AI Agent menyusun data tersebut secara rapi, mengirimkannya ke pengurus untuk diverifikasi, dan menanyakan nomor rumah (Kompleks) tempat tinggal warga tersebut untuk langsung disimpan di sistem.

---

## 4. Konfigurasi Engine AI (Ollama vs OpenRouter)

Anda dapat memilih untuk menjalankan engine AI secara lokal (gratis tanpa internet) atau menggunakan cloud API berbayar. Konfigurasikan di `.env` melalui variabel `KTP_AI_PROVIDER`:

### Opsi A: Engine Lokal (Ollama)
Sangat cocok untuk menjaga kerahasiaan data warga karena foto KTP diproses secara lokal di komputer server Anda tanpa dikirim ke internet.
```bash
export KTP_AI_PROVIDER="ollama"
export OLLAMA_API_URL="http://localhost:11434" # Host server Ollama Anda
export OLLAMA_MODEL="llama3.2-vision" # Model Vision yang mendukung pemrosesan gambar
export OLLAMA_API_KEY="" # Isi jika Ollama Anda menggunakan reverse proxy berproteksi auth
```
*Persyaratan:* Pastikan Anda telah menginstal Ollama di server dan mengunduh model vision:
```bash
ollama run llama3.2-vision
```

### Opsi B: Engine Cloud (OpenRouter)
Sangat praktis jika server Anda tidak memiliki GPU untuk menjalankan LLM lokal. Model yang digunakan secara default adalah Gemini milik Google yang sangat akurat dalam membaca teks gambar KTP.
```bash
export KTP_AI_PROVIDER="openrouter"
export OPENROUTER_API_KEY="sk-or-v1-..." # Dapatkan key di openrouter.ai
export OPENROUTER_MODEL="google/gemini-2.5-flash"
export OPENROUTER_QUOTA_THRESHOLD="1.0" # Alert limit jika saldo API tersisa di bawah $1.0
```
Sistem akan memantau quota API Key OpenRouter Anda secara berkala melalui endpoint Key Balance API dan memberikan catatan log peringatan jika kuota mulai menipis.
