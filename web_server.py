"""
Web server для Mini App статистики
Отдаёт данные из базы данных по API
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, date
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для Mini App

DB_PATH = Path(__file__).parent / "assistant.db"


def get_db_connection():
    """Подключение к БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_stats(user_id: int) -> dict:
    """Получить статистику пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Пользователь
    cursor.execute('SELECT xp, level, daily_xp FROM users WHERE user_id = ?', (user_id,))
    user_row = cursor.fetchone()
    
    if not user_row:
        conn.close()
        return None
    
    # Напоминания
    cursor.execute('''
        SELECT COUNT(*) as total, SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) as completed
        FROM reminders WHERE user_id = ?
    ''', (user_id,))
    rem_row = cursor.fetchone()
    
    # Заметки
    cursor.execute('SELECT COUNT(*) FROM notes WHERE user_id = ?', (user_id,))
    notes_count = cursor.fetchone()[0]
    
    # Привычки
    cursor.execute('''
        SELECT COUNT(*) as habits, SUM(streak) as total_streak
        FROM habits WHERE user_id = ?
    ''', (user_id,))
    habit_row = cursor.fetchone()
    
    conn.close()
    
    # Расчёт прогресса уровня
    current_level = user_row['level']
    current_xp = user_row['xp']
    next_level_xp = ((current_level + 1) ** 2) * 100
    prev_level_xp = (current_level ** 2) * 100
    progress_percent = ((current_xp - prev_level_xp) / (next_level_xp - prev_level_xp)) * 100 if next_level_xp > prev_level_xp else 0
    
    # Награды
    rewards = ['Новичок', 'Любитель', 'Пользователь', 'Активный', 'Опытный', 'Эксперт', 'Мастер', 'Профи', 'Ветеран', 'Легенда']
    reward = rewards[min(current_level - 1, len(rewards) - 1)]
    
    return {
        'level': current_level,
        'xp': current_xp,
        'nextLevelXp': next_level_xp,
        'progressPercent': max(0, min(100, progress_percent)),
        'reward': reward,
        'dailyXp': user_row['daily_xp'],
        'dailyLimit': 500,
        'reminders': rem_row['total'] or 0,
        'completedReminders': rem_row['completed'] or 0,
        'notes': notes_count,
        'streak': habit_row['total_streak'] or 0,
        'habits': habit_row['habits'] or 0
    }


@app.route('/api/stats/<int:user_id>')
def api_stats(user_id):
    """API для получения статистики"""
    stats = get_user_stats(user_id)
    
    if stats:
        return jsonify({
            'success': True,
            'data': stats
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Пользователь не найден'
        }), 404


@app.route('/api/stats')
def api_stats_current():
    """API для получения статистики текущего пользователя (из Telegram)"""
    # Получаем данные из Telegram WebApp
    tg_data = request.args.get('tg_data', '')
    
    # Для простоты возвращаем демо-данные если нет tg_data
    if not tg_data:
        return jsonify({
            'success': True,
            'data': {
                'level': 5,
                'xp': 450,
                'nextLevelXp': 900,
                'progressPercent': 50,
                'reward': 'Опытный',
                'dailyXp': 150,
                'dailyLimit': 500,
                'reminders': 12,
                'completedReminders': 8,
                'notes': 24,
                'streak': 7,
                'habits': 5
            }
        })
    
    return jsonify({'success': False, 'error': 'Not implemented'})


@app.route('/')
def index():
    """Отдаёт HTML файл Mini App"""
    from flask import send_from_directory
    return send_from_directory(Path(__file__).parent, 'index.html')


if __name__ == '__main__':
    # Инициализация БД
    from database import init_db
    init_db()
    print("✅ Database initialized!")
    
    print("🚀 Запуск сервера Mini App...")
    print("📊 API: /api/stats/<user_id>")
    print("🎮 Mini App: /")
    
    # Render автоматически назначает порт через переменную окружения
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
