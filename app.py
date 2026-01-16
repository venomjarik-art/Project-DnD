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
    