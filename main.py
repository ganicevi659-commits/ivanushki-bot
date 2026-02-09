import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ContentType
import google.genai as genai
from pptx import Presentation
from io import BytesIO
from PIL import Image
import pytesseract

# -------------------------
# Переменные окружения
# -------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("❌ BOT_TOKEN или GEMINI_API_KEY не заданы!")
    exit(1)

# -------------------------
# Настройка модели
# -------------------------
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# -------------------------
# Клавиатура
# -------------------------
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Помощь ИИ")],
        [KeyboardButton(text="Подбор фильмов"), KeyboardButton(text="Задачи по судостроению")],
        [KeyboardButton(text="Презентации"), KeyboardButton(text="Сокращение текстов / Тексты")],
        [KeyboardButton(text="Примеры / Фото"), KeyboardButton(text="Контрольная / Фото")]
    ],
    resize_keyboard=True
)

# -------------------------
# Функции категорий
# -------------------------
def generate_ai_response(prompt: str) -> str:
    """Главная функция ИИ для любых текстовых запросов"""
    try:
        response = model.generate_content(f"Отвечай на русском языке:\n{prompt}")
        return response.text
    except Exception as e:
        return f"❌ Ошибка при генерации ответа: {e}"

def recommend_movies(prompt: str) -> str:
    """ИИ рекомендует топ фильмов по запросу"""
    return generate_ai_response(f"Предложи топ фильмов. Запрос: {prompt}")

def solve_shipbuilding_task(task_text: str) -> str:
    """Решение задач по судостроению"""
    return generate_ai_response(f"Реши задачу по судостроению:\n{task_text}")

def make_presentation(topic: str) -> BytesIO:
    """Создаёт PPTX файл по теме через ИИ"""
    prompt = f"Сделай готовую презентацию по теме: {topic}. Напиши заголовки слайдов и текст каждого слайда."
    slides_text = generate_ai_response(prompt)
    
    prs = Presentation()
    for slide_info in slides_text.split("\n\n"):
        if not slide_info.strip():
            continue
        slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title + Content
        lines = slide_info.split("\n", 1)
        slide.shapes.title.text = lines[0].strip()
        if len(lines) > 1:
            slide.placeholders[1].text = lines[1].strip()
    pptx_file = BytesIO()
    prs.save(pptx_file)
    pptx_file.seek(0)
    return pptx_file

def summarize_text(text: str) -> str:
    """Сокращение или исправление текста"""
    return generate_ai_response(f"Сократи или перепиши текст:\n{text}")

def handle_photo(file_bytes: bytes) -> str:
    """Распознаём текст с фото и отвечаем через ИИ"""
    try:
        img = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(img, lang="rus+eng")
        if not text.strip():
            return "❌ Не удалось распознать текст на фото."
        return generate_ai_response(f"Распознан текст с фото:\n{text}")
    except Exception as e:
        return f"❌ Ошибка обработки фото: {e}"

# -------------------------
# /start
# -------------------------
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.reply(
        "Привет! Я бот «Иванушки» 😎\n\n"
        "Выбери категорию или просто напиши свой вопрос ИИ.",
        reply_markup=keyboard
    )

# -------------------------
# Обработка текстовых сообщений
# -------------------------
@dp.message_handler(content_types=ContentType.TEXT)
async def handle_text(msg: types.Message):
    text = msg.text.strip()

    # Обработка выбора категории
    if text.lower() == "подбор фильмов":
        await msg.reply("🎬 Напиши жанр или тему фильмов, которые хочешь посмотреть.")
    elif text.lower() == "задачи по судостроению":
        await msg.reply("📐 Пришли текст или фото задачи по судостроению, и ИИ решит её.")
elif text.lower() == "презентации":
        await msg.reply("📊 Пришли тему презентации, и ИИ сгенерирует готовый PPTX файл.")
    elif text.lower() == "сокращение текстов / тексты":
        await msg.reply("✏️ Пришли текст, и ИИ его сократит или перепишет.")
    elif text.lower() == "примеры / фото":
        await msg.reply("📸 Пришли фото примера задачи или работы.")
    elif text.lower() == "контрольная / фото":
        await msg.reply("📸 Пришли фото контрольной работы.")
    elif text.lower() == "помощь ии":
        await msg.reply("🤖 Напиши любой вопрос, и ИИ ответит.")
    else:
        # Автоопределение запроса
        if "фильмы" in text.lower():
            await msg.reply(recommend_movies(text))
        elif "задача" in text.lower() or "судостроение" in text.lower():
            await msg.reply(solve_shipbuilding_task(text))
        elif text.lower().startswith("тема:") or "тема презентации" in text.lower():
            topic = text.replace("тема:", "").strip()
            pptx_file = make_presentation(topic)
            await msg.reply_document(document=pptx_file, filename=f"{topic[:20]}.pptx")
        elif len(text) > 20:
            # Любой длинный текст → помощь ИИ / сокращение
            await msg.reply(summarize_text(text))
        else:
            # Короткий текст → просто ИИ отвечает
            await msg.reply(generate_ai_response(text))

# -------------------------
# Обработка фото
# -------------------------
@dp.message_handler(content_types=ContentType.PHOTO)
async def handle_photo_msg(msg: types.Message):
    photo = msg.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    response = handle_photo(file_bytes.read())
    await msg.reply(response)

# -------------------------
# Запуск бота
# -------------------------
if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
