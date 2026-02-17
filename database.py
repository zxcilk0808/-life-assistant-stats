"""
База данных для бота-помощника
+ Система уровней, наград, защита от абуза
"""
import sqlite3
import os
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

DB_PATH = Path(__file__).parent / "assistant.db"

# Загрузка ADMIN_IDS из окружения
def get_admin_ids_from_env() -> list:
    """Получить список ID админов из .env"""
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    if admin_ids_str:
        return [int(x.strip()) for x in admin_ids_str.split(',') if x.strip().isdigit()]
    return []


def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            timezone TEXT DEFAULT 'Europe/Moscow',
            is_admin BOOLEAN DEFAULT FALSE,
            daily_xp INTEGER DEFAULT 0,
            daily_xp_reset DATE DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active DATE DEFAULT CURRENT_DATE
        )
    ''')
    
    # Таблица уровней и наград
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS level_rewards (
            level INTEGER PRIMARY KEY,
            xp_required INTEGER,
            reward_text TEXT,
            reward_xp INTEGER DEFAULT 0
        )
    ''')
    
    # Награды по умолчанию
    cursor.execute('''
        INSERT OR IGNORE INTO level_rewards (level, xp_required, reward_text, reward_xp)
        VALUES 
        (1, 0, 'Новичок', 0),
        (2, 100, 'Любитель', 50),
        (3, 300, 'Пользователь', 100),
        (4, 600, 'Активный', 150),
        (5, 1000, 'Опытный', 200),
        (6, 1500, 'Эксперт', 250),
        (7, 2100, 'Мастер', 300),
        (8, 2800, 'Профи', 400),
        (9, 3600, 'Ветеран', 500),
        (10, 4500, 'Легенда', 1000)
    ''')
    
    # Таблица напоминаний
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            remind_at TIMESTAMP NOT NULL,
            location TEXT,
            is_completed BOOLEAN DEFAULT FALSE,
            notified BOOLEAN DEFAULT FALSE,
            pre_notified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблица заметок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            is_pinned BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблица привычек
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            frequency TEXT DEFAULT 'daily',
            streak INTEGER DEFAULT 0,
            total_completed INTEGER DEFAULT 0,
            last_completed DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблица ежедневных действий (для защиты от абуза)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            action_date DATE DEFAULT CURRENT_DATE,
            xp_earned INTEGER DEFAULT 0,
            count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблица настроек бота
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Таблица логов действий пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            user_level INTEGER DEFAULT 1,
            user_xp INTEGER DEFAULT 0,
            action_type TEXT,
            action_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # Настройки по умолчанию
    default_settings = [
        ('daily_xp_limit', '500'),
        ('reminder_xp', '10'),
        ('habit_xp', '20'),
        ('note_xp', '5'),
        ('start_xp', '50'),
        ('admin_ids', '')
    ]

    for key, value in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)
        ''', (key, value))
    
    conn.commit()
    conn.close()


# ========== Настройки ==========

def get_setting(key: str, default: str = None) -> str:
    """Получить настройку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM bot_settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key: str, value: str):
    """Установить настройку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)
    ''', (key, value))
    conn.commit()
    conn.close()


# ========== Пользователи ==========

def add_user(user_id: int, username: str = None):
    """Добавить пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username)
        VALUES (?, ?)
    ''', (user_id, username))
    conn.commit()
    conn.close()


def get_user(user_id: int) -> dict:
    """Получить пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'xp': row[2],
            'level': row[3],
            'timezone': row[4],
            'is_admin': row[5],
            'daily_xp': row[6],
            'daily_xp_reset': row[7]
        }
    return None


def is_admin(user_id: int) -> bool:
    """Проверка на админа"""
    user = get_user(user_id)
    
    # Проверка по списку admin_ids из .env
    env_admin_ids = get_admin_ids_from_env()
    if user_id in env_admin_ids:
        return True
    
    # Проверка по флагу is_admin в БД
    if user and user['is_admin']:
        return True

    # Проверка по списку admin_ids в БД
    admin_ids = get_setting('admin_ids', '')
    if admin_ids:
        return str(user_id) in admin_ids.split(',')

    return False


def set_admin(user_id: int, is_admin_flag: bool):
    """Назначить/снять админа"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET is_admin = ? WHERE user_id = ?
    ''', (is_admin_flag, user_id))
    conn.commit()
    conn.close()


def reset_daily_xp(user_id: int):
    """Сброс дневного XP"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET daily_xp = 0, daily_xp_reset = DATE('now')
        WHERE user_id = ? AND daily_xp_reset < DATE('now')
    ''', (user_id,))
    conn.commit()
    conn.close()


def check_daily_limit(user_id: int, xp_amount: int) -> tuple:
    """Проверка лимита XP на день"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Сброс если новый день
    cursor.execute('''
        UPDATE users SET daily_xp = 0, daily_xp_reset = DATE('now')
        WHERE user_id = ? AND daily_xp_reset < DATE('now')
    ''', (user_id,))
    
    # Получаем текущий дневной XP
    cursor.execute('SELECT daily_xp FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    daily_limit = int(get_setting('daily_xp_limit', '500'))
    
    if row:
        current_daily = row[0]
        if current_daily + xp_amount > daily_limit:
            conn.close()
            return False, daily_limit - current_daily  # Превышен лимит
    
    conn.close()
    return True, 0  # ОК


# ========== Система XP и уровней ==========

def add_xp(user_id: int, xp_amount: int, action_type: str = "general") -> dict:
    """
    Добавить XP пользователю с проверкой лимитов
    Возвращает: {'success': bool, 'xp_added': int, 'level': int, 'level_up': bool, 'reward': str}
    """
    result = {
        'success': False,
        'xp_added': 0,
        'level': 1,
        'level_up': False,
        'reward': None,
        'message': ''
    }
    
    # Проверка дневного лимита
    allowed, remaining = check_daily_limit(user_id, xp_amount)
    
    if not allowed:
        result['message'] = f"⚠️ Дневной лимит XP исчерпан! Осталось: {remaining} XP"
        return result
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем текущего пользователя
    cursor.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row:
        current_xp, current_level = row
        
        # Ограничиваем XP дневным лимитом
        actual_xp = min(xp_amount, remaining) if remaining > 0 else 0
        
        if actual_xp > 0:
            new_xp = current_xp + actual_xp
            
            # Формула уровня: level = sqrt(xp / 100) + 1
            new_level = int((new_xp / 100) ** 0.5) + 1
            
            # Обновляем пользователя
            cursor.execute('''
                UPDATE users SET xp = ?, level = ?, daily_xp = daily_xp + ?, last_active = DATE('now')
                WHERE user_id = ?
            ''', (new_xp, new_level, actual_xp, user_id))
            
            # Записываем действие
            cursor.execute('''
                INSERT INTO daily_actions (user_id, action_type, xp_earned)
                VALUES (?, ?, ?)
            ''', (user_id, action_type, actual_xp))
            
            result['success'] = True
            result['xp_added'] = actual_xp
            result['level'] = new_level
            
            # Проверка на повышение уровня
            if new_level > current_level:
                result['level_up'] = True
                
                # Получаем награду за уровень
                cursor.execute('''
                    SELECT reward_text, reward_xp FROM level_rewards WHERE level = ?
                ''', (new_level,))
                reward_row = cursor.fetchone()
                
                if reward_row:
                    result['reward'] = reward_row[0]
                    
                    # Если есть бонусный XP за награду
                    if reward_row[1] > 0:
                        bonus_xp = reward_row[1]
                        new_xp += bonus_xp
                        cursor.execute('UPDATE users SET xp = ? WHERE user_id = ?', (new_xp, user_id))
                        result['message'] = f"🎉 +{bonus_xp} XP бонус!"
            
            conn.commit()
    
    conn.close()
    return result


def get_xp_for_level(level: int) -> int:
    """Сколько XP нужно для уровня"""
    return ((level) ** 2) * 100


def get_level_progress(user_id: int) -> dict:
    """Прогресс до следующего уровня"""
    user = get_user(user_id)
    if not user:
        return {'level': 1, 'xp': 0, 'next_level_xp': 100, 'progress_percent': 0, 'daily_xp': 0, 'daily_limit': 500}
    
    current_level = user['level']
    current_xp = user['xp']
    
    # XP для текущего уровня
    current_level_xp = get_xp_for_level(current_level - 1)
    # XP для следующего уровня
    next_level_xp = get_xp_for_level(current_level)
    
    # Прогресс в текущем уровне
    xp_in_level = current_xp - current_level_xp
    xp_needed = next_level_xp - current_level_xp
    progress_percent = (xp_in_level / xp_needed * 100) if xp_needed > 0 else 0
    
    # Дневной лимит
    daily_limit = int(get_setting('daily_xp_limit', '500'))
    
    return {
        'level': current_level,
        'xp': current_xp,
        'next_level_xp': next_level_xp,
        'xp_in_level': xp_in_level,
        'xp_needed': xp_needed,
        'progress': xp_in_level,
        'progress_percent': min(100, progress_percent),
        'daily_xp': user['daily_xp'],
        'daily_limit': daily_limit
    }


def get_level_rewards() -> list:
    """Получить все награды за уровни"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT level, xp_required, reward_text, reward_xp FROM level_rewards ORDER BY level')
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {'level': row[0], 'xp_required': row[1], 'reward_text': row[2], 'reward_xp': row[3]}
        for row in rows
    ]


def update_timezone(user_id: int, timezone: str):
    """Обновить часовой пояс"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET timezone = ? WHERE user_id = ?
    ''', (timezone, user_id))
    conn.commit()
    conn.close()


# ========== Напоминания ==========

def add_reminder(user_id: int, title: str, remind_at: datetime, 
                 description: str = None, location: str = None):
    """Добавить напоминание"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reminders (user_id, title, description, remind_at, location)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, title, description, remind_at, location))
    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id


def get_pending_reminders():
    """Получить напоминания, которые нужно отправить"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM reminders
        WHERE is_completed = FALSE
        AND notified = FALSE
        AND remind_at <= datetime('now')
        ORDER BY remind_at
    ''')

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'id': row[0],
            'user_id': row[1],
            'title': row[2],
            'description': row[3],
            'remind_at': row[4],
            'location': row[5],
            'is_completed': row[6],
            'notified': row[7],
            'pre_notified': row[8] if len(row) > 8 else False
        }
        for row in rows
    ]


def get_pre_notify_reminders():
    """Получить напоминания для предварительного уведомления (за 1 час)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Находим напоминания, которые сработают через 1 час
    cursor.execute('''
        SELECT * FROM reminders
        WHERE is_completed = FALSE
        AND pre_notified = FALSE
        AND remind_at > datetime('now')
        AND remind_at <= datetime('now', '+1 hour')
        ORDER BY remind_at
    ''')

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'id': row[0],
            'user_id': row[1],
            'title': row[2],
            'description': row[3],
            'remind_at': row[4],
            'location': row[5],
            'is_completed': row[6],
            'notified': row[7],
            'pre_notified': row[8] if len(row) > 8 else False
        }
        for row in rows
    ]


def mark_pre_notified(reminder_id: int):
    """Отметить что предварительное уведомление отправлено"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reminders SET pre_notified = TRUE WHERE id = ?
    ''', (reminder_id,))
    conn.commit()
    conn.close()


def get_all_reminders(user_id: int):
    """Получить все напоминания пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM reminders 
        WHERE user_id = ?
        ORDER BY remind_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': row[0],
            'title': row[2],
            'description': row[3],
            'remind_at': row[4],
            'location': row[5],
            'is_completed': row[6]
        }
        for row in rows
    ]


def get_reminder_by_id(reminder_id: int):
    """Получить напоминание по ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reminders WHERE id = ?', (reminder_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'user_id': row[1],
            'title': row[2],
            'description': row[3],
            'remind_at': row[4],
            'location': row[5],
            'is_completed': row[6]
        }
    return None


def complete_reminder(reminder_id: int):
    """Отметить напоминание выполненным"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reminders SET is_completed = TRUE WHERE id = ?
    ''', (reminder_id,))
    conn.commit()
    conn.close()


def delete_reminder(reminder_id: int):
    """Удалить напоминание"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
    conn.commit()
    conn.close()


def mark_notified(reminder_id: int):
    """Отметить что уведомление отправлено"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reminders SET notified = TRUE WHERE id = ?
    ''', (reminder_id,))
    conn.commit()
    conn.close()


# ========== Заметки ==========

def add_note(user_id: int, content: str, title: str = None, category: str = 'general'):
    """Добавить заметку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notes (user_id, title, content, category)
        VALUES (?, ?, ?, ?)
    ''', (user_id, title, content, category))
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_all_notes(user_id: int):
    """Получить все заметки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM notes 
        WHERE user_id = ?
        ORDER BY is_pinned DESC, created_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': row[0],
            'title': row[2],
            'content': row[3],
            'category': row[4],
            'is_pinned': row[5],
            'created_at': row[6]
        }
        for row in rows
    ]


def get_note_by_id(note_id: int):
    """Получить заметку по ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM notes WHERE id = ?', (note_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'title': row[2],
            'content': row[3],
            'category': row[4],
            'is_pinned': row[5]
        }
    return None


def delete_note(note_id: int):
    """Удалить заметку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()


def toggle_pin_note(note_id: int):
    """Закрепить/открепить заметку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE notes SET is_pinned = NOT is_pinned WHERE id = ?
    ''', (note_id,))
    conn.commit()
    conn.close()


# ========== Привычки ==========

def add_habit(user_id: int, title: str, frequency: str = 'daily'):
    """Добавить привычку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO habits (user_id, title, frequency)
        VALUES (?, ?, ?)
    ''', (user_id, title, frequency))
    habit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return habit_id


def get_all_habits(user_id: int):
    """Получить все привычки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM habits WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': row[0],
            'title': row[2],
            'frequency': row[3],
            'streak': row[4],
            'total_completed': row[5],
            'last_completed': row[6]
        }
        for row in rows
    ]


def get_habit_by_id(habit_id: int):
    """Получить привычку по ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM habits WHERE id = ?', (habit_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'title': row[2],
            'frequency': row[3],
            'streak': row[4],
            'total_completed': row[5],
            'last_completed': row[6]
        }
    return None


def complete_habit(habit_id: int) -> dict:
    """Отметить привычку выполненной"""
    from datetime import date
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT streak, last_completed, total_completed FROM habits WHERE id = ?', (habit_id,))
    row = cursor.fetchone()
    
    result = {'success': False, 'new_streak': 0, 'already_done': False}
    
    if row:
        streak, last_completed, total_completed = row
        today = str(date.today())
        
        if last_completed == today:
            result['already_done'] = True
        else:
            new_streak = streak + 1 if last_completed else 1
            new_total = total_completed + 1
            
            cursor.execute('''
                UPDATE habits SET streak = ?, total_completed = ?, last_completed = ?
                WHERE id = ?
            ''', (new_streak, new_total, today, habit_id))
            
            result['success'] = True
            result['new_streak'] = new_streak
            result['new_total'] = new_total
    
    conn.commit()
    conn.close()
    return result


def delete_habit(habit_id: int):
    """Удалить привычку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
    conn.commit()
    conn.close()


# ========== Статистика ==========

def get_user_stats(user_id: int) -> dict:
    """Получить полную статистику пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Напоминания
    cursor.execute('SELECT COUNT(*), SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) FROM reminders WHERE user_id = ?', (user_id,))
    rem_row = cursor.fetchone()
    
    # Заметки
    cursor.execute('SELECT COUNT(*), SUM(CASE WHEN is_pinned THEN 1 ELSE 0 END) FROM notes WHERE user_id = ?', (user_id,))
    note_row = cursor.fetchone()
    
    # Привычки
    cursor.execute('SELECT COUNT(*), SUM(streak), SUM(total_completed) FROM habits WHERE user_id = ?', (user_id,))
    habit_row = cursor.fetchone()
    
    # XP за сегодня
    cursor.execute('''
        SELECT SUM(xp_earned) FROM daily_actions 
        WHERE user_id = ? AND action_date = DATE('now')
    ''', (user_id,))
    today_xp_row = cursor.fetchone()
    
    conn.close()
    
    return {
        'total_reminders': rem_row[0] or 0,
        'completed_reminders': rem_row[1] or 0,
        'total_notes': note_row[0] or 0,
        'pinned_notes': note_row[1] or 0,
        'total_habits': habit_row[0] or 0,
        'total_streak': habit_row[1] or 0,
        'total_habit_completions': habit_row[2] or 0,
        'today_xp': today_xp_row[0] or 0
    }


def get_global_stats() -> dict:
    """Получить глобальную статистику бота"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Пользователи
    cursor.execute('SELECT COUNT(*) FROM users')
    users_count = cursor.fetchone()[0]
    
    # Активные сегодня
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_active = DATE('now')")
    active_today = cursor.fetchone()[0]
    
    # Всего напоминаний
    cursor.execute('SELECT COUNT(*) FROM reminders')
    total_reminders = cursor.fetchone()[0]
    
    # Всего заметок
    cursor.execute('SELECT COUNT(*) FROM notes')
    total_notes = cursor.fetchone()[0]
    
    # Всего привычек
    cursor.execute('SELECT COUNT(*) FROM habits')
    total_habits = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'users_count': users_count,
        'active_today': active_today,
        'total_reminders': total_reminders,
        'total_notes': total_notes,
        'total_habits': total_habits
    }


# ========== Логи ==========

def add_log(user_id: int, username: str, level: int, xp: int, action_type: str, action_data: str = None):
    """Добавить запись в лог"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (user_id, username, user_level, user_xp, action_type, action_data)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, level, xp, action_type, action_data))
    conn.commit()
    conn.close()


def get_all_logs(limit: int = 50, offset: int = 0) -> list:
    """Получить все логи с информацией о пользователе"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, username, user_level, user_xp, action_type, action_data, created_at
        FROM logs
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'id': row[0],
            'user_id': row[1],
            'username': row[2],
            'level': row[3],
            'xp': row[4],
            'action_type': row[5],
            'action_data': row[6],
            'created_at': row[7]
        }
        for row in rows
    ]


def get_user_logs(user_id: int, limit: int = 50) -> list:
    """Получить логи конкретного пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, username, user_level, user_xp, action_type, action_data, created_at
        FROM logs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'id': row[0],
            'user_id': row[1],
            'username': row[2],
            'level': row[3],
            'xp': row[4],
            'action_type': row[5],
            'action_data': row[6],
            'created_at': row[7]
        }
        for row in rows
    ]


def get_logs_count() -> int:
    """Получить общее количество записей в логах"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM logs')
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_all_users_with_stats() -> list:
    """Получить всех пользователей со статистикой"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            u.user_id,
            u.username,
            u.xp,
            u.level,
            u.created_at,
            u.last_active,
            COUNT(DISTINCT r.id) as reminders_count,
            SUM(CASE WHEN r.is_completed THEN 1 ELSE 0 END) as completed_reminders,
            COUNT(DISTINCT n.id) as notes_count,
            COUNT(DISTINCT h.id) as habits_count,
            SUM(h.streak) as total_streak
        FROM users u
        LEFT JOIN reminders r ON u.user_id = r.user_id
        LEFT JOIN notes n ON u.user_id = n.user_id
        LEFT JOIN habits h ON u.user_id = h.user_id
        GROUP BY u.user_id
        ORDER BY u.xp DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'user_id': row[0],
            'username': row[1],
            'xp': row[2],
            'level': row[3],
            'created_at': row[4],
            'last_active': row[5],
            'reminders_count': row[6] or 0,
            'completed_reminders': row[7] or 0,
            'notes_count': row[8] or 0,
            'habits_count': row[9] or 0,
            'total_streak': row[10] or 0
        }
        for row in rows
    ]


if __name__ == "__main__":
    init_db()
    print("Database initialized!")
