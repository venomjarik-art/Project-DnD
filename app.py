from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import random
import json
import os
 
app = FastAPI(title="D&D Cards") 
templates = Jinja2Templates(directory="templates")

CARDS_FILE = "data/cards.json"

def load_cards():
    if not os.path.exists(CARDS_FILE):
        os.makedirs(os.path.dirname(CARDS_FILE), exist_ok=True)
        with open(CARDS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    
def save_cards(cards):
         with open(CARDS_FILE, "w", encoding="utf-8") as f:
          json.dump(cards, f, ensure_ascii=False, indent=2)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    cards = load_cards()
    return templates.TemplateResponse("index.html", {"request": request, "cards": cards})
    
@app.post("/", response_class=HTMLResponse)
async def add_card(
    request: Request,
    name: str = Form(...),
    description: str = Form("")
):

    cards = load_cards()
    new_id = max([c.get("id", 0) for c in cards], default=0) + 1
    cards.append({
        "id": new_id,
        "name": name.strip(),
        "description": description.strip()
    })
    save_cards(cards)
    return templates.TemplateResponse("index.html", {"request": request, "cards": cards})

@app.get("/dice", response_class=HTMLResponse)
async def dice_page(request: Request, result: int = None, sides: int = None):
    # result и sides передаются как query-параметры после POST
    return templates.TemplateResponse(
        "dice.html",
        {"request": request, "result": result, "sides": sides}
    )

@app.post("/dice", response_class=HTMLResponse)
async def roll_dice(
    request: Request,
    sides: int = Form(...)
):
    if sides not in [4, 6, 8, 10, 12, 20, 100]:
        result = None
    else:
        result = random.randint(1, sides)
    # Перенаправляем на GET /dice с параметрами
    return templates.TemplateResponse(
        "dice.html",
        {"request": request, "result": result, "sides": sides}
    )

@app.get("/api/cards")
async def api_get_cards():
    return load_cards()

@app.post("/api/cards")
async def api_add_card(card: dict):
    cards = load_cards()
    new_id = max([c.get("id", 0) for c in cards], default=0) + 1
    card["id"] = new_id
    cards.append(card)
    save_cards(cards)
    return {"status": "ok", "id": new_id}

@app.get("/api/roll/{sides}")
async def api_roll_dice(sides: int):
    if sides not in [4, 6, 8, 10, 12, 20, 100]:
        return {"error": "Недопустимое количество граней"}
    return {"sides": sides, "result": random.randint(1, sides)}

