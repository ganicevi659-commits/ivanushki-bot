mport os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
import google.genai as genai
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("Привет 👋\nПросто напиши любой вопрос — я отвечу.")

@dp.message()
async def chat(message: types.Message):
    try:
        response = model.generate_content(
            "Отвечай на русском языке:\n" + message.text
        )
        await message.answer(response.text)
    except:
        await message.answer("Ошибка. Попробуй позже.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
