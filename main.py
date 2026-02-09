import os
from io import BytesIO
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ContentType
from aiogram import executor
from pptx import Presentation
from PIL import Image
import pytesseract
import google.genai as genai
import feedparser  # Для новостей СПб

# ===============================
# Настройки и ключи
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("❌ BOT_TOKEN или GEMINI_API_KEY не заданы!")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===============================
# Клавиатура
# ===============================
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Помощь ИИ")],
        [KeyboardButton(text="Подбор фильмов"), KeyboardButton(text="Задачи по судостроению")],
        [KeyboardButton(text="Презентации"), KeyboardButton(text="Сокращение текстов / Тексты")],
        [KeyboardButton(text="Примеры / Фото"), KeyboardButton(text="Контрольная / Фото")],
        [KeyboardButton(text="Новости СПб")]
    ],
    resize_keyboard=True
)

# ===============================
# Вспомогательные функции ИИ
# ===============================
def generate_ai_response(prompt: str) -> str:
    try:
        response = model.generate_content(f"Отвечай на русском языке:\n{prompt}")
        return response.text
    except Exception as e:
        return f"❌ Ошибка при генерации ответа: {e}"

def recommend_movies(prompt: str) -> str:
    return generate_ai_response(f"Предложи топ фильмов. Запрос: {prompt}")

def solve_shipbuilding_task(task_text: str) -> str:
    return generate_ai_response(f"Реши задачу по судостроению:\n{task_text}")

def make_presentation(topic: str) -> BytesIO:
    prompt = f"Сделай готовую презентацию по теме: {topic}. Заголовки слайдов и текст."
    slides_text = generate_ai_response(prompt)
    
    prs = Presentation()
    for slide_info in slides_text.split("\n\n"):
        if not slide_info.strip():
            continue
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        lines = slide_info.split("\n", 1)
        slide.shapes.title.text = lines[0].strip()
        if len(lines) > 1:
            slide.placeholders[1].text = lines[1].strip()
    pptx_file = BytesIO()
    prs.save(pptx_file)
    pptx_file.seek(0)
    return pptx_file

def summarize_text(text: str) -> str:
    return generate_ai_response(f"Сократи или перепиши текст:\n{text}")

def handle_photo(file_bytes: bytes) -> str:
    try:
        img = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(img, lang="rus+eng")
        if not text.strip():
            return "❌ Не удалось распознать текст на фото."
        return generate_ai_response(f"Распознан текст с фото:\n{text}")
    except Exception as e:
        return f"❌ Ошибка обработки фото: {e}"

def get_spb_news(limit=5) -> str:
    rss_urls = [
        "https://www.fontanka.ru/fontanka.rss",      # Фонтанка (СПб)
        "https://www.47news.ru/rss/all.xml"         # 47news (Ленобласть)
    ]

    all_entries = []
    for url in rss_urls:
        feed = feedparser.parse(url)
        all_entries.extend(feed.entries)

    # Сортируем по дате (самые новые сверху)
    all_entries.sort(key=lambda x: x.get("published_parsed", 0), reverse=True)

    # Берём только limit новостей
    latest_news = all_entries[:limit]
    if not latest_news:
        return "❌ Не удалось получить новости."

    news_texts = []
    for entry in latest_news:
        # Используем ИИ, чтобы кратко сформулировать новость
        summary_prompt = f"Сделай краткий, понятный пересказ новости: {entry.title}\nСсылка: {entry.link}"
        summarized = generate_ai_response(summary_prompt)
        news_texts.append(summarized)

    return "\n\n".join(news_texts)

# ===============================
# Хэндлеры
# ===============================
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.reply(
        "Привет! Я бот «Иванушки» 😎\n\n"
        "Выбери категорию или просто напиши свой вопрос ИИ.",
        reply_markup=keyboard
    )

@dp.message_handler(content_types=ContentType.TEXT)
async def handle_text(msg: types.Message):
    text = msg.text.strip().lower()

    if text == "подбор фильмов":
        await msg.reply("🎬 Напиши жанр или тему фильмов, которые хочешь посмотреть.")
    elif text == "задачи по судостроению":
        await msg.reply("📐 Пришли текст или фото задачи по судостроению, и ИИ решит её.")
    elif text == "презентации":
        await msg.reply("📊 Пришли тему презентации, и ИИ сгенерирует готовый PPTX файл.")
    elif text == "сокращение текстов / тексты":
        await msg.reply("✏️ Пришли текст, и ИИ его сократит или перепишет.")
    elif text == "примеры / фото":
        await msg.reply("📸 Пришли фото примера задачи или работы.")
    elif text == "контрольная / фото":
        await msg.reply("📸 Пришли фото контрольной работы.")
    elif text == "помощь ии":
        await msg.reply("🤖 Напиши любой вопрос, и ИИ ответит.")
    elif text == "новости спб":
        news = get_spb_news()
        await msg.reply(news)
    else:
        # Всё остальное — ИИ
        if "фильмы" in text:
            await msg.reply(recommend_movies(text))
        elif "задача" in text or "судостроение" in text:
            await msg.reply(solve_shipbuilding_task(text))
        elif text.startswith("тема:") or "тема презентации" in text:
            topic = text.replace("тема:", "").strip()
            pptx_file = make_presentation(topic)
            await msg.reply_document(document=pptx_file, filename=f"{topic[:20]}.pptx")
        elif len(text) > 20:
            await msg.reply(summarize_text(text))
        else:
            await msg.reply(generate_ai_response(text))

@dp.message_handler(content_types=ContentType.PHOTO)
async def handle_photo_msg(msg: types.Message):
    photo = msg.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    response = handle_photo(file_bytes.read())
    await msg.reply(response)

# ===============================
# Запуск
# ===============================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
