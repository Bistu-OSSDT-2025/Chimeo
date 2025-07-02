from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import os
from datetime import datetime
from icalendar import Calendar, Event
from io import BytesIO
import threading
import time
from mail_sender import send_email

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.config['DATABASE'] = 'users.db'
app.config['SESSION_COOKIE_SECURE'] = False

def init_db():
    with sqlite3.connect(app.config['DATABASE']) as conn:
        cursor = conn.cursor()
        
        # 检查并创建users表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
        
        # 检查并创建events表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    is_all_day INTEGER DEFAULT 0,
                    repeat_rule TEXT,
                    category TEXT,
                    notes TEXT,
                    is_reminded INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
        conn.commit()

def update_db():
    with sqlite3.connect(app.config['DATABASE']) as conn:
        cursor = conn.cursor()
        # 首先检查events表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        if cursor.fetchone():  # 只有表存在时才执行修改
            cursor.execute("PRAGMA table_info(events)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'is_reminded' not in columns:
                cursor.execute("ALTER TABLE events ADD COLUMN is_reminded INTEGER DEFAULT 0")
                conn.commit()
                print("已添加 is_reminded 字段")

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def get_user_id(username):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        return user['id'] if user else None

# ============= 原有所有路由保持不变 =============
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            if user:
                if user['password'] == password:
                    session['username'] = username
                    session.permanent = True
                    return redirect(url_for('index'))
                flash('密码错误')
            else:
                email = request.form.get('email', '').strip()
                
                if not email:
                    flash('请填写邮箱地址')
                else:
                    try:
                        cursor.execute(
                            'INSERT INTO users VALUES (NULL, ?, ?, ?)',
                            (username, email, password)
                        )
                        conn.commit()
                        session['username'] = username
                        return redirect(url_for('index'))
                    except sqlite3.IntegrityError:
                        flash('用户名已存在')
        
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM events 
                WHERE user_id = ?
                ORDER BY start_time
            ''', (get_user_id(session['username']),))
            events = cursor.fetchall()
        return render_template('index.html', events=events)
    except Exception as e:
        flash('加载日程失败')
        return redirect(url_for('logout'))

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO events VALUES (
                        NULL, ?, ?, ?, ?, ?, ?, ?, ?, 0
                    )
                ''', (
                    get_user_id(session['username']),
                    request.form['title'],
                    request.form['start_time'],
                    request.form.get('end_time', ''),
                    1 if 'is_all_day' in request.form else 0,
                    request.form.get('repeat_rule', ''),
                    request.form.get('category', ''),
                    request.form.get('notes', '')
                ))
                conn.commit()
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'创建失败: {str(e)}')
    return render_template('create_event.html')

@app.route('/text_input', methods=['GET'])
def text_input():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('text_input.html')

@app.route('/edit_event/<int:event_id>', methods=['GET'])
def edit_event(event_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM events 
                WHERE id = ? AND user_id = ?
            ''', (event_id, get_user_id(session['username'])))
            event = cursor.fetchone()
        
        if not event:
            flash('日程不存在或无权编辑')
            return redirect(url_for('index'))
            
        event = dict(event)
        event['start_time'] = event['start_time'].replace(' ', 'T')
        if event['end_time']:
            event['end_time'] = event['end_time'].replace(' ', 'T')
            
        return render_template('text_input.html', event=event)
    except Exception as e:
        flash(f'编辑失败: {str(e)}')
        return redirect(url_for('index'))

@app.route('/update_event/<int:event_id>', methods=['POST'])
def update_event(event_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE events SET
                title = ?, start_time = ?, end_time = ?,
                is_all_day = ?, repeat_rule = ?, category = ?, notes = ?
                WHERE id = ? AND user_id = ?
            ''', (
                request.form['title'],
                request.form['start_time'],
                request.form.get('end_time', ''),
                1 if 'is_all_day' in request.form else 0,
                request.form.get('repeat_rule', ''),
                request.form.get('category', ''),
                request.form.get('notes', ''),
                event_id,
                get_user_id(session['username'])
            ))
            conn.commit()
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'更新失败: {str(e)}')
        return redirect(url_for('edit_event', event_id=event_id))

@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM events 
                WHERE id = ? AND user_id = ?
            ''', (event_id, get_user_id(session['username'])))
            conn.commit()
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'删除失败: {str(e)}')
        return redirect(url_for('index'))

@app.route('/export_ics')
def export_ics():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        cal = Calendar()
        cal.add('prodid', '-//My Calendar//mxm.dk//')
        cal.add('version', '2.0')

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM events 
                WHERE user_id = ?
            ''', (get_user_id(session['username']),))
            events = cursor.fetchall()

        for event in events:
            ical_event = Event()
            ical_event.add('summary', event['title'])
            
            # 处理时间格式
            start_time_str = event['start_time']
            try:
                if 'T' in start_time_str:
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
                else:
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                ical_event.add('dtstart', start_time)
                
                if event['end_time']:
                    end_time_str = event['end_time']
                    if 'T' in end_time_str:
                        end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
                    else:
                        end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
                    ical_event.add('dtend', end_time)
                
                if event['notes']:
                    ical_event.add('description', event['notes'])
                
                cal.add_component(ical_event)
            except ValueError as e:
                print(f"时间格式错误: {str(e)}")
                continue

        ics_file = BytesIO(cal.to_ical())
        return send_file(
            ics_file,
            as_attachment=True,
            download_name='my_schedule.ics',
            mimetype='text/calendar'
        )
    except Exception as e:
        flash(f'导出失败: {str(e)}')
        return redirect(url_for('index'))

@app.route('/import_ics', methods=['GET', 'POST'])
def import_ics():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'ics_file' not in request.files:
            flash('未选择文件')
            return redirect(request.url)
            
        file = request.files['ics_file']
        if file.filename == '':
            flash('未选择文件')
            return redirect(request.url)
            
        if file and file.filename.endswith('.ics'):
            try:
                cal = Calendar.from_ical(file.read())
                user_id = get_user_id(session['username'])
                imported_count = 0
                
                with get_db() as conn:
                    cursor = conn.cursor()
                    for component in cal.walk():
                        if component.name == 'VEVENT':
                            cursor.execute('''
                                INSERT INTO events VALUES (
                                    NULL, ?, ?, ?, ?, ?, ?, ?, ?, 0
                                )
                            ''', (
                                user_id,
                                str(component.get('summary')),
                                component.get('dtstart').dt.strftime('%Y-%m-%d %H:%M:%S'),
                                component.get('dtend').dt.strftime('%Y-%m-%d %H:%M:%S') if component.get('dtend') else None,
                                0, '', 'other',
                                str(component.get('description')) if component.get('description') else None
                            ))
                            imported_count += 1
                    conn.commit()
                flash(f'成功导入 {imported_count} 个日程')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'导入失败: {str(e)}')
        else:
            flash('仅支持.ics文件')
    return render_template('import_ics.html')

# ============= 新增的邮件提醒功能 =============
def check_reminders():
    while True:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT e.id, e.title, u.email 
                    FROM events e
                    JOIN users u ON e.user_id = u.id
                    WHERE e.is_reminded = 0 
                    AND datetime(e.start_time) <= datetime(?)
                ''', (now,))
                events_to_remind = cursor.fetchall()
                
                for event_id, title, email in events_to_remind:
                    try:
                        send_email(
                            "【日程提醒】",
                            f"您有一个即将开始的日程:\n\n标题: {title}\n时间: {now}",
                            email
                        )
                        cursor.execute('UPDATE events SET is_reminded = 1 WHERE id = ?', (event_id,))
                        print(f"✓ 已发送提醒给 {email}")
                    except Exception as e:
                        print(f"✗ 邮件发送失败: {str(e)}")
                
                conn.commit()
        except Exception as e:
            print(f"提醒系统错误: {str(e)}")
        
        time.sleep(60)  # 每分钟检查一次

# 启动应用
if __name__ == '__main__':
    init_db()
    update_db()
    reminder_thread = threading.Thread(target=check_reminders, daemon=True)
    reminder_thread.start()
    app.run(host='0.0.0.0', port=5001, debug=True)