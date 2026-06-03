"""
SQLite数据库操作封装
修复版 - 使用本地时间
"""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from utils.config import DB_PATH

# 线程本地存储，确保每个线程有自己的数据库连接
_local = threading.local()

def get_connection():
    """获取当前线程的数据库连接"""
    if not hasattr(_local, 'conn'):
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.row_factory = sqlite3.Row
        _init_db(_local.conn)
    return _local.conn

def _init_db(conn):
    """初始化数据库表 - 使用本地时间"""
    cursor = conn.cursor()

    # 学生表 - create_time 不再使用 DEFAULT，由代码写入
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(50) NOT NULL,
            face_count INTEGER DEFAULT 0,
            create_time TIMESTAMP
        )
    ''')

    # 考勤记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(20) NOT NULL,
            name VARCHAR(50) NOT NULL,
            check_time TIMESTAMP,
            status INTEGER DEFAULT 1,
            confidence FLOAT
        )
    ''')

    # 系统配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key VARCHAR(50) PRIMARY KEY,
            value VARCHAR(200)
        )
    ''')
    conn.commit()

@contextmanager
def get_cursor():
    """获取数据库游标的上下文管理器"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise

# ------------------- 学生操作 -------------------
def add_student(student_id, name):
    """
    添加学生记录 - 使用本地系统时间
    """
    with get_cursor() as c:
        # 获取当前本地系统时间
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 先检查是否存在
        c.execute('SELECT * FROM students WHERE student_id=?', (student_id,))
        existing = c.fetchone()

        if existing:
            # 更新姓名，保留原有创建时间
            c.execute('UPDATE students SET name=? WHERE student_id=?', (name, student_id))
        else:
            # 插入新记录，使用本地时间
            c.execute('''
                INSERT INTO students (student_id, name, create_time, face_count)
                VALUES (?,?,?,0)
            ''', (student_id, name, local_time))

        return c.lastrowid

def get_student_by_id(student_id):
    """根据学号查询学生"""
    with get_cursor() as c:
        c.execute('SELECT * FROM students WHERE student_id=?', (student_id,))
        row = c.fetchone()
        return dict(row) if row else None

def get_all_students():
    """获取所有学生列表"""
    with get_cursor() as c:
        c.execute('SELECT student_id, name, create_time, face_count FROM students ORDER BY student_id')
        rows = c.fetchall()
        return [{'student_id': row['student_id'], 'name': row['name'],
                 'create_time': row['create_time'], 'face_count': row['face_count']} for row in rows]

def update_face_count(student_id, count):
    """更新学生的注册照片数"""
    with get_cursor() as c:
        c.execute('UPDATE students SET face_count=? WHERE student_id=?', (count, student_id))

def delete_student(student_id):
    """删除学生及其考勤记录"""
    with get_cursor() as c:
        try:
            c.execute('DELETE FROM attendance WHERE student_id=?', (student_id,))
            c.execute('DELETE FROM students WHERE student_id=?', (student_id,))
            return True
        except Exception as e:
            print(f"[数据库] 删除学生失败: {e}")
            return False

# ------------------- 考勤操作 -------------------
def add_attendance_record(student_id, name, confidence):
    """
    添加考勤记录 - 使用本地系统时间
    """
    with get_cursor() as c:
        # 获取当前本地系统时间
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''
            INSERT INTO attendance (student_id, name, confidence, check_time)
            VALUES (?,?,?,?)
        ''', (student_id, name, confidence, local_time))
        return c.lastrowid

def get_last_attendance_time(student_id):
    """获取某学生最近一次考勤时间"""
    with get_cursor() as c:
        c.execute('''
            SELECT check_time FROM attendance 
            WHERE student_id=? ORDER BY check_time DESC LIMIT 1
        ''', (student_id,))
        row = c.fetchone()
        if row and row['check_time']:
            from datetime import datetime
            return datetime.strptime(row['check_time'], '%Y-%m-%d %H:%M:%S')
        return None

def query_attendance(start_date, end_date, student_id=None):
    """
    按日期范围查询考勤记录
    :param start_date: 开始日期字符串 'YYYY-MM-DD'
    :param end_date: 结束日期字符串 'YYYY-MM-DD'
    :param student_id: 可选，学号过滤
    :return: 记录列表（字典格式）
    """
    with get_cursor() as c:
        sql = '''
            SELECT a.*, s.name as student_name 
            FROM attendance a
            LEFT JOIN students s ON a.student_id = s.student_id
            WHERE date(a.check_time) BETWEEN date(?) AND date(?)
        '''
        params = [start_date, end_date]
        if student_id:
            sql += ' AND a.student_id=?'
            params.append(student_id)
        sql += ' ORDER BY a.check_time DESC'
        c.execute(sql, params)
        rows = c.fetchall()
        return [dict(row) for row in rows]

# ------------------- 配置操作 -------------------
def get_config(key, default=None):
    """获取配置项"""
    with get_cursor() as c:
        c.execute('SELECT value FROM config WHERE key=?', (key,))
        row = c.fetchone()
        return row['value'] if row else default

def set_config(key, value):
    """设置配置项"""
    with get_cursor() as c:
        c.execute('REPLACE INTO config (key, value) VALUES (?,?)', (key, value))

# 初始化默认配置
from utils.config import LBPH_THRESHOLD
if get_config('lbph_threshold') is None:
    set_config('lbph_threshold', str(LBPH_THRESHOLD))