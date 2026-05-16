from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
from functools import wraps
import json, os, uuid, secrets
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ucbucaq-restoran-secret-2025')

# ── EMAIL KONFİQURASİYASI ──
# Railway dashboard-da bu dəyişənləri əlavə edin:
#   MAIL_USERNAME = sizin@gmail.com
#   MAIL_PASSWORD = Gmail App Password (boşluqsuz 16 simvol)
#   APP_BASE_URL  = https://sizin-app-adı.up.railway.app
_mail_user = os.environ.get('MAIL_USERNAME', '')
_mail_pass = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_SERVER']         = 'smtp.gmail.com'
app.config['MAIL_PORT']           = 587
app.config['MAIL_USE_TLS']        = True
app.config['MAIL_USERNAME']       = _mail_user
app.config['MAIL_PASSWORD']       = _mail_pass
app.config['MAIL_DEFAULT_SENDER'] = ('QR Menu', _mail_user)
APP_BASE_URL = os.environ.get('APP_BASE_URL', 'http://localhost:5000').rstrip('/')

mail = Mail(app)

# ── QOVLUQLAR ──
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_FILE   = os.path.join(BASE_DIR, 'data.json')
UPLOAD_DIR  = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── DATA ──
DEFAULT_DATA = {
    "cafe": {
        "nameAz": "Üçbucaq Restoran", "nameEn": "Üçbucaq Restaurant",
        "addrAz": "Bakı, Nizami küçəsi 42", "addrEn": "42 Nizami Street, Baku",
        "phone": "+994 50 000 00 00", "icon": "☕",
        "whatsapp": "", "instagram": "", "tiktok": "", "maps": ""
    },
    "categories": [
        {"id":"coffee","labelAz":"Qəhvə","labelEn":"Coffee","bg":"#FFF3E0"},
        {"id":"tea",   "labelAz":"Çay",   "labelEn":"Tea",   "bg":"#E8F5E9"},
        {"id":"food",  "labelAz":"Yemək", "labelEn":"Food",  "bg":"#FFF8E1"},
        {"id":"dessert","labelAz":"Desert","labelEn":"Desserts","bg":"#FCE4EC"}
    ],
    "items": [],
    "theme": {"id":"classic","vars":{"accent":"#E8622A","bg":"#FDF8F3","card":"#FFFFFF","text":"#1A1210","muted":"#8B7355","border":"rgba(180,140,100,0.18)","header":"#E8622A","headerText":"#ffffff"}},
    "users": {
        "admin": {"password": generate_password_hash("admin123"), "role": "superadmin"}
    }
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    save_data(DEFAULT_DATA)
    return DEFAULT_DATA.copy()

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ── ABUNƏLİK SİSTEMİ ──


# ── AUTH ──
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Giriş tələb olunur'}), 401
        return f(*args, **kwargs)
    return decorated

def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Giriş tələb olunur'}), 401
        if session.get('role') != 'superadmin':
            return jsonify({'error': 'Bu əməliyyat üçün superadmin səlahiyyəti lazımdır'}), 403
        return f(*args, **kwargs)
    return decorated

# ── SƏHIFƏLƏR ──
@app.route('/')
def index():
    return redirect(url_for('menu'))

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ── AUTH API ──
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    db = load_data()
    users = db.get('users', {})
    if username in users and check_password_hash(users[username]['password'], password):
        role = users[username].get('role', 'manager')
        session['user'] = username
        session['role'] = role
        return jsonify({'ok': True, 'username': username, 'role': role})
    return jsonify({'ok': False, 'error': 'İstifadəçi adı və ya şifrə yanlışdır'}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me')
def api_me():
    if 'user' in session:
        return jsonify({'ok': True, 'username': session['user'], 'role': session.get('role','manager')})
    return jsonify({'ok': False}), 401

# ── DATA API ──
@app.route('/api/data')
def api_get_data():
    db = load_data()
    # İstifadəçi şifrələrini göndərmə
    safe = {k: v for k, v in db.items() if k != 'users'}
    return jsonify(safe)

@app.route('/api/data', methods=['PUT'])
@login_required
def api_save_data():
    incoming = request.json
    db = load_data()
    # users-i saxla, qalan hər şeyi yenilə
    for key in incoming:
        if key != 'users':
            db[key] = incoming[key]
    save_data(db)
    return jsonify({'ok': True})

# ── ŞƏKIL YÜKLƏMƏ ──
@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'Fayl tapılmadı'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Fayl seçilmədi'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Yalnız PNG, JPG, GIF, WEBP faylları qəbul edilir'}), 400
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = str(uuid.uuid4()) + '.' + ext
    file.save(os.path.join(UPLOAD_DIR, filename))
    url = '/static/uploads/' + filename
    return jsonify({'ok': True, 'url': url})

@app.route('/api/upload/logo', methods=['POST'])
@login_required
def api_upload_logo():
    if 'file' not in request.files:
        return jsonify({'error': 'Fayl tapılmadı'}), 400
    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({'error': 'Yalnız şəkil faylları'}), 400
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = 'logo.' + ext
    file.save(os.path.join(UPLOAD_DIR, filename))
    url = '/static/uploads/' + filename + '?v=' + str(int(datetime.now().timestamp()))
    db = load_data()
    db['cafe']['logo'] = url
    save_data(db)
    return jsonify({'ok': True, 'url': url})

# ── İSTİFADƏÇİ API ──
@app.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    db = load_data()
    current_role = session.get('role', 'manager')
    users = {}
    for k, v in db.get('users', {}).items():
        # Superadmin hesabları yalnız superadmin-ə görünsün
        if v.get('role') == 'superadmin' and current_role != 'superadmin':
            continue
        users[k] = {'role': v.get('role', 'manager')}
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
@login_required
def api_add_user():
    data = request.json
    username = data.get('username','').strip().lower()
    password = data.get('password','')
    role = data.get('role','manager')
    if not username or not password:
        return jsonify({'error': 'Ad və şifrə tələb olunur'}), 400
    if role == 'superadmin':
        return jsonify({'error': 'Superadmin rolu əlavə edilə bilməz'}), 403
    db = load_data()
    if username in db.get('users', {}):
        return jsonify({'error': 'Bu istifadəçi artıq mövcuddur'}), 400
    db.setdefault('users', {})[username] = {
        'password': generate_password_hash(password), 'role': role
    }
    save_data(db)
    return jsonify({'ok': True})

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
def api_delete_user(username):
    if username == session.get('user'):
        return jsonify({'error': 'Özünüzü silə bilməzsiniz'}), 400
    db = load_data()
    db.get('users', {}).pop(username, None)
    save_data(db)
    return jsonify({'ok': True})

@app.route('/api/users/<username>/role', methods=['PUT'])
@login_required
def api_update_user_role(username):
    if session.get('role') != 'superadmin':
        return jsonify({'error': 'Yalnız superadmin rol dəyişə bilər'}), 403
    data = request.json or {}
    role = data.get('role', 'admin')
    db = load_data()
    if username not in db.get('users', {}):
        return jsonify({'error': 'İstifadəçi tapılmadı'}), 404
    db['users'][username]['role'] = role
    save_data(db)
    return jsonify({'ok': True})

@app.route('/api/users/<username>/set-password', methods=['PUT'])
@login_required
def api_set_user_password(username):
    if session.get('role') != 'superadmin' and session.get('user') != username:
        return jsonify({'error': 'İcazə yoxdur'}), 403
    data = request.json or {}
    password = data.get('password', '')
    if not password or len(password) < 6:
        return jsonify({'error': 'Şifrə ən az 6 simvol olmalıdır'}), 400
    db = load_data()
    if username not in db.get('users', {}):
        return jsonify({'error': 'İstifadəçi tapılmadı'}), 404
    db['users'][username]['password'] = generate_password_hash(password)
    save_data(db)
    return jsonify({'ok': True})
@login_required
def api_change_password(username):
    if username != session.get('user'):
        return jsonify({'error': 'İcazə yoxdur'}), 403
    data = request.json
    db = load_data()
    user = db.get('users', {}).get(username)
    if not user or not check_password_hash(user['password'], data.get('current','')):
        return jsonify({'error': 'Cari şifrə yanlışdır'}), 400
    db['users'][username]['password'] = generate_password_hash(data.get('new',''))
    save_data(db)
    return jsonify({'ok': True})

# ── STATİSTİKA ──
@app.route('/api/stats', methods=['POST'])
def api_track_stats():
    data = request.json
    db = load_data()
    stats = db.setdefault('stats', {'clicks': {}, 'opens': {'total': 0, 'dates': {}}, 'cats': {}})
    if data.get('type') == 'click':
        key = data.get('item', '')
        stats['clicks'][key] = stats['clicks'].get(key, 0) + 1
    elif data.get('type') == 'open':
        stats['opens']['total'] = stats['opens'].get('total', 0) + 1
        today = datetime.now().strftime('%Y-%m-%d')
        stats['opens']['dates'][today] = stats['opens']['dates'].get(today, 0) + 1
    elif data.get('type') == 'cat':
        key = data.get('cat', '')
        stats['cats'][key] = stats['cats'].get(key, 0) + 1
    save_data(db)
    return jsonify({'ok': True})

@app.route('/api/stats')
@login_required
def api_get_stats():
    db = load_data()
    return jsonify(db.get('stats', {'clicks': {}, 'opens': {'total': 0, 'dates': {}}, 'cats': {}}))

@app.route('/api/stats', methods=['DELETE'])
@login_required
def api_clear_stats():
    db = load_data()
    db['stats'] = {'clicks': {}, 'opens': {'total': 0, 'dates': {}}, 'cats': {}}
    save_data(db)
    return jsonify({'ok': True})

# ── ŞİFRƏ SIFIRLAMA ──

@app.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email tələb olunur'}), 400

    db = load_data()
    users = db.get('users', {})

    # Admin istifadəçisini götür (ilk admin və ya ilk user)
    matched_user = None
    for username, info in users.items():
        if info.get('role') == 'admin':
            matched_user = username
            break
    if not matched_user and users:
        matched_user = list(users.keys())[0]

    if not matched_user:
        return jsonify({'error': 'İstifadəçi tapılmadı'}), 400

    # Token yarat (1 saatlıq)
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(hours=1)).isoformat()
    reset_tokens = db.setdefault('reset_tokens', {})
    reset_tokens[token] = {'username': matched_user, 'expires': expires, 'used': False}
    save_data(db)

    # Email göndər
    reset_link = f"{APP_BASE_URL}/reset-password?token={token}"
    try:
        msg = Message(
            subject='QR Menu — Şifrə sıfırlama',
            recipients=[email],
            html=f"""
            <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#FDF8F3;border-radius:16px">
              <div style="text-align:center;margin-bottom:24px">
                <div style="font-size:2.5rem">☕</div>
                <h2 style="color:#C9A84C;margin:8px 0">Üçbucaq Restoran</h2>
                <p style="color:#8B7355;font-size:0.9rem">Admin Panel</p>
              </div>
              <div style="background:#fff;border-radius:12px;padding:24px;border:1px solid rgba(180,140,100,0.2)">
                <h3 style="margin-top:0;color:#1A1210">Şifrə sıfırlama sorğusu</h3>
                <p style="color:#555;line-height:1.6">
                  Salam <strong>{matched_user}</strong>, admin paneliniz üçün şifrə sıfırlama sorğusu alındı.
                  Aşağıdakı düyməyə basaraq yeni şifrə təyin edə bilərsiniz.
                </p>
                <p style="text-align:center;margin:28px 0">
                  <a href="{reset_link}"
                     style="background:#C9A84C;color:#fff;text-decoration:none;padding:14px 32px;border-radius:10px;font-weight:600;display:inline-block;font-size:1rem">
                    Şifrəni sıfırla
                  </a>
                </p>
                <p style="color:#999;font-size:0.78rem;text-align:center">
                  Bu link <strong>1 saat</strong> ərzində istifadə edilə bilər.<br>
                  Bu sorğu siz tərəfindən edilməyibsə, bu emaili nəzərə almayın.
                </p>
              </div>
              <p style="color:#ccc;font-size:0.7rem;text-align:center;margin-top:16px">
                Üçbucaq Restoran Admin Panel &copy; {datetime.now().year}
              </p>
            </div>
            """,
            body=f"Şifrə sıfırlama linki: {reset_link}\n\nBu link 1 saat ərzində etibarlıdır."
        )
        mail.send(msg)
    except Exception as e:
        return jsonify({'error': f'Email göndərilmədi: {str(e)}'}), 500

    return jsonify({'ok': True, 'message': 'Şifrə sıfırlama linki emailinizə göndərildi'})


@app.route('/reset-password')
def reset_password_page():
    token = request.args.get('token', '')
    db = load_data()
    token_data = db.get('reset_tokens', {}).get(token)
    if not token_data:
        return "<h2>❌ Keçərsiz link</h2><p>Bu link mövcud deyil və ya artıq istifadə olunub.</p><a href='/admin'>Admin Panelə qayıt</a>"
    if token_data.get('used'):
        return "<h2>❌ Artıq istifadə edilib</h2><p>Bu link artıq istifadə olunub.</p><a href='/admin'>Admin Panelə qayıt</a>"
    if datetime.fromisoformat(token_data['expires']) < datetime.now():
        return "<h2>⏰ Linkın vaxtı bitib</h2><p>Bu link 1 saatlıq etibarlıdır. Yenidən sorğu edin.</p><a href='/admin'>Admin Panelə qayıt</a>"
    # Token etibarlıdır — reset forması göstər (admin.html-ə yönləndir)
    return redirect(f"/admin?reset_token={token}")


@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    data = request.json or {}
    token = data.get('token', '').strip()
    new_password = data.get('password', '')

    if not token or not new_password:
        return jsonify({'error': 'Token və yeni şifrə tələb olunur'}), 400
    if len(new_password) < 6:
        return jsonify({'error': 'Şifrə ən az 6 simvol olmalıdır'}), 400

    db = load_data()
    token_data = db.get('reset_tokens', {}).get(token)

    if not token_data:
        return jsonify({'error': 'Keçərsiz link'}), 400
    if token_data.get('used'):
        return jsonify({'error': 'Bu link artıq istifadə olunub'}), 400
    if datetime.fromisoformat(token_data['expires']) < datetime.now():
        return jsonify({'error': 'Linkın vaxtı bitib. Yenidən sorğu edin'}), 400

    username = token_data['username']
    if username not in db.get('users', {}):
        return jsonify({'error': 'İstifadəçi tapılmadı'}), 400

    db['users'][username]['password'] = generate_password_hash(new_password)
    db['reset_tokens'][token]['used'] = True
    save_data(db)

    return jsonify({'ok': True, 'message': 'Şifrə uğurla yeniləndi'})


# ── İSTİFADƏÇİ EMAIL YENİLƏ ──
@app.route('/api/users/<username>/email', methods=['PUT'])
@login_required
def api_update_user_email(username):
    if username != session.get('user') and session.get('role') != 'admin':
        return jsonify({'error': 'İcazə yoxdur'}), 403
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    db = load_data()
    if username not in db.get('users', {}):
        return jsonify({'error': 'İstifadəçi tapılmadı'}), 404
    db['users'][username]['email'] = email
    save_data(db)
    return jsonify({'ok': True})


@app.route('/api/users/<username>/info', methods=['GET'])
@login_required
def api_get_user_info(username):
    if username != session.get('user') and session.get('role') != 'admin':
        return jsonify({'error': 'İcazə yoxdur'}), 403
    db = load_data()
    user = db.get('users', {}).get(username)
    if not user:
        return jsonify({'error': 'Tapılmadı'}), 404
    return jsonify({'username': username, 'email': user.get('email', ''), 'role': user.get('role', 'manager')})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
