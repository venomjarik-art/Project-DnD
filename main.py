
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import random

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

#новое
class Card(BaseModel):
    id: int
    name: str
    hp: int
    intelligence: int
    strength: int
    card_type: str

#новое
class UserWithCards(BaseModel):
    id: int
    username: str
    email: Optional[str]
    cards: List[Card]
    total_cards: int

# ==================== HTML СТРАНИЦЫ ====================

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа (HTML форма)"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None
    })

@app.post("/login", response_class=HTMLResponse)
async def process_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Обработка формы входа"""
    if username in users_db and users_db[username]["password"] == password:
        # Успешный вход - редирект на главную
        return RedirectResponse("/", status_code=302)
    else:
        # Ошибка - показываем форму снова
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверный логин или пароль",
            "username": username
        })

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации (HTML форма)"""
    return templates.TemplateResponse("register.html", {
        "request": request,
        "error": None
    })

@app.post("/register", response_class=HTMLResponse)
async def process_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(""),
    confirm_password: str = Form(...)
):
    """Обработка формы регистрации"""
    
    # Валидация
    errors = []
    
    if username in users_db:
        errors.append("Пользователь с таким именем уже существует")
    
    if len(password) < 6:
        errors.append("Пароль должен быть не менее 6 символов")
    
    if password != confirm_password:
        errors.append("Пароли не совпадают")
    
    if errors:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "; ".join(errors),
            "username": username,
            "email": email
        })
    
    # Регистрация
    users_db[username] = {
        "password": password,
        "email": email if email else f"{username}@example.com"
    }
    
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

class DiceRoll(BaseModel):
    sides: int = 6
    count: int = 1

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
    users_list = []
    for username, data in users_db.items():
        users_list.append({
            "username": username,
            "email": data["email"]
        })
    
    return {"users": users_list}

