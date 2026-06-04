# Panduan Keamanan, MFA & Proteksi Berkas Media

Sistem DataWarga menerapkan standar keamanan tinggi untuk melindungi data kependudukan sensitif. Dokumen ini menjelaskan mekanisme deteksi brute-force (lockout), verifikasi login Multi-Factor Authentication (MFA), dan proteksi berkas media (protected serve).

---

## 1. Mekanisme Proteksi Brute-Force Login (Lockout)

Untuk melindungi akun pengurus dan warga dari serangan pencurian kata sandi secara berulang (brute-force), sistem menerapkan custom backend otentikasi **`LockoutBackend`** yang didefinisikan dalam [auth_backends.py](file:///Users/robertusnegoro/workingdir/repo/datawarga/datawarga/kependudukan/auth_backends.py).

### Aturan Batasan Login:
1. **Kegagalan Login Pertama & Kedua**: Upaya login dicatat. Kolom `failed_login_attempts` pada model `UserProfile` bertambah.
2. **Kegagalan Login Ketiga (3x)**:
   - Akun mengalami **Shadow Ban** (dikunci sementara) selama **30 menit**.
   - Kolom `shadow_ban_expires_at` disetel menjadi waktu saat ini + 30 menit.
   - Setiap upaya login baru dalam rentang waktu ini akan langsung diblokir secara otomatis tanpa memeriksa kata sandi.
3. **Kegagalan Login Keenam (6x)**:
   - Akun mengalami **Lockout Permanen**.
   - Kolom `is_permanently_locked` diubah menjadi `True` dan status user `is_active` diubah menjadi `False`.
   - Akun tidak dapat digunakan lagi sampai dibuka kembali secara manual oleh Administrator.

### Reset Logika:
- Jika pengguna berhasil login dengan kredensial yang valid sebelum menyentuh batas lockout permanen, maka kolom `failed_login_attempts` dan `shadow_ban_expires_at` akan otomatis di-reset menjadi `0` dan `None`.

### Penanganan Akun Terkunci oleh Admin:
Melalui halaman **Admin Panel User Management** (`/warga/admin/users/`), Administrator dapat:
- **Membuka Kunci (Unblock User)**: Mengubah status `is_active` menjadi `True`, me-reset jumlah kegagalan login, dan membersihkan ban expired time.
- **Memblokir User (Block User)**: Menonaktifkan user secara langsung sehingga tidak dapat melakukan login sama sekali.

---

## 2. Autentikasi Dua Faktor (MFA / 2FA)

Sistem DataWarga mendukung autentikasi dua faktor (Multi-Factor Authentication) berbasis waktu (**TOTP**) menggunakan aplikasi autentikator standar (seperti Google Authenticator, Authy, Microsoft Authenticator).

### Alur Aktivasi MFA oleh Pengguna:
1. Masuk ke halaman profil pengurus di `/profile/` dan klik menu **Setup MFA**.
2. Sistem akan menghasilkan secret key TOTP acak sepanjang 32 karakter dan menyimpannya di kolom `totp_secret` pada model `UserProfile`.
3. Halaman web akan memuat gambar kode QR berisi URI otentikator.
4. Pengguna memindai kode QR tersebut menggunakan aplikasi otentikator di ponsel mereka.
5. Pengguna memasukkan 6-digit kode OTP yang muncul untuk memverifikasi dan mengaktifkan MFA (`mfa_enabled = True`).

### Alur Proses Login dengan MFA:
1. Pengguna memasukkan Username dan Password di halaman login utama.
2. Sistem memeriksa apakah profil pengguna mengaktifkan MFA.
3. Jika aktif, Django memproses otentikasi awal namun menahan sesi login sementara, dan mengalihkan browser pengguna ke halaman verifikasi OTP (`/accounts/login/mfa/`).
4. Pengguna harus memasukkan 6-digit token aktif dari aplikasi autentikator di ponselnya untuk menyelesaikan verifikasi login dan dialihkan ke dashboard utama.

> [!TIP]
> Jika pengguna kehilangan ponsel atau tidak sengaja menghapus aplikasi autentikator sehingga tidak bisa login, Administrator dapat mereset status MFA pengguna tersebut melalui Admin Panel User Management dengan mengklik tombol **Reset MFA**.

---

## 3. Perlindungan Dokumen Media Sensitif (Protected Serve)

Secara default, berkas yang diunggah di Django (seperti foto KTP, foto profil, dan dokumen transfer bukti bayar) disimpan dalam folder `media/` dan dapat diakses langsung secara publik via URL. Hal ini berpotensi membocorkan data pribadi warga (seperti NIK dan foto KTP).

Untuk mencegah hal tersebut, DataWarga menggunakan fungsi **`protected_serve`** di [warga.py](file:///Users/robertusnegoro/workingdir/repo/datawarga/datawarga/kependudukan/views/warga.py#L442-L462) yang dipetakan ke url pattern media di [urls.py](file:///Users/robertusnegoro/workingdir/repo/datawarga/datawarga/kependudukan/urls.py#L179-L183).

### Cara Kerja Proteksi Akses Berkas:
1. Setiap permintaan berkas media yang dimulai dengan `/media/` akan diarahkan ke view `protected_serve` alih-alih dilayani langsung oleh server web statik.
2. Sistem memeriksa status login pengguna:
   - **Melalui Session Web**: Pengguna harus sudah login di browser.
   - **Melalui API JWT Token**: Berguna untuk permintaan dari Telegram Bot, sistem akan mengekstrak header `Authorization: Bearer <token>` dan memverifikasinya menggunakan *JWTAuthentication*.
3. **Hasil Evaluasi**:
   - Jika pengguna terverifikasi telah masuk, server akan mengembalikan file media tersebut.
   - Jika permintaan berasal dari API luar tanpa otentikasi JWT yang valid, sistem mengembalikan respon HTTP status **401 Unauthorized**.
   - Jika permintaan berasal dari browser web umum yang belum login, sistem akan mengalihkan pengguna ke halaman login utama (`/accounts/login/`) dengan melampirkan parameter redirect `?next=` ke file media asal.
