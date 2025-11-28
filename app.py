from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'super_secret_key_coinquest_2025'

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, coins=0):
        self.id = id
        self.username = username
        self.coins = coins

@app.before_request
def restrict_to_telegram():
    if request.path.startswith('/telegram'):
        if not request.headers.get('User-Agent', '').lower().startswith('telegram'):
            return "فقط از داخل تلگرام باز کن!", 403

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['coins'])
    return None

# دیتابیس
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  coins INTEGER DEFAULT 0,
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS quests
                 (id INTEGER PRIMARY KEY,
                  name TEXT,
                  description TEXT,
                  reward INTEGER,
                  completed_by_user TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS game_scores
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  game_name TEXT,
                  score INTEGER,
                  timestamp TEXT)''')
    
    # کوئست‌های نمونه
    sample_quests = [
        (1, 'کلیک سریع', '۵۰ بار در ۱۰ ثانیه کلیک کن', 100, ''),
        (2, 'حدس عدد', 'عدد مخفی رو درست حدس بزن', 80, ''),
        (3, 'خاطره‌بازی', '۵ کارت رو به خاطر بسپار', 150, ''),
        (4, 'ورود روزانه', 'هر روز وارد شو', 30, ''),
        (5, '۱۰۰۰ کوین جمع کن', 'به ۱۰۰۰ کوین برس', 500, ''),
        (6, 'بازی ۱۰ بار', 'هر بازی رو حداقل ۱۰ بار بازی کن', 300, ''),
        (7, 'دوست دعوت کن', 'یک دوست رو دعوت کن', 400, ''),
        (8, 'فروشگاه', 'اولین خرید رو انجام بده', 200, '')
    ]
    c.executemany('INSERT OR IGNORE INTO quests VALUES (?, ?, ?, ?, ?)', sample_quests)
    conn.commit()
    conn.close()

# روت‌ها
@app.route('/telegram')
def telegram():
    return render_template('telegram.html')

@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['coins'])
            login_user(user_obj)
            return redirect(url_for('index'))
        flash('نام کاربری یا رمز اشتباهه!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                         (username, password, datetime.now().isoformat()))
            conn.commit()
            flash('ثبت‌نام موفق! حالا لاگین کن')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('این نام کاربری قبلاً گرفته شده!')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/games')
@login_required
def games():
    return render_template('games.html')

@app.route('/quests')
@login_required
def quests():
    conn = get_db_connection()
    all_quests = conn.execute('SELECT * FROM quests').fetchall()
    conn.close()
    return render_template('quests.html', quests=all_quests)

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()
    recent_scores = conn.execute('SELECT * FROM game_scores WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10', (current_user.id,)).fetchall()
    conn.close()
    return render_template('dashboard.html', stats=user_data, scores=recent_scores)

@app.route('/shop')
@login_required
def shop():
    rewards = [
        {"id": 1, "name": "گیفت کارت ۱۰ هزار تومانی", "price": 600},
        {"id": 2, "name": "شارژ ایرانسل ۵ هزار", "price": 350},
        {"id": 3, "name": "نقش VIP (یک ماه)", "price": 1200},
        {"id": 4, "name": "بوست کوین ×۲ (۲۴ ساعت)", "price": 800},
        {"id": 5, "name": "آواتار اختصاصی", "price": 400}
    ]
    return render_template('shop.html', rewards=rewards)

# API ها
@app.route('/api/game_score', methods=['POST'])
@login_required
def save_game_score():
    data = request.json
    conn = get_db_connection()
    conn.execute('INSERT INTO game_scores (user_id, game_name, score, timestamp) VALUES (?, ?, ?, ?)',
                 (current_user.id, data['game_name'], data['score'], datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/complete_quest', methods=['POST'])
@login_required
def complete_quest():
    quest_id = request.json['quest_id']
    conn = get_db_connection()
    quest = conn.execute('SELECT * FROM quests WHERE id = ?', (quest_id,)).fetchone()
    
    if quest and str(current_user.id) not in (quest['completed_by_user'] or ''):
        reward = quest['reward']
        conn.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (reward, current_user.id))
        new_completed = (quest['completed_by_user'] or '') + f' {current_user.id}'
        conn.execute('UPDATE quests SET completed_by_user = ? WHERE id = ?', (new_completed.strip(), quest_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "reward": reward, "new_coins": current_user.coins + reward})
    
    conn.close()
    return jsonify({"status": "already_completed"})

@app.route('/api/buy_reward', methods=['POST'])
@login_required
def buy_reward():
    price = request.json['price']
    conn = get_db_connection()
    user = conn.execute('SELECT coins FROM users WHERE id = ?', (current_user.id,)).fetchone()
    if user and user['coins'] >= price:
        conn.execute('UPDATE users SET coins = coins - ? WHERE id = ?', (price, current_user.id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    conn.close()
    return jsonify({"status": "error", "message": "کوین کافی نیست!"})

# این همون API که خواستی — برای آپدیت لحظه‌ای کوین
@app.route('/api/user_coins')
@login_required
def user_coins():
    conn = get_db_connection()
    coins = conn.execute('SELECT coins FROM users WHERE id = ?', (current_user.id,)).fetchone()['coins']
    conn.close()
    return jsonify({'coins': coins})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)