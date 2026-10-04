# 🎱 Billiard Hub

Aplikasi web **reservasi meja billiard** berbasis **Flask** dan **MySQL**. Pengguna dapat mendaftar, memesan meja per paket waktu menggunakan saldo **KAIA Coin**, membeli paket **membership**, dan melakukan **top-up** saldo — lengkap dengan dashboard pemantauan sisa waktu booking secara real-time.

> Database didukung MySQL lokal (XAMPP/Laragon) maupun **TiDB Serverless**

---

## ✨ Fitur

| Fitur | Keterangan |
|---|---|
| 🔐 Autentikasi | Registrasi, login, logout, dan edit profil (session-based) |
| 🎯 Booking Meja | Paket **Malam**, **Murah (Happy Hour)**, dan **Reguler** — dibayar dengan KAIA Coin per increment waktu |
| 💳 Pembayaran | Pembayaran via QRIS untuk top-up & pembelian produk |
| 👑 Membership | Tier **Perunggu** (3 hari), **Silver** (7 hari), **Gold** (7 hari) |
| 🪙 KAIA Coin | Dompet koin in-app: top-up Rp 25.000 – Rp 500.000, dengan log transaksi |
| 📊 Dashboard | Pemantauan sisa waktu booking (zona WIB) dan pembatalan booking |
| ⏱️ Auto-expire | Membership & booking kedaluwarsa otomatis diperbarui di database |

## 🛠️ Teknologi

- **Backend:** Python 3 + Flask 3
- **Database:** MySQL / TiDB Serverless (PyMySQL)
- **Frontend:** Jinja2 template + static assets
- **Deploy:** Vercel (serverless, zero-config)

## 📁 Struktur Proyek

```
├── app.py              # Entrypoint Vercel (mengimpor app dari myapp.py)
├── myapp.py            # Seluruh logika & route aplikasi
├── schema.sql          # Skema database (user, topup_log)
├── requirements.txt    # Dependensi Python
├── vercel.json         # Konfigurasi deploy Vercel
├── .env.example        # Contoh konfigurasi environment
├── public/static/      # Aset statis (CSS/JS/gambar)
└── templates/          # Template Jinja2 (auth, dashboard, payment, dll.)
```

## 🚀 Menjalankan Secara Lokal

1. **Clone repo & siapkan virtual environment**

   ```bash
   git clone https://github.com/gawns/billiard-hub.git
   cd billiard-hub
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

2. **Install dependensi**

   ```bash
   pip install -r requirements.txt
   ```

3. **Buat database**

   ```bash
   mysql -u root -p < schema.sql
   ```

4. **Konfigurasi environment**

   Salin `.env.example` menjadi `.env`, lalu sesuaikan:

   ```env
   # MySQL lokal (XAMPP/Laragon)
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASS=
   DB_NAME=billard_hub

   # Atau TiDB/PlanetScale via DATABASE_URL (mengesampingkan konfigurasi di atas)
   # DATABASE_URL=mysql://user:password@host:4000/billard_hub

   # Wajib untuk sesi login
   SECRET_KEY=ganti-dengan-string-acak-64-karakter
   ```

   > Generator `SECRET_KEY`: `python -c "import secrets;print(secrets.token_hex(32))"`

5. **Jalankan aplikasi**

   ```bash
   python myapp.py
   ```

   Buka `http://127.0.0.1:5000` di browser.

## ☁️ Deploy ke Vercel

1. Push repo ini ke GitHub, lalu import di [Vercel](https://vercel.com/new).
2. Vercel otomatis mendeteksi `app.py` sebagai WSGI handler (tanpa build command).
3. Set **Environment Variables** di dashboard Vercel:
   - `DATABASE_URL` — koneksi MySQL/TiDB (TLS aktif otomatis)
   - `SECRET_KEY` — string acak 64 karakter
4. Deploy. Folder `templates/` ikut ter-bundle berkat konfigurasi `includeFiles` di `vercel.json`.

## 🗄️ Skema Database

| Tabel | Fungsi |
|---|---|
| `user` | Akun pengguna: kredensial, tier membership, saldo KAIA Coin, booking aktif |
| `topup_log` | Riwayat top-up koin (jumlah koin, nominal rupiah, waktu) |

Skema lengkap tersedia di [`schema.sql`](schema.sql).

---

Dibuat sebagai proyek pengembangan web (UTS Basis Data) — Flask × MySQL.
