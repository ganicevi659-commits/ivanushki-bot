import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import google.generativeai as genai

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ALLOWED_USERS = {"GanyaVanichev", "vaizmolld"}

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: types.Message):
    if msg.from_user.username not in ALLOWED_USERS:
        await msg.answer("❌ Доступ только по приглашению.")
        return
    await msg.answer(
        "👋 Я бот «Иванушки»\n\n"
        "🎬 Подбор фильмов\n"
        "✍️ Тексты\n"
        "📉 Презентации\n"
        "📸 Решение задач по фото\n"
        "💡 Советы\n\n"
        "Просто напиши, что нужно 🙂"
    )

@dp.message()
async def chat(msg: types.Message):
    if msg.from_user.username not in ALLOWED_USERS:
        return
    response = model.generate_content(
        f"Отвечай на русском языке.\nЗапрос пользователя:\n{msg.text}"
    )
    await msg.answer(response.text)

if name == "__main__":
    dp.run_polling(bot)
