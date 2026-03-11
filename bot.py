import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Вставь сюда токен от BotFather
API_TOKEN = '8710704958:AAHFHE-o9ui7_HzkN8rwOn06RC_TZ9Ek3l8'

# Включаем логирование, чтобы видеть ошибки в консоли
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер (управление сообщениями)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот, привязанный к сайту.")

# Обработчик любого текстового сообщения
@dp.message()
async def echo_handler(message: types.Message):
    # Здесь можно добавить логику: если пользователь написал текст,
    # мы можем отправить его на твой сайт или в базу данных.
    await message.answer(f"Вы написали: {message.text}")

# Главная функция запуска
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")