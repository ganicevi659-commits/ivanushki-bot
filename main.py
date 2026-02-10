import os
import json
import time
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from google import genai

# ---------- Логирование ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Загружаем .env ----------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", 3))
MAX_WARNINGS = int(os.getenv("MAX_WARNINGS", 3))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

DATA_FILE = "user_data.json"
BLACKLIST_FILE = "blacklist.json"

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY обязательны!")

# ---------- Загрузка данных ----------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        user_data = json.load(f)
else:
    user_data = {}

if os.path.exists(BLACKLIST_FILE):
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        blacklist = json.load(f)
else:
    blacklist = []

last_message_time = {}  # {user_id: timestamp}

# ---------- Gemini 2.5 Flash ----------
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

# ---------- Сохранение данных ----------
def save_user_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=4)

# ---------- Проверка блокировки ----------
def is_blocked(user_id):
    return user_id in blacklist

# ---------- Команды ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return
    user_key = str(user_id)
    if user_key not in user_data:
        user_data[user_key] = {"name": None, "history": [], "warnings": 0}
        save_user_data()
        text = "Привет! Я бот на Gemini 2.5 Flash 🚀\nНапиши своё имя, и я тебя запомню!"
        image_url = "https://i.imgur.com/5cX9a9k.jpg"  # пример картинки
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image_url,
            caption=text
        )
    else:
        await update.message.reply_text("С возвращением! Пиши что угодно — я отвечу.")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return
    user_key = str(user_id)
    if user_key in user_data:
        user_data[user_key]["history"] = []
        save_user_data()
    await update.message.reply_text("Чат очищен! Можешь писать дальше.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return
    text = (
        "💡 Список команд:\n"
        "/start - Запустить бота\n"
        "/new - Очистить чат\n"
        "/help - Показать это сообщение\n"
        "/about - Информация о боте\n"
        "/block <user_id> - Заблокировать пользователя (только админ)\n"
        "/unblock <user_id> - Разблокировать пользователя (только админ)\n"
        "🚀 Дополнительно: бот может предупреждать, мутить и удалять сообщения нарушителей"
    )
    await update.message.reply_text(text)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return
    text = (
        "🤖 Бот на Gemini 2.5 Flash\n"
        "Память: запоминаю имя пользователя и приветствую новых\n"
        "Защита: rate-limit, черный список, анти-спам, удаление сообщений"
    )
    await update.message.reply_text(text)

# ---------- Черный список ----------
async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Только админ может блокировать пользователей")
        return
    if not context.args:
        await update.message.reply_text("Использование: /block <user_id>")
        return
    try:
        block_id = int(context.args[0])
        if block_id not in blacklist:
            blacklist.append(block_id)
            save_blacklist()
        await update.message.reply_text(f"Пользователь {block_id} добавлен в черный список ✅")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Только админ может разблокировать пользователей")
        return
    if not context.args:
        await update.message.reply_text("Использование: /unblock <user_id>")
        return
    try:
        unblock_id = int(context.args[0])
        if unblock_id in blacklist:
            blacklist.remove(unblock_id)
            save_blacklist()
        await update.message.reply_text(f"Пользователь {unblock_id} удалён из черного списка ✅")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID")

# ---------- Обработка сообщений ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return

    user_key = str(user_id)
    text = update.message.text.strip()
    now = time.time()

    # ---------- Rate-limit ----------
    if user_id in last_message_time and now - last_message_time[user_id] < RATE_LIMIT:
        await update.message.reply_text(f"⏱ Подожди {RATE_LIMIT} секунд перед следующим сообщением")
        return
    last_message_time[user_id] = now

    # ---------- Память имени ----------
    if user_key in user_data and not user_data[user_key].get("name"):
        user_data[user_key]["name"] = text
        save_user_data()
        await update.message.reply_text(f"Приятно познакомиться, {text}!")
        return

    prompt = f"Пользователь {user_data[user_key]['name']} спрашивает: {text}" \
        if user_key in user_data else text

    logger.info(f"Запрос к Gemini: {prompt}")

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        # ---------- Gemini 2.5 Flash новый синтаксис ----------
        model = client.models.get(MODEL_NAME)
        response = model.generate(prompt=prompt)
        answer = response.output_text

        await update.message.reply_text(answer)

    except Exception as e:
        logger.exception("Gemini ошибка")
        await update.message.reply_text(f"❌ Gemini ошибка:\n{type(e).__name__}: {str(e)[:300]}")

# ---------- Основной запуск ----------
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", clear_chat))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("block", block_command))
    application.add_handler(CommandHandler("unblock", unblock_command))

    # Сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ Бот запущен в polling режиме")
    application.run_polling()

if __name__ == "__main__":
    main()


