import uvicorn
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime, timedelta



# Создаем основной объект приложения
app = FastAPI()


# Это ОЧЕНЬ ВАЖНО для разработки. Позволяет нашему фронтенду
# делать запросы к этому серверу. В реальном продакшене настройки могут быть строже.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы (GET, POST, DELETE и т.д.)
    allow_headers=["*"],  # Разрешаем все заголовки
)

# Модели данных 
class User(BaseModel):
    id: str
    name: str
    active_rooms: List[str] = []
    status: str = "offline"  # "offline", "online", "away"

class MessageBase(BaseModel):
    sender: User
    text: str
    room: str

class Message(MessageBase):
    id: str
    timestamp: datetime
   

class MessageUpdate(BaseModel):
    text: str

class TypingStatus(BaseModel):
    user: User

# База данных в памяти
alice = User(id=str(uuid.uuid4()), name="Алиса", active_rooms=["general"], status="online")
bob = User(id=str(uuid.uuid4()), name="Боб", active_rooms=["general"], status="online")
charlie = User(id=str(uuid.uuid4()), name="Чарли", active_rooms=["work"], status="online")
DB = {
    "users": [
        alice,
        bob,
        charlie,
    ],
    "messages": [
        Message(id=str(uuid.uuid4()), room="general", sender=alice, text="Всем привет в общем чате!", timestamp=datetime.now() - timedelta(minutes=5)),
        Message(id=str(uuid.uuid4()), room="general", sender=bob, text="И тебе привет!", timestamp=datetime.now() - timedelta(minutes=4)),
        Message(id=str(uuid.uuid4()), room="work", sender=charlie, text="Коллеги, кто проверил мой отчет?", timestamp=datetime.now() - timedelta(minutes=10)),
    ],
    "typing_users": {}, # Словарь для хранения, кто печатает и когда
    "rooms": {
        "general": {
            "active_users": []  # Список ID активных пользователей
        },
        "work": {
            "active_users": []  # Список ID активных пользователей
        }
    }
}


#API - маршруты

@app.get("/users", response_model=List[User], summary="Получить список пользователей")
async def get_users():
    return DB["users"]


@app.get("/rooms/{room_name}/messages", response_model=List[Message], summary="Получить сообщения для комнаты")
async def get_messages(room_name: str):
    room_messages = [msg for msg in DB["messages"] if msg.room == room_name]
    return sorted(room_messages, key=lambda m: m.timestamp)


@app.post("/messages", response_model=Message, status_code=201, summary="Отправить новое сообщение")
async def create_message(message_in: MessageBase):

    new_message = Message(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        **message_in.dict()
    )
    DB["messages"].append(new_message)
    return new_message



@app.delete("/messages/{message_id}", status_code=204, summary="Удалить сообщение")
async def delete_message(message_id: str):
    message_found = False
    for i, msg in enumerate(DB["messages"]):
        if msg.id == message_id:
            del DB["messages"][i]
            message_found = True
            break
    if not message_found:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

@app.get("/messages/poll", response_model=List[Message], summary="Опрос новых сообщений (Polling)")
def poll_new_messages(since:int):
    since = datetime.fromtimestamp(since/1000)
    new_messages = [
        msg for msg in DB["messages"] 
        if  msg.timestamp > since
    ]
    return sorted(new_messages, key=lambda m: m.timestamp)


class UserRegister(BaseModel):
    username: str


@app.post("/register", response_model=User, status_code=201, summary="Зарегистрировать нового пользователя")
async def register_user(user_data:UserRegister):

    # Проверяем: а нет ли уже такого ника?
    for existing_user in DB["users"]:
        if existing_user.name.lower() == user_data.username.lower():
            raise HTTPException(status_code=400, detail="Такой ник уже занят! Выбери другой ")
   
    # Создаём нового пользователя с уникальным ID
    new_user = User(
        id=str(uuid.uuid4()), 
        name=user_data.username
    )
    
    DB["users"].append(new_user)
    
    return new_user


class UserLogin(BaseModel):
    username: str

@app.post("/login")
def login(user_data: UserLogin):
    for user in DB["users"]:
        if user.name.lower() == user_data.username.lower():
            return {"message": "Успешный вход", "user": user}
    raise HTTPException(status_code=404, detail="Пользователь не найден")


# Эндпоинты для управления комнатами и активными пользователями

class JoinRoomRequest(BaseModel):
    user_id: str

class LeaveRoomRequest(BaseModel):
    user_id: str


@app.post("/rooms/{room_name}/join", response_model=Dict, status_code=200, summary="Присоединиться к комнате")
async def join_room(room_name: str, request: JoinRoomRequest):
    # Проверяем, существует ли пользователь
    user_found = None
    for user in DB["users"]:
        if user.id == request.user_id:
            user_found = user
            break
    
    if not user_found:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Создаём комнату, если её нет
    if room_name not in DB["rooms"]:
        DB["rooms"][room_name] = {"active_users": []}
    
    # Проверяем, уже ли пользователь в комнате
    if request.user_id in DB["rooms"][room_name]["active_users"]:
        raise HTTPException(status_code=400, detail="Пользователь уже в этой комнате")
    
    # Добавляем пользователя в комнату
    DB["rooms"][room_name]["active_users"].append(request.user_id)
    
    # Добавляем комнату в активные комнаты пользователя
    if room_name not in user_found.active_rooms:
        user_found.active_rooms.append(room_name)
    
    # Устанавливаем статус в online если был offline
    if user_found.status == "offline":
        user_found.status = "online"
    
    # Получаем список активных пользователей в этой комнате
    active_users = []
    for user_id in DB["rooms"][room_name]["active_users"]:
        for user in DB["users"]:
            if user.id == user_id:
                active_users.append(user)
                break
    
    return {
        "message": f"Успешно присоединился к комнате '{room_name}'",
        "room": room_name,
        "user": user_found,
        "active_users": active_users
    }


@app.get("/rooms/{room_name}/users", response_model=Dict, status_code=200, summary="Получить активных пользователей комнаты")
async def get_room_users(room_name: str):
    # Проверяем, существует ли комната
    if room_name not in DB["rooms"]:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Получаем список активных пользователей
    active_users = []
    for user_id in DB["rooms"][room_name]["active_users"]:
        for user in DB["users"]:
            if user.id == user_id:
                active_users.append(user)
                break
    
    return {
        "room": room_name,
        "active_users": active_users,
        "count": len(active_users)
    }


@app.post("/rooms/{room_name}/leave", response_model=Dict, status_code=200, summary="Покинуть комнату")
async def leave_room(room_name: str, request: LeaveRoomRequest):
    # Проверяем, существует ли комната
    if room_name not in DB["rooms"]:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    # Проверяем, существует ли пользователь
    user_found = None
    for user in DB["users"]:
        if user.id == request.user_id:
            user_found = user
            break
    
    if not user_found:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверяем, находится ли пользователь в комнате
    if request.user_id not in DB["rooms"][room_name]["active_users"]:
        raise HTTPException(status_code=400, detail="Пользователь не находится в этой комнате")
    
    # Удаляем пользователя из комнаты
    DB["rooms"][room_name]["active_users"].remove(request.user_id)
    
    # Удаляем комнату из активных комнат пользователя
    if room_name in user_found.active_rooms:
        user_found.active_rooms.remove(room_name)
    
    # Если у пользователя нет активных комнат, устанавливаем статус offline
    if len(user_found.active_rooms) == 0:
        user_found.status = "offline"
    
    return {
        "message": f"Успешно покинул комнату '{room_name}'",
        "room": room_name,
        "user": user_found
    }






if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
