from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import random
import asyncpg
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

app = FastAPI(title="Game API")

# Подключаем статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ==================== НАСТРОЙКИ БАЗЫ ДАННЫХ ====================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/card_game_db")

# Модели данных
class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class Card(BaseModel):
    id: int
    name: str
    hp: int
    intelligence: int
    strength: int
    card_type: str

class UserWithCards(BaseModel):
    id: int
    username: str
    email: Optional[str]
    cards: List[Card]
    total_cards: int

class DiceRoll(BaseModel):
    sides: int = 6
    count: int = 1

# ==================== РАБОТА С БД ====================

async def get_db_connection():
    """Создание подключения к БД"""
    return await asyncpg.connect(DATABASE_URL)

async def create_user_in_db(username: str, hashed_password: str, email: str):
    """Создание пользователя в БД"""
    conn = await get_db_connection()
    try:
        await conn.execute(
            """
            INSERT INTO users (username, password, email)
            VALUES ($1, $2, $3)
            """,
            username, hashed_password, email
        )
        print(f"✅ Пользователь {username} создан в БД")
    finally:
        await conn.close()

async def get_user_by_username(username: str):
    """Получение пользователя по имени"""
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow(
            "SELECT username, password, email FROM users WHERE username = $1",
            username
        )
        return dict(row) if row else None
    finally:
        await conn.close()

async def get_all_users():
    """Получение всех пользователей"""
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("SELECT id, username, email FROM users")
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def init_db():
    """Инициализация таблиц в БД"""
    conn = await get_db_connection()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Таблицы БД созданы/проверены")
    finally:
        await conn.close()

# ==================== БЕЗОПАСНОСТЬ ====================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# ==================== HTML СТРАНИЦЫ ====================

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа (GET)"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def process_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Обработка формы входа"""
    user = await get_user_by_username(username)
    
    if user and verify_password(password, user["password"]):
        return RedirectResponse("/", status_code=302)
    else:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверный логин или пароль",
            "username": username
        })

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации (GET)"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def process_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(""),
    confirm_password: str = Form(...)
):
    """Обработка формы регистрации"""
    errors = []
    
    if len(password) < 6:
        errors.append("Пароль должен быть не менее 6 символов")
    
    if password != confirm_password:
        errors.append("Пароли не совпадают")
    
    if not errors:
        existing_user = await get_user_by_username(username)
        if existing_user:
            errors.append("Пользователь с таким именем уже существует")
    
    if errors:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "; ".join(errors),
            "username": username,
            "email": email
        })
    
    hashed_password = get_password_hash(password)
    
    await create_user_in_db(
        username=username,
        hashed_password=hashed_password,
        email=email if email else f"{username}@example.com"
    )
    
    return templates.TemplateResponse("register_success.html", {
        "request": request,
        "username": username
    })

@app.get("/dice", response_class=HTMLResponse)
async def dice_page(request: Request):
    """Страница игры в кости"""
    return templates.TemplateResponse("dice.html", {
        "request": request,
        "result": None
    })

@app.post("/dice", response_class=HTMLResponse)
async def roll_dice_page(
    request: Request,
    sides: int = Form(6),
    count: int = Form(1)
):
    """Бросок кубиков через форму"""
    if sides < 2:
        sides = 6
    if count < 1 or count > 10:
        count = 1
    
    results = [random.randint(1, sides) for _ in range(count)]
    
    return templates.TemplateResponse("dice.html", {
        "request": request,
        "result": {
            "sides": sides,
            "count": count,
            "rolls": results,
            "total": sum(results),
            "average": round(sum(results) / len(results), 2) if results else 0
        }
    })

# ==================== API ЭНДПОИНТЫ (JSON) ====================

@app.post("/api/dice")
async def api_roll_dice(roll: DiceRoll):
    """API для броска кубиков (JSON)"""
    if roll.sides < 2:
        raise HTTPException(400, "Dice must have at least 2 sides")
    if roll.count < 1 or roll.count > 100:
        raise HTTPException(400, "Count must be between 1 and 100")
    
    results = [random.randint(1, roll.sides) for _ in range(roll.count)]
    
    return {
        "sides": roll.sides,
        "count": roll.count,
        "results": results,
        "total": sum(results),
        "average": round(sum(results) / len(results), 2)
    }

@app.get("/api/users")
async def api_list_users():
    """API для получения списка пользователей"""
    users_list = await get_all_users()
    return {"users": users_list}

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == "__main__":
    import uvicorn
    
    # Инициализация БД перед запуском
    import asyncio
    asyncio.run(init_db())
    
    uvicorn.run(app, host="0.0.0.0", port=8000)