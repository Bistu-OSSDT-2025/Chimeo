from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import sqlite3
import os
from datetime import datetime
from icalendar import Calendar, Event
from io import BytesIO
import threading
import time
from mail_sender import send_email
import openai
from dotenv import load_dotenv
from typing import List, Optional

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.config['DATABASE'] = 'users.db'
app.config['SESSION_COOKIE_SECURE'] = False

# 加载环境变量
load_dotenv()

class TaskSplitter:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.model_id = os.getenv("OPENAI_MODEL_ID", "deepseek32b")
    
    def split_task(self, task_description: str, language: str = "zh-CN") -> Optional[List[str]]:
        try:
            prompt = self._build_prompt(task_description, language)
            
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "你是一个高效的任务规划助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            steps = self._parse_response(response.choices[0].message.content)
            return steps
            
        except Exception as e:
            print(f"Error splitting task: {e}")
            return None
    
    def _build_prompt(self, task_description: str, language: str) -> str:
        if language.startswith("zh"):
            return (
                f"请将以下任务拆分为具体的执行步骤，步骤数量在3-8个之间，每个步骤应简洁明了。"
                f"直接输出步骤内容，不要添加任何解释或额外信息。"
                f"任务描述：{task_description}\n\n"
                f"步骤："
            )
        else:
            return (
                f"Please break down the following task into specific steps, with 3-8 steps in total. "
                f"Each step should be concise and clear. "
                f"Output only the step contents, without any explanations or additional information. "
                f"Task description: {task_description}\n\n"
                f"Steps:"
            )
    
    def _parse_response(self, response_text: str) -> List[str]:
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        steps = []
        for line in lines:
            if line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", 
                               "1、", "2、", "3、", "4、", "5、", "6、", "7、", "8、",
                               "- ", "* ")):
                line = line[2:].strip()
            steps.append(line)
        return steps

# 初始化任务拆分器
splitter = TaskSplitter()

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
            
            # 处理时间
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
                
                # 添加备注（可选）
                if event['notes']:
                    ical_event.add('description', event['notes'])
                
                # ✅ 关键修复：添加分类标签
                if event['category']:
                    ical_event.add('categories', event['category'])  # 写入 CATEGORIES 字段
                
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
                file.seek(0)
                ics_content = file.read()
                
                if not ics_content:
                    flash('文件内容为空')
                    return redirect(request.url)
                
                try:
                    ics_content = ics_content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        ics_content = ics_content.decode('gbk')
                    except:
                        flash('文件编码不支持')
                        return redirect(request.url)
                
                cal = Calendar.from_ical(ics_content)
                if not cal:
                    flash('无效的日历文件')
                    return redirect(request.url)
                
                user_id = get_user_id(session['username'])
                imported_count = 0
                
                with get_db() as conn:
                    cursor = conn.cursor()
                    for component in cal.walk():
                        if component.name == 'VEVENT':
                            # 获取分类
                            ical_categories = component.get('categories')
                            category = 'other'  # 默认值
                            
                            if ical_categories:
                                try:
                                    # 处理分类数据 - 关键修复点
                                    if hasattr(ical_categories, 'cats'):  # 处理vCategory对象
                                        categories = ical_categories.cats
                                    elif isinstance(ical_categories, list):
                                        categories = [str(cat) for cat in ical_categories]
                                    else:
                                        categories = str(ical_categories).split(',')
                                    
                                    # 获取第一个分类并清理
                                    if categories:
                                        first_category = categories[0].strip().lower()
                                        # 直接使用小写分类名，确保与前端样式匹配
                                        category = first_category if first_category in ['work', 'study', 'life', 'other'] else 'other'
                                except Exception as e:
                                    print(f"分类处理错误: {e}")
                                    category = 'other'
                            
                            # 处理时间和其他字段...
                            dtstart = component.get('dtstart').dt
                            start_time = dtstart.strftime('%Y-%m-%d %H:%M:%S')
                            
                            dtend = component.get('dtend')
                            end_time = dtend.dt.strftime('%Y-%m-%d %H:%M:%S') if dtend else None
                            
                            cursor.execute('''
                                INSERT INTO events VALUES (
                                    NULL, ?, ?, ?, ?, ?, ?, ?, ?, 0
                                )
                            ''', (
                                user_id,
                                str(component.get('summary')),
                                start_time,
                                end_time,
                                0,  # is_all_day
                                '',  # repeat_rule
                                category,
                                str(component.get('description')) if component.get('description') else None
                            ))
                            imported_count += 1
                    conn.commit()
                flash(f'成功导入 {imported_count} 个日程')
                return redirect(url_for('index'))
            except Exception as e:
                print(f"导入错误详情: {str(e)}")
                flash(f"导入失败: {str(e)}")
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


# 在app.py中添加以下路由
@app.route('/save_subtasks', methods=['POST'])
def save_subtasks():
    if 'username' not in session:
        return jsonify({"error": "请先登录"}), 401
    
    data = request.json
    main_task = data.get('main_task')
    steps = data.get('steps')
    
    if not main_task or not steps:
        return jsonify({"error": "缺少必要参数"}), 400
    
    try:
        user_id = get_user_id(session['username'])
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 为每个子步骤创建日程
            for i, step in enumerate(steps):
                cursor.execute('''
                    INSERT INTO events VALUES (
                        NULL, ?, ?, ?, ?, ?, ?, ?, ?, 0
                    )
                ''', (
                    user_id,
                    f"{main_task} - 步骤{i+1}: {step}",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # 默认开始时间为现在
                    '',  # 无结束时间
                    0,   # 非全天
                    '',  # 无重复规则
                    'work',  # 默认分类为工作
                    f"主任务: {main_task}\n步骤内容: {step}",  # 备注
                ))
            
            conn.commit()
        return jsonify({"success": True, "redirect": url_for('index')})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/split-task', methods=['POST'])
def api_split_task():
    if 'username' not in session:
        return jsonify({"error": "请先登录"}), 401
    
    data = request.json
    task = data.get('task')
    language = data.get('language', 'zh-CN')
    
    if not task:
        return jsonify({"error": "任务描述不能为空"}), 400
    
    steps = splitter.split_task(task, language)
    
    if steps:
        return jsonify({"success": True, "steps": steps})
    else:
        return jsonify({"success": False, "error": "任务拆分失败"}), 500

# 新增任务拆分页面路由
@app.route('/task_splitter')
def task_splitter():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('task_splitter.html')

if __name__ == '__main__':
    init_db()
    update_db()
    reminder_thread = threading.Thread(target=check_reminders, daemon=True)
    reminder_thread.start()
    app.run(host='0.0.0.0', port=5001, debug=True)