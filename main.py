from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Tuple
import random
import asyncpg
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from passlib.context import CryptContext
from contextlib import asynccontextmanager
import sys
import traceback

load_dotenv()

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345@127.0.0.1:5432/dnd_database")

async def get_db_connection():
    try:
        print(f"[DEBUG] Подключение к БД: {DATABASE_URL[:50]}...")
        conn = await asyncpg.connect(DATABASE_URL)
        print("[DEBUG] ✅ Подключение к БД успешно")
        return conn
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка подключения к БД: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def init_db():
    try:
        print("[DEBUG] Инициализация БД...")
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
            print("[DEBUG] ✅ Таблица users проверена")
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS character_cards (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    photo_url TEXT,
                    agility INTEGER DEFAULT 0,
                    strength INTEGER DEFAULT 0,
                    health INTEGER DEFAULT 0,
                    speed INTEGER DEFAULT 0,
                    intelligence INTEGER DEFAULT 0,
                    backstory TEXT,
                    personality TEXT,
                    traits TEXT,
                    equipment TEXT,
                    abilities TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("[DEBUG] ✅ Таблица character_cards проверена")
            print("✅ Таблицы БД созданы/проверены")
        finally:
            await conn.close()
            print("[DEBUG] ✅ Соединение с БД закрыто")
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка инициализации БД: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def create_user_in_db(username: str, hashed_password: str, email: str):
    try:
        print(f"[DEBUG] Создание пользователя в БД: {username}")
        conn = await get_db_connection()
        try:
            await conn.execute(
                "INSERT INTO users (username, password, email) VALUES ($1, $2, $3)",
                username, hashed_password, email
            )
            print(f"[DEBUG] ✅ Пользователь {username} создан в БД")
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка создания пользователя {username}: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def get_user_by_username(username: str):
    try:
        print(f"[DEBUG] Поиск пользователя: {username}")
        conn = await get_db_connection()
        try:
            row = await conn.fetchrow(
                "SELECT id, username, password, email FROM users WHERE username = $1",
                username
            )
            result = dict(row) if row else None
            print(f"[DEBUG] {'✅ Пользователь найден' if result else '⚠️ Пользователь не найден'}: {username}")
            return result
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка поиска пользователя {username}: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def get_all_users():
    try:
        print("[DEBUG] Получение списка пользователей")
        conn = await get_db_connection()
        try:
            rows = await conn.fetch("SELECT id, username, email FROM users")
            result = [dict(row) for row in rows]
            print(f"[DEBUG] ✅ Найдено пользователей: {len(result)}")
            return result
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка получения пользователей: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def create_character_card(
    user_id: int, name: str, photo_url: str = None, agility: int = 0,
    strength: int = 0, health: int = 0, speed: int = 0, intelligence: int = 0,
    backstory: str = None, personality: str = None, traits: str = None,
    equipment: str = None, abilities: str = None
):
    try:
        print(f"[DEBUG] Создание карты персонажа: {name} (user_id={user_id})")
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                INSERT INTO character_cards 
                (user_id, name, photo_url, agility, strength, health, speed, intelligence,
                 backstory, personality, traits, equipment, abilities)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                user_id, name, photo_url, agility, strength, health, speed, intelligence,
                backstory, personality, traits, equipment, abilities
            )
            print(f"[DEBUG] ✅ Карта '{name}' создана")
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка создания карты '{name}': {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def get_user_cards(user_id: int):
    try:
        print(f"[DEBUG] Получение карт пользователя {user_id}")
        conn = await get_db_connection()
        try:
            rows = await conn.fetch(
                """
                SELECT id, name, photo_url, agility, strength, health, speed, intelligence
                FROM character_cards WHERE user_id = $1 ORDER BY created_at DESC
                """, user_id
            )
            result = [dict(row) for row in rows]
            print(f"[DEBUG] ✅ Найдено карт: {len(result)}")
            return result
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка получения карт пользователя {user_id}: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def get_card_by_id(card_id: int, user_id: int = None):
    try:
        print(f"[DEBUG] Поиск карты ID={card_id}, user_id={user_id}")
        conn = await get_db_connection()
        try:
            if user_id:
                row = await conn.fetchrow(
                    "SELECT * FROM character_cards WHERE id = $1 AND user_id = $2",
                    card_id, user_id
                )
            else:
                row = await conn.fetchrow("SELECT * FROM character_cards WHERE id = $1", card_id)
            result = dict(row) if row else None
            print(f"[DEBUG] {'✅ Карта найдена' if result else '⚠️ Карта не найдена'}: {card_id}")
            return result
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка поиска карты {card_id}: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def update_character_card(
    card_id: int, user_id: int, name: str = None, photo_url: str = None,
    agility: int = None, strength: int = None, health: int = None, speed: int = None,
    intelligence: int = None, backstory: str = None, personality: str = None,
    traits: str = None, equipment: str = None, abilities: str = None
):
    try:
        print(f"[DEBUG] Обновление карты {card_id} (user_id={user_id})")
        conn = await get_db_connection()
        try:
            updates = []
            values = []
            fields = {
                'name': name, 'photo_url': photo_url, 'agility': agility,
                'strength': strength, 'health': health, 'speed': speed,
                'intelligence': intelligence, 'backstory': backstory,
                'personality': personality, 'traits': traits,
                'equipment': equipment, 'abilities': abilities
            }
            for field, value in fields.items():
                if value is not None:
                    updates.append(f"{field} = ${len(updates)+1}")
                    values.append(value)
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                values.append(card_id)
                values.append(user_id)
                await conn.execute(
                    f"UPDATE character_cards SET {', '.join(updates)} WHERE id = ${len(values)-1} AND user_id = ${len(values)}",
                    *values
                )
                print(f"[DEBUG] ✅ Карта {card_id} обновлена")
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка обновления карты {card_id}: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

async def delete_character_card(card_id: int, user_id: int):
    try:
        print(f"[DEBUG] Удаление карты {card_id} (user_id={user_id})")
        conn = await get_db_connection()
        try:
            await conn.execute(
                "DELETE FROM character_cards WHERE id = $1 AND user_id = $2",
                card_id, user_id
            )
            print(f"[DEBUG] ✅ Карта {card_id} удалена")
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка удаления карты {card_id}: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        print("[DEBUG] Проверка пароля")
        result = pwd_context.verify(plain_password, hashed_password)
        print(f"[DEBUG] {'✅ Пароль верен' if result else '❌ Пароль неверен'}")
        return result
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка проверки пароля: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    try:
        print(f"[DEBUG] Валидация пароля (длина: {len(password)} симв., {len(password.encode('utf-8'))} байт)")
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            print("[DEBUG] ❌ Пароль превышает 72 байта")
            return False, "Пароль слишком длинный (максимум 72 байта). Совет: латинские символы занимают 1 байт, русские — обычно 2 байта."
        if len(password) < 6:
            print("[DEBUG] ❌ Пароль короче 6 символов")
            return False, "Пароль должен быть не менее 6 символов"
        print("[DEBUG] ✅ Пароль прошёл валидацию")
        return True, None
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка валидации пароля: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False, "Ошибка валидации пароля"

def get_password_hash(password: str) -> str:
    try:
        print("[DEBUG] Хеширование пароля")
        if len(password.encode('utf-8')) > 72:
            raise ValueError("Пароль не может быть длиннее 72 байт")
        result = pwd_context.hash(password)
        print("[DEBUG] ✅ Пароль захеширован")
        return result
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка хеширования пароля: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("[DEBUG] Запуск приложения...")
        await init_db()
        print("[DEBUG] ✅ Приложение готово")
        yield
        print("[DEBUG] Завершение приложения...")
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка lifespan: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

app = FastAPI(title="D&D Game Portal", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    try:
        print("[DEBUG] GET /")
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка home_page: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    try:
        print("[DEBUG] GET /login")
        return templates.TemplateResponse("login.html", {"request": request})
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка login_page: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.post("/login", response_class=HTMLResponse)
async def process_login(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        print(f"[DEBUG] POST /login: username={username}")
        user = await get_user_by_username(username)
        if user and verify_password(password, user["password"]):
            print(f"[DEBUG] ✅ Вход успешен: {username}")
            # Передаём username через query parameter
            response = RedirectResponse(f"/dashboard?username={username}", status_code=302)
            return response
        else:
            print(f"[DEBUG] ❌ Вход неудачен: {username}")
            return templates.TemplateResponse("login.html", {
                "request": request, "error": "Неверный логин или пароль", "username": username
            })
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка process_login: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    try:
        print("[DEBUG] GET /register")
        return templates.TemplateResponse("register.html", {"request": request})
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка register_page: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.post("/register", response_class=HTMLResponse)
async def process_register(
    request: Request, username: str = Form(...), password: str = Form(...),
    email: str = Form(""), confirm_password: str = Form(...)
):
    try:
        print(f"[DEBUG] POST /register: username={username}, email={email}")
        errors = []
        
        print("[DEBUG] Этап 1: Валидация пароля")
        is_valid, password_error = validate_password(password)
        if not is_valid:
            print(f"[DEBUG] ❌ Ошибка валидации: {password_error}")
            errors.append(password_error)
        
        print("[DEBUG] Этап 2: Проверка совпадения паролей")
        if password != confirm_password:
            print("[DEBUG] ❌ Пароли не совпадают")
            errors.append("Пароли не совпадают")
        
        print("[DEBUG] Этап 3: Проверка уникальности имени")
        if not errors:
            existing_user = await get_user_by_username(username)
            if existing_user:
                print(f"[DEBUG] ❌ Пользователь {username} уже существует")
                errors.append("Пользователь с таким именем уже существует")
        
        if errors:
            print(f"[DEBUG] ❌ Ошибки регистрации: {'; '.join(errors)}")
            return templates.TemplateResponse("register.html", {
                "request": request, "error": "; ".join(errors),
                "username": username, "email": email
            })
        
        print("[DEBUG] Этап 4: Хеширование пароля")
        hashed_password = get_password_hash(password)
        
        print("[DEBUG] Этап 5: Создание пользователя в БД")
        await create_user_in_db(
            username=username, hashed_password=hashed_password,
            email=email if email else f"{username}@example.com"
        )
        
        print(f"[DEBUG] Регистрация успешна: {username}")
        # Перенаправляем на dashboard
        response = RedirectResponse("/dashboard", status_code=302)
        return response
        
    except Exception as e:
        print(f"[ERROR] Ошибка process_register: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/dice", response_class=HTMLResponse)
async def dice_page(request: Request):
    try:
        print("[DEBUG] GET /dice")
        return templates.TemplateResponse("dice.html", {"request": request, "result": None})
    except Exception as e:
        print(f"[ERROR] Ошибка dice_page: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.post("/dice", response_class=HTMLResponse)
async def roll_dice_page(request: Request, sides: int = Form(6), count: int = Form(1)):
    try:
        print(f"[DEBUG] POST /dice: sides={sides}, count={count}")
        if sides < 2: sides = 6
        if count < 1 or count > 10: count = 1
        results = [random.randint(1, sides) for _ in range(count)]
        return templates.TemplateResponse("dice.html", {
            "request": request, "result": {
                "sides": sides, "count": count, "rolls": results,
                "total": sum(results),
                "average": round(sum(results) / len(results), 2) if results else 0
            }
        })
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка roll_dice_page: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, username: str = "Гость"):
    try:
        print(f"[DEBUG] GET /dashboard, username={username}")
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "username": username
        })
    except Exception as e:
        print(f"[ERROR] Ошибка dashboard: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/create-card", response_class=HTMLResponse)
async def create_card_page(request: Request):
    try:
        print("[DEBUG] GET /create-card")
        return templates.TemplateResponse("create-card.html", {"request": request})
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка create_card_page: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.post("/save-card", response_class=HTMLResponse)
async def save_card(
    request: Request, name: str = Form(...), strength: int = Form(0),
    agility: int = Form(0), health: int = Form(0), speed: int = Form(0),
    intelligence: int = Form(0), photo: UploadFile = File(None)
):
    try:
        print(f"[DEBUG] POST /save-card: name={name}")
        photo_url = None
        if photo and photo.filename:
            print(f"[DEBUG] Обработка фото: {photo.filename}")
            file_path = UPLOAD_DIR / photo.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            photo_url = f"/static/uploads/{photo.filename}"
            print(f"[DEBUG] ✅ Фото сохранено: {photo_url}")
        
        user_id = 1
        await create_character_card(
            user_id=user_id, name=name, photo_url=photo_url,
            strength=strength, agility=agility, health=health,
            speed=speed, intelligence=intelligence
        )
        print("[DEBUG] ✅ Карта сохранена, редирект на /my-cards")
        return RedirectResponse("/my-cards", status_code=302)
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка save_card: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/my-cards", response_class=HTMLResponse)
async def my_cards(request: Request):
    try:
        print("[DEBUG] GET /my-cards")
        user_id = 1
        cards = await get_user_cards(user_id)
        return templates.TemplateResponse("my-cards.html", {"request": request, "cards": cards})
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка my_cards: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/view-card/{card_id}", response_class=HTMLResponse)
async def view_card(request: Request, card_id: int):
    try:
        print(f"[DEBUG] GET /view-card/{card_id}")
        user_id = 1
        card = await get_card_by_id(card_id, user_id)
        if not card:
            print(f"[DEBUG] ❌ Карта {card_id} не найдена")
            raise HTTPException(404, "Карта не найдена")
        print(f"[DEBUG] ✅ Карта {card_id} найдена")
        return templates.TemplateResponse("view-card.html", {"request": request, "card": card})
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка view_card: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.post("/update-card/{card_id}", response_class=HTMLResponse)
async def update_card(
    request: Request, card_id: int, name: str = Form(None), strength: int = Form(None),
    agility: int = Form(None), health: int = Form(None), speed: int = Form(None),
    intelligence: int = Form(None), backstory: str = Form(None), personality: str = Form(None),
    traits: str = Form(None), equipment: str = Form(None), abilities: str = Form(None),
    photo: UploadFile = File(None)
):
    try:
        print(f"[DEBUG] POST /update-card/{card_id}")
        user_id = 1
        photo_url = None
        if photo and photo.filename:
            print(f"[DEBUG] Обработка нового фото: {photo.filename}")
            file_path = UPLOAD_DIR / photo.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            photo_url = f"/static/uploads/{photo.filename}"
        
        await update_character_card(
            card_id=card_id, user_id=user_id, name=name, photo_url=photo_url,
            strength=strength, agility=agility, health=health, speed=speed,
            intelligence=intelligence, backstory=backstory, personality=personality,
            traits=traits, equipment=equipment, abilities=abilities
        )
        print(f"[DEBUG] ✅ Карта {card_id} обновлена, редирект")
        return RedirectResponse(f"/view-card/{card_id}", status_code=302)
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка update_card: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/instrumentation", response_class=HTMLResponse)
async def instrumentation_page(request: Request):
    try:
        print("[DEBUG] GET /instrumentation")
        return templates.TemplateResponse("instrumentation.html", {"request": request})
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка instrumentation_page: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.post("/update-instrumentation", response_class=HTMLResponse)
async def update_instrumentation(
    request: Request, backstory_extended: str = Form(None), personality_extended: str = Form(None),
    habits: str = Form(None), combat_skills: str = Form(None), magic_abilities: str = Form(None),
    other_skills: str = Form(None), weapons: str = Form(None), armor: str = Form(None),
    magic_items: str = Form(None), other_equipment: str = Form(None)
):
    try:
        print("[DEBUG] POST /update-instrumentation")
        return RedirectResponse("/my-cards", status_code=302)
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка update_instrumentation: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    try:
        print("[DEBUG] GET /logout")
        return RedirectResponse("/", status_code=302)
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка logout: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.post("/api/dice")
async def api_roll_dice(roll: DiceRoll):
    try:
        print(f"[DEBUG] API POST /api/dice: sides={roll.sides}, count={roll.count}")
        if roll.sides < 2:
            raise HTTPException(400, "Dice must have at least 2 sides")
        if roll.count < 1 or roll.count > 100:
            raise HTTPException(400, "Count must be between 1 and 100")
        results = [random.randint(1, roll.sides) for _ in range(roll.count)]
        return {"sides": roll.sides, "count": roll.count, "results": results,
                "total": sum(results), "average": round(sum(results) / len(results), 2)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка api_roll_dice: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/api/users")
async def api_list_users():
    try:
        print("[DEBUG] API GET /api/users")
        users_list = await get_all_users()
        return {"users": users_list}
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка api_list_users: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/api/cards")
async def api_get_user_cards():
    try:
        print("[DEBUG] API GET /api/cards")
        user_id = 1
        cards = await get_user_cards(user_id)
        return {"cards": cards}
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка api_get_user_cards: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.get("/places", response_class=HTMLResponse)
async def places_page(request: Request):
    try:
        print("[DEBUG] GET /places")
        return templates.TemplateResponse("places.html", {"request": request})
    except Exception as e:
        print(f"[ERROR] Ошибка places_page: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

@app.post("/api/cards")
async def api_create_card(card: Card):
    try:
        print(f"[DEBUG] API POST /api/cards: {card.name}")
        return {"message": "Card created", "card": card}
    except Exception as e:
        print(f"[ERROR] ❌ Ошибка api_create_card: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    import uvicorn
    print(f"[DEBUG] Запуск сервера на 0.0.0.0:8000 (Python {sys.version})")
    uvicorn.run(app, host="0.0.0.0", port=8000)
