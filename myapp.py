from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql.cursors
import pymysql.err
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import math
import os
import re
from urllib.parse import unquote
import random
import pytz 

# --- (BARU) Muat variabel lingkungan dari .env saat pengembangan lokal ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Konfigurasi Aplikasi ---
# Aset statis ada di public/static: di Vercel folder public/ disajikan CDN,
# dan local dev tetap bisa memakai url_for('static', ...) tanpa BuildError.
app = Flask(__name__, static_folder='public/static', static_url_path='/static')


IS_PROD = os.environ.get('VERCEL') == '1' or os.environ.get('FLASK_ENV') == 'production'
if IS_PROD:
    # Vercel berada di belakang proxy: tanpa ini url_for()/redirect jadi http atau salah host.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# --- KONFIGURASI MYSQL (dibaca dari environment variable, lihat .env.example) ---
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', '')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_NAME = os.environ.get('DB_NAME', 'billard_hub')

# DATABASE_URL (mis. dari TiDB/PlanetScale) lebih diprioritaskan daripada DB_HOST.
# contoh: mysql://user:pass@gateway.prod.regio1.ti-db.cloud:4000/billard_hub?ssl_verify=true
DB_URL = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
DB_SSL = None
if DB_URL and '://' in DB_URL:
    _m = re.match(r'(?:mysql|mysql\+pymysql)://(?P<u>[^:]*):(?P<p>[^@]*)@(?P<h>[^/:]+):?(?P<port>\d*)/(?P<db>[^?\s]+)',
                  DB_URL)
    if not _m:
        raise RuntimeError(f'Format DATABASE_URL tidak dikenali: {DB_URL}')
    DB_USER = _m.group('u') or DB_USER
    DB_PASS = unquote(_m.group('p'))
    DB_HOST = _m.group('h')
    DB_PORT = int(_m.group('port') or 3306)
    DB_NAME = unquote(_m.group('db')).split('?')[0]
    if os.environ.get('DB_SSL', '1') not in ('0', 'false', 'off'):
        # PyMySQL: ssl={} diperlakukan SAMA dengan tidak pakai SSL, jadi selalu isi
        # 'verify_mode' eksplisit. CA diverifikasi hanya jika bundle CA tersedia
        # (di Vercel: /etc/ssl/certs). Set DB_SSL=0 untuk MySQL tanpa TLS.
        _ca = os.environ.get('DB_SSL_CA') or next(
            (p for p in ('/etc/ssl/certs/ca-certificates.crt', '/etc/ssl/certs/ca-bundle.crt')
             if os.path.exists(p)), None)
        DB_SSL = ({'ca': _ca, 'verify_mode': True} if _ca
                  else {'verify_mode': False, 'check_hostname': False})


app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ganti-ini-dengan-kunci-rahasia-yang-sangat-rumit')
if IS_PROD:
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=True, PERMANENT_SESSION_LIFETIME=timedelta(hours=6))

# --- Zona Waktu ---
WIB = pytz.timezone('Asia/Jakarta')

# --- Fungsi Bantuan Koneksi Database ---
def get_db_connection():
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=8,
            ssl=DB_SSL
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"Error saat menghubungkan ke database: {e}")
        return None

# --- (DIRALAT) Data Produk (Harga KAIA Coin) ---
PRODUCTS = {
    "booking": {
        "malam": {"name": "Paket Malam", "price_per_increment": 10, "increment_minutes": 60},
        # (BARU) Paket Murah: 10 Coin dapat 180 menit (3 jam)
        "murah": {"name": "Paket Murah (Happy Hour)", "price_per_increment": 10, "increment_minutes": 180},
        "reguler": {"name": "Reguler", "price_per_increment": 10, "increment_minutes": 60}
    },
    "membership": {
        "perunggu": {"name": "Membership Perunggu", "price": 20, "duration_days": 3},
        "silver": {"name": "Membership Silver", "price": 100, "duration_days": 7},
        "gold": {"name": "Membership Gold", "price": 500, "duration_days": 7}
    },
    "topup": {
        "topup10": {"name": "10 KAIA Coin", "price_cash": 25000, "kaia_reward": 10},
        "topup30": {"name": "30 KAIA Coin", "price_cash": 70000, "kaia_reward": 30},
        "topup50": {"name": "50 KAIA Coin", "price_cash": 125000, "kaia_reward": 50},
        "topup100": {"name": "100 KAIA Coin", "price_cash": 200000, "kaia_reward": 100},
        "topup200": {"name": "200 KAIA Coin", "price_cash": 350000, "kaia_reward": 200},
        "topup300": {"name": "300 KAIA Coin", "price_cash": 500000, "kaia_reward": 300}
    }
}

# --- Fungsi Helper Sisa Waktu ---
def get_remaining_time(expiry_dt, show_seconds=False):
    if not expiry_dt:
        return None
    now = datetime.utcnow()
    remaining = expiry_dt - now

    if remaining.total_seconds() <= 0:
        return "Telah berakhir"
        
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0:
        parts.append(f"{hours} jam")
    if minutes > 0:
        parts.append(f"{minutes} menit")
    
    if show_seconds and days == 0 and hours == 0 and minutes < 10:
         parts.append(f"{seconds} detik")

    if not parts:
        if show_seconds:
            return f"{seconds} detik"
        else:
            return "Kurang dari 1 menit"
        
    return ", ".join(parts)

# --- Fungsi Helper Format Waktu (Jam & Menit) ---
def format_time_spent(total_seconds):
    if total_seconds == 0:
        return "0 menit"
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} jam")
    if minutes > 0:
        parts.append(f"{minutes} menit")
    
    return ", ".join(parts) if parts else "0 detik"


# --- Routes (Halaman) ---

@app.route('/')
def dashboard():
    if 'user_id' in session:
        return redirect(url_for('dashboard_user'))
    return render_template('dashboard.html')
# ... (impor Anda lainnya)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if conn is None: 
                flash('Koneksi database gagal.', 'error')
                # (RALAT) Kembali ke halaman register jika gagal
                return render_template('auth.html', panel='register') 
            
            cursor = conn.cursor()
            # (RALAT) Memberi 50 koin saat registrasi
            sql = "INSERT INTO user (username, email, password, membership_tier, kaia_coin, total_rupiah_spent) VALUES (%s, %s, %s, 'Biasa', 50, 0.0)"
            cursor.execute(sql, (username, email, password))
            conn.commit()
            flash('Registrasi berhasil! Anda mendapat 50 KAIA Coin gratis. Silakan login.', 'success')
            return redirect(url_for('login'))
        
        except pymysql.err.IntegrityError:
            if conn: conn.rollback()
            flash('Username atau Email sudah terdaftar.', 'error')
            # (RALAT) Kembali ke halaman register jika gagal
            return render_template('auth.html', panel='register') 
            
        except Exception as e:
            if conn: conn.rollback()
            flash(f'Terjadi error: {e}', 'error')
            # (RALAT) Kembali ke halaman register jika gagal
            return render_template('auth.html', panel='register') 
            
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # (BARU) Tampilkan halaman auth dengan panel register aktif
    return render_template('auth.html', panel='register')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if conn is None: 
                flash('Koneksi database gagal.', 'error')
                return render_template('auth.html', panel='login')
                
            cursor = conn.cursor()
            sql = "SELECT * FROM user WHERE email = %s"
            cursor.execute(sql, (email,))
            user = cursor.fetchone()
            
            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['membership_tier'] = user.get('membership_tier', 'Biasa')
                session['kaia_coin'] = user.get('kaia_coin', 0)
                # (RALAT) Arahkan ke dashboard_user setelah login
                return redirect(url_for('dashboard_user')) 
            else:
                flash('Email atau password salah.', 'error')
                # (RALAT) Kembali ke halaman login jika gagal
                return render_template('auth.html', panel='login') 
        except Exception as e:
            flash(f'Terjadi error saat login: {e}', 'error')
            return render_template('auth.html', panel='login')
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
            
    # (BARU) Tampilkan halaman auth dengan panel login aktif
    return render_template('auth.html', panel='login')

@app.route('/dashboard_user')
def dashboard_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = None
    cursor = None
    user_data = {}
    now_utc = datetime.utcnow()
    try:
        conn = get_db_connection()
        if conn is None: return redirect(url_for('login'))
        cursor = conn.cursor()
        sql = "SELECT booking_expiry, membership_expiry FROM user WHERE id = %s"
        cursor.execute(sql, (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            user_data['booking_expiry'] = parse_db_datetime(user_data.get('booking_expiry'))
            user_data['membership_expiry'] = parse_db_datetime(user_data.get('membership_expiry'))
        else:
            return redirect(url_for('logout')) 
    except Exception as e:
        print(f"Error di dashboard_user: {e}")
        flash('Gagal memuat data user.', 'error')
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return render_template('dashboardafterlogin.html', 
                           username=session['username'],
                           user=user_data, 
                           now=now_utc) 

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('dashboard'))

def parse_db_datetime(dt_str):
    if isinstance(dt_str, str):
        try:
            try:
                return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
    return dt_str

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = None
    cursor = None
    
    username_cooldown_error = None
    password_cooldown_error = None

    try:
        conn = get_db_connection()
        if conn is None: return redirect(url_for('login'))
        cursor = conn.cursor()

        sql_select = "SELECT * FROM user WHERE id = %s"
        cursor.execute(sql_select, (user_id,))
        user = cursor.fetchone()

        if not user:
            return redirect(url_for('logout'))
        
        user['membership_expiry'] = parse_db_datetime(user.get('membership_expiry'))
        user['booking_expiry'] = parse_db_datetime(user.get('booking_expiry'))
        user['booking_start_time'] = parse_db_datetime(user.get('booking_start_time'))
        user['username_last_changed'] = parse_db_datetime(user.get('username_last_changed'))
        user['password_last_changed'] = parse_db_datetime(user.get('password_last_changed'))

        now = datetime.utcnow()
        one_hour_cooldown = timedelta(hours=1)

        if request.method == 'POST':
            if 'change_username' in request.form:
                new_username = request.form['username'].strip()
                if user['username_last_changed'] and (now < user['username_last_changed'] + one_hour_cooldown):
                    cooldown_end = user['username_last_changed'] + one_hour_cooldown
                    time_remaining = get_remaining_time(cooldown_end, show_seconds=True)
                    username_cooldown_error = f"Tidak dapat mengganti nama, harap tunggu {time_remaining}"
                elif not new_username:
                    username_cooldown_error = "Username tidak boleh kosong."
                elif new_username == user['username']:
                    username_cooldown_error = "Username baru sama dengan username lama."
                else:
                    try:
                        sql_update_user = "UPDATE user SET username = %s, username_last_changed = %s WHERE id = %s"
                        cursor.execute(sql_update_user, (new_username, now, user_id))
                        conn.commit()
                        session['username'] = new_username
                        user['username'] = new_username
                        user['username_last_changed'] = now
                        flash('Username berhasil diperbarui!', 'success')
                    except pymysql.err.IntegrityError:
                        conn.rollback()
                        username_cooldown_error = "Username tersebut sudah digunakan."
            elif 'change_password' in request.form:
                old_password = request.form['old_password']
                new_password = request.form['new_password']
                confirm_new_password = request.form['confirm_new_password']
                if user['password_last_changed'] and (now < user['password_last_changed'] + one_hour_cooldown):
                    cooldown_end = user['password_last_changed'] + one_hour_cooldown
                    time_remaining = get_remaining_time(cooldown_end, show_seconds=True)
                    password_cooldown_error = f"Tidak dapat mengganti password, harap tunggu {time_remaining}"
                elif user['password'] != old_password:
                    password_cooldown_error = "Password lama Anda salah."
                elif new_password != confirm_new_password:
                    password_cooldown_error = "Password baru tidak cocok dengan konfirmasi."
                elif len(new_password) < 4:
                    password_cooldown_error = "Password baru minimal 4 karakter."
                elif new_password == old_password:
                    password_cooldown_error = "Password baru tidak boleh sama dengan password lama."
                else:
                    sql_update_pass = "UPDATE user SET password = %s, password_last_changed = %s WHERE id = %s"
                    cursor.execute(sql_update_pass, (new_password, now, user_id))
                    conn.commit()
                    user['password_last_changed'] = now
                    flash('Password berhasil diperbarui!', 'success')
            
            if not username_cooldown_error and not password_cooldown_error and request.method == 'POST':
                 return redirect(url_for('edit_profile'))

        # === LOGIKA GET ===
        membership_remaining = get_remaining_time(user['membership_expiry'])
        booking_remaining = get_remaining_time(user['booking_expiry'])

        if not username_cooldown_error and user['username_last_changed'] and (now < user['username_last_changed'] + one_hour_cooldown):
            cooldown_end = user['username_last_changed'] + one_hour_cooldown
            time_remaining = get_remaining_time(cooldown_end, show_seconds=True)
            username_cooldown_error = f"Tidak dapat mengganti nama, harap tunggu {time_remaining}"
        if not password_cooldown_error and user['password_last_changed'] and (now < user['password_last_changed'] + one_hour_cooldown):
            cooldown_end = user['password_last_changed'] + one_hour_cooldown
            time_remaining = get_remaining_time(cooldown_end, show_seconds=True)
            password_cooldown_error = f"Tidak dapat mengganti password, harap tunggu {time_remaining}"

        booking_total_duration_formatted = None
        if user['booking_start_time'] and user['booking_expiry']:
            duration_seconds = (user['booking_expiry'] - user['booking_start_time']).total_seconds()
            booking_total_duration_formatted = format_time_spent(int(duration_seconds))

        total_rupiah_spent = user.get('total_rupiah_spent', 0)
        
        if user['membership_expiry'] and user['membership_expiry'] < now:
            cursor.execute("UPDATE user SET membership_tier = 'Biasa', membership_expiry = NULL WHERE id = %s", (user_id,))
            conn.commit()
            session['membership_tier'] = 'Biasa'
            user['membership_tier'] = 'Biasa'
            user['membership_expiry'] = None
            membership_remaining = None

        if user['booking_expiry'] and user['booking_expiry'] < now:
            cursor.execute("UPDATE user SET active_booking_id = NULL, booking_expiry = NULL, booking_start_time = NULL WHERE id = %s", (user_id,))
            conn.commit()
            user['active_booking_id'] = None
            user['booking_expiry'] = None
            booking_remaining = None
        
        topup_log = []
        sql_log = "SELECT kaia_amount, rupiah_amount, timestamp FROM topup_log WHERE user_id = %s ORDER BY timestamp DESC LIMIT 5"
        cursor.execute(sql_log, (user_id,))
        topup_log = cursor.fetchall()
        for log in topup_log:
            log['timestamp'] = log['timestamp'].strftime('%d %b %Y, %H:%M')


        return render_template('edit_profile.html', 
                               user=user, 
                               membership_remaining=membership_remaining, 
                               booking_remaining=booking_remaining,
                               booking_total_duration=booking_total_duration_formatted,
                               username_cooldown_error=username_cooldown_error,
                               password_cooldown_error=password_cooldown_error,
                               total_rupiah_spent=total_rupiah_spent,
                               topup_log=topup_log)

    except Exception as e:
        print(f"Error di edit_profile: {e}") 
        flash(f'Terjadi error: {e}', 'error')
        return redirect(url_for('dashboard_user'))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/payment/<string:product_type>/<string:item_id>', methods=['GET', 'POST'])
def payment(product_type, item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        product = PRODUCTS.get(product_type, {}).get(item_id)
        if not product:
            flash('Produk tidak ditemukan.', 'error')
            return redirect(url_for('dashboard_user'))
    except Exception:
        return redirect(url_for('dashboard_user'))

    user_id = session['user_id']
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        if conn is None: return redirect(url_for('dashboard_user'))
        cursor = conn.cursor()
        
        sql_select = "SELECT email, password, kaia_coin, membership_expiry, booking_expiry FROM user WHERE id = %s"
        cursor.execute(sql_select, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return redirect(url_for('logout'))
        
        user['membership_expiry'] = parse_db_datetime(user.get('membership_expiry'))
        user['booking_expiry'] = parse_db_datetime(user.get('booking_expiry'))

        if request.method == 'POST':
            email_form = request.form['email']
            password_form = request.form['password']

            if email_form != user['email'] or password_form != user['password']:
                flash('Email atau Password validasi salah.', 'error')
                return render_template('payment.html', product=product, product_type=product_type, item_id=item_id, user_email=user['email'])

            now = datetime.utcnow()

            if product_type == 'booking':
                try:
                    duration_units = int(request.form.get('duration_slider', 1)) 
                    duration_minutes = duration_units * product['increment_minutes']
                    total_price = duration_units * product['price_per_increment']
                except ValueError:
                    flash('Durasi tidak valid.', 'error')
                    return redirect(url_for('payment', product_type=product_type, item_id=item_id))
                
                if user['kaia_coin'] < total_price:
                    flash(f"KAIA Coin Anda tidak cukup. Butuh {total_price} KAIA@.", 'error')
                    return redirect(url_for('payment', product_type=product_type, item_id=item_id))

                now_wib = pytz.utc.localize(now).astimezone(WIB)
                # Validasi Waktu Paket Malam
                if item_id == 'malam':
                    wib_hour = now_wib.hour
                    if not (wib_hour >= 18 or wib_hour < 6):
                        flash('Paket Malam hanya berlaku pukul 18:00 - 06:00 WIB.', 'error')
                        return redirect(url_for('payment', product_type=product_type, item_id=item_id))
                
                # (BARU) Validasi Waktu Paket Murah
                elif item_id == 'murah':
                    wib_hour = now_wib.hour
                    # Hanya boleh dibeli antara jam 12 siang (>=12) sampai sebelum jam 3 sore (<15)
                    if not (wib_hour >= 12 and wib_hour < 15):
                         flash('Paket Murah hanya berlaku pukul 12:00 - 15:00 WIB.', 'error')
                         return redirect(url_for('payment', product_type=product_type, item_id=item_id))

                current_expiry = user['booking_expiry']
                start_time_for_db = None
                
                if current_expiry and current_expiry > now:
                    start_time = current_expiry
                else:
                    start_time = now
                    start_time_for_db = now
                    
                duration = timedelta(minutes=duration_minutes)
                expiry_time = start_time + duration
                
                if start_time_for_db:
                    sql = "UPDATE user SET kaia_coin = kaia_coin - %s, active_booking_id = %s, booking_expiry = %s, booking_start_time = %s WHERE id = %s"
                    cursor.execute(sql, (total_price, item_id, expiry_time, start_time_for_db, user_id))
                else:
                    sql = "UPDATE user SET kaia_coin = kaia_coin - %s, booking_expiry = %s WHERE id = %s"
                    cursor.execute(sql, (total_price, expiry_time, user_id))
                
                conn.commit()
                session['kaia_coin'] = user['kaia_coin'] - total_price
                
                # Hitung durasi dalam jam untuk pesan sukses
                hours_bought = duration_minutes // 60
                flash(f"Berhasil membeli {product['name']} (+{hours_bought} Jam)!", 'success')


            elif product_type == 'membership':
                total_price = product['price']
                
                if user['kaia_coin'] < total_price:
                    flash(f"KAIA Coin Anda tidak cukup. Butuh {total_price} KAIA@.", 'error')
                    return redirect(url_for('payment', product_type=product_type, item_id=item_id))

                current_expiry = user['membership_expiry']
                start_time = current_expiry if current_expiry and current_expiry > now else now
                duration = timedelta(days=product['duration_days'])
                expiry_time = start_time + duration
                tier_name = item_id.capitalize()
                
                sql = "UPDATE user SET kaia_coin = kaia_coin - %s, membership_tier = %s, membership_expiry = %s WHERE id = %s"
                cursor.execute(sql, (total_price, tier_name, expiry_time, user_id))
                conn.commit()
                
                session['kaia_coin'] = user['kaia_coin'] - total_price
                session['membership_tier'] = tier_name
                flash(f"Berhasil membeli {product['name']}!", 'success')
            
            elif product_type == 'topup':
                kaia_reward = product['kaia_reward']
                price_cash = product['price_cash']
                
                sql_update = "UPDATE user SET kaia_coin = kaia_coin + %s, total_rupiah_spent = total_rupiah_spent + %s WHERE id = %s"
                cursor.execute(sql_update, (kaia_reward, price_cash, user_id))
                
                sql_log = "INSERT INTO topup_log (user_id, kaia_amount, rupiah_amount) VALUES (%s, %s, %s)"
                cursor.execute(sql_log, (user_id, kaia_reward, price_cash))
                
                sql_cleanup = """
                    DELETE FROM topup_log 
                    WHERE user_id = %s AND id NOT IN (
                        SELECT id FROM (
                            SELECT id FROM topup_log 
                            WHERE user_id = %s 
                            ORDER BY timestamp DESC 
                            LIMIT 5
                        ) AS T
                    )
                """
                cursor.execute(sql_cleanup, (user_id, user_id))

                conn.commit()
                
                session['kaia_coin'] = user['kaia_coin'] + kaia_reward
                flash(f"Berhasil Topup {product['name']}!", 'success')

            return redirect(url_for('edit_profile'))

        return render_template('payment.html', 
                               product=product, 
                               product_type=product_type, 
                               item_id=item_id, 
                               user_email=user['email'])

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error di payment: {e}") 
        flash(f'Terjadi error: {e}', 'error')
        return redirect(url_for('dashboard_user'))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/cancel_status', methods=['POST'])
def cancel_status():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cancel_type = request.form.get('cancel_type')
    user_id = session['user_id']
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None: return redirect(url_for('edit_profile'))
        cursor = conn.cursor()
        if cancel_type == 'membership':
            sql = "UPDATE user SET membership_tier = 'Biasa', membership_expiry = NULL WHERE id = %s"
            cursor.execute(sql, (user_id,))
            conn.commit()
            session['membership_tier'] = 'Biasa'
            flash('Membership berhasil dibatalkan.', 'success')
        elif cancel_type == 'booking':
            sql = "UPDATE user SET active_booking_id = NULL, booking_expiry = NULL, booking_start_time = NULL WHERE id = %s"
            cursor.execute(sql, (user_id,))
            conn.commit()
            flash('Booking berhasil dibatalkan.', 'success')
    except Exception as e:
        if conn: conn.rollback()
        flash(f'Terjadi error: {e}', 'error')
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for('edit_profile'))

# --- Menjalankan Aplikasi ---
if __name__ == '__main__':
    app.run(debug=True)