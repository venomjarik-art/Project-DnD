import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123@localhost:5432/card_game_db")

async def get_db_connection():
    """Создание подключения к БД"""
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    """Инициализация таблиц в БД"""
    conn = await get_db_connection()
    try:
        # Таблица пользователей
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица карт персонажей
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
        print("✅ Таблицы БД созданы/проверены")
    finally:
        await conn.close()

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
            "SELECT id, username, password, email FROM users WHERE username = $1",
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

# Новые функции для работы с картами
async def create_character_card(
    user_id: int,
    name: str,
    photo_url: str = None,
    agility: int = 0,
    strength: int = 0,
    health: int = 0,
    speed: int = 0,
    intelligence: int = 0,
    backstory: str = None,
    personality: str = None,
    traits: str = None,
    equipment: str = None,
    abilities: str = None
):
    """Создание новой карты персонажа"""
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
        print(f"✅ Карта персонажа '{name}' создана")
    finally:
        await conn.close()

async def get_user_cards(user_id: int):
    """Получение всех карт пользователя"""
    conn = await get_db_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT id, name, photo_url, agility, strength, health, speed, intelligence
            FROM character_cards 
            WHERE user_id = $1 
            ORDER BY created_at DESC
            """,
            user_id
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def get_card_by_id(card_id: int, user_id: int = None):
    """Получение карты по ID (опционально с проверкой владельца)"""
    conn = await get_db_connection()
    try:
        if user_id:
            row = await conn.fetchrow(
                """
                SELECT * FROM character_cards 
                WHERE id = $1 AND user_id = $2
                """,
                card_id, user_id
            )
        else:
            row = await conn.fetchrow(
                "SELECT * FROM character_cards WHERE id = $1",
                card_id
            )
        return dict(row) if row else None
    finally:
        await conn.close()

async def update_character_card(
    card_id: int,
    user_id: int,
    name: str = None,
    photo_url: str = None,
    agility: int = None,
    strength: int = None,
    health: int = None,
    speed: int = None,
    intelligence: int = None,
    backstory: str = None,
    personality: str = None,
    traits: str = None,
    equipment: str = None,
    abilities: str = None
):
    """Обновление карты персонажа"""
    conn = await get_db_connection()
    try:
        updates = []
        values = []
        params = []
        
        if name is not None:
            updates.append(f"name = ${len(updates)+1}")
            values.append(name)
        if photo_url is not None:
            updates.append(f"photo_url = ${len(updates)+1}")
            values.append(photo_url)
        if agility is not None:
            updates.append(f"agility = ${len(updates)+1}")
            values.append(agility)
        if strength is not None:
            updates.append(f"strength = ${len(updates)+1}")
            values.append(strength)
        if health is not None:
            updates.append(f"health = ${len(updates)+1}")
            values.append(health)
        if speed is not None:
            updates.append(f"speed = ${len(updates)+1}")
            values.append(speed)
        if intelligence is not None:
            updates.append(f"intelligence = ${len(updates)+1}")
            values.append(intelligence)
        if backstory is not None:
            updates.append(f"backstory = ${len(updates)+1}")
            values.append(backstory)
        if personality is not None:
            updates.append(f"personality = ${len(updates)+1}")
            values.append(personality)
        if traits is not None:
            updates.append(f"traits = ${len(updates)+1}")
            values.append(traits)
        if equipment is not None:
            updates.append(f"equipment = ${len(updates)+1}")
            values.append(equipment)
        if abilities is not None:
            updates.append(f"abilities = ${len(updates)+1}")
            values.append(abilities)
        
        if updates:
            updates.append(f"updated_at = CURRENT_TIMESTAMP")
            values.append(card_id)
            values.append(user_id)
            
            await conn.execute(
                f"""
                UPDATE character_cards 
                SET {', '.join(updates)}
                WHERE id = ${len(values)-1} AND user_id = ${len(values)}
                """,
                *values
            )
            print(f"✅ Карта {card_id} обновлена")
    finally:
        await conn.close()

async def delete_character_card(card_id: int, user_id: int):
    """Удаление карты персонажа"""
    conn = await get_db_connection()
    try:
        await conn.execute(
            """
            DELETE FROM character_cards 
            WHERE id = $1 AND user_id = $2
            """,
            card_id, user_id
        )
        print(f"✅ Карта {card_id} удалена")
    finally:
        await conn.close()