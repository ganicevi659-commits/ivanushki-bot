import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, Text
import google.genai as genai  # новая библиотека

# Токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Разрешённые пользователи
ALLOWED_USERS = {"GanyaVanichev", "vaizmolld"}

# Настройка модели
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Инициализация бота
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def start(msg: types.Message):
    if msg.from_user.username not in ALLOWED_USERS:
        await msg.answer("❌ Доступ только по приглашению.")
        return

    # Главное меню
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Подбор фильмов"), types.KeyboardButton(text="Тексты")],
            [types.KeyboardButton(text="Презентации"), types.KeyboardButton(text="Решение задач")],
            [types.KeyboardButton(text="Советы")]
        ],
        resize_keyboard=True
    )

    await msg.answer(
        "Я бот «Иванушки»\n\n"
        "Выберите действие из меню или просто напишите, что нужно:",
        reply_markup=keyboard
    )

# Обработка всех текстов
@dp.message()
async def chat(msg: types.Message):
    if msg.from_user.username not in ALLOWED_USERS:
        return

    text = msg.text.lower()

    # Простые ответы на пункты меню
    if "подбор фильмов" in text:
        await msg.answer("🎬 Вы выбрали Подбор фильмов. Скиньте жанр или фильм, и я подберу варианты!")
        return
    elif "тексты" in text:
        await msg.answer("📝 Вы выбрали Тексты. Напишите тему, и я сгенерирую текст.")
        return
    elif "презентации" in text:
        await msg.answer("📊 Вы выбрали Презентации. Опишите тему — я помогу слайд за слайдом.")
        return
    elif "решение задач" in text:
        await msg.answer("📸 Вы выбрали Решение задач по фото. Пришлите фото задачи.")
        return
    elif "советы" in text:
        await msg.answer("💡 Вы выбрали Советы. Задайте вопрос, и я дам рекомендации.")
        return

    # Если текст не совпадает с меню, используем модель для ответа
    try:
        response = model.generate_content(
            f"Отвечай на русском языке. Запрос пользователя:\n{msg.text}"
        )
        await msg.answer(response.text)
    except Exception as e:
        await msg.answer(f"❌ Ошибка при генерации ответа: {e}")

# Запуск бота
if __name__ == "__main__":
    dp.run_polling(bot)
