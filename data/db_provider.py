import sqlite3
from datetime import datetime, timedelta
import uuid
from typing import List, Dict

DATABASE_FILE = "datachat.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # Это позволит получать данные как словари (например, row['username'])
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Таблица для пользователей (id, username)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE
        );
    """)

    # Таблица для сообщений (id, user_id, room, text, timestamp)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            room TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            name TEXT PRIMARY KEY
        );
    """)

    conn.commit()
    conn.close()

def seed_db():
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from seed_data import INITIAL_MESSAGES, INITIAL_ROOMS, INITIAL_USERS
    conn = get_db_connection()
    cursor = conn.cursor()

    # Заполняем пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0: # Если таблица пользователей пуста
        print("Заполняем пользователей...")
        for username in INITIAL_USERS:
            user_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO users (id, username) VALUES (?, ?)", (user_id, username))
            
    # Заполняем комнаты
    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0: # Если таблица комнат пуста
        print("Заполняем комнаты...")
        for room_name in INITIAL_ROOMS:
            cursor.execute("INSERT INTO rooms (name) VALUES (?)", (room_name,))

    # Заполняем сообщения (нужно сначала получить ID пользователей)
    cursor.execute("SELECT COUNT(*) FROM messages")
    if cursor.fetchone()[0] == 0: # Если таблица сообщений пуста
        print("Заполняем сообщения...")
        # Получаем всех пользователей для сопоставления
        users_map ={} 
        for row in conn.execute("SELECT id, username FROM users").fetchall():
            users_map [row['username']]=row['id']

        for room, sender_username, text, minutes_ago in INITIAL_MESSAGES:
            message_id = str(uuid.uuid4())
            user_id = users_map.get(sender_username) # Получаем user_id по username
            if user_id:
                timestamp = datetime.now() - timedelta(minutes=minutes_ago)
                cursor.execute(
                    "INSERT INTO messages (id, user_id, room, text, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (message_id, user_id, room, text, timestamp.isoformat())
                )
            else:
                print(f"Внимание: Пользователь '{sender_username}' не найден для сообщения.")
    
    conn.commit()
    conn.close()

def add_message(user_id, room, text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, room, text) VALUES (?, ?, ?)",
        (user_id, room, text)
    )
    conn.commit()
    conn.close()

def get_messages_for_room(room_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM messages WHERE room= ?", (room_name,))
    res = cursor.fetchall()
    return list(res)

if __name__ == "__main__":
    init_db()
    print(f"База данных {DATABASE_FILE} и таблицы users, messages, rooms инициализированы.")
    seed_db()
    for i in get_messages_for_room("work"):
        print(i[0])