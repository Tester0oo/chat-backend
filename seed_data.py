from datetime import datetime, timedelta

# Начальные пользователи (без ID, ID сгенерируем при добавлении)
INITIAL_USERS = [
    "Алиса",
    "Боб",
    "Чарли",
]

# Начальные комнаты
INITIAL_ROOMS = [
    "general",
    "work",
    "random",
]

# Начальные сообщения (без ID и user_id, их сгенерируем)
# Пример: ("room_name", "sender_username", "text", "minutes_ago")
INITIAL_MESSAGES = [
    ("general", "Алиса", "Всем привет в общем чате!", 5),
    ("general", "Боб", "И тебе привет!", 4),
    ("work", "Чарли", "Коллеги, кто проверил мой отчет?", 10),
    ("random", "Алиса", "Что нового?", 2),
]