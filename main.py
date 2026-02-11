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
    ContextTypes,
    filters,
)

from google import genai

# ---------- Логи ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- ENV ----------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", 3))
MAX_WARNINGS = int(os.getenv("MAX_WARNINGS", 3))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("❌ TELEGRAM_TOKEN и GEMINI_API_KEY обязательны")

# ---------- Файлы ----------
DATA_FILE = "user_data.json"
BLACKLIST_FILE = "blacklist.json"

user_data = {}
blacklist = []
last_message_time = {}

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        user_data = json.load(f)

if os.path.exists(BLACKLIST_FILE):
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        blacklist = json.load(f)

# ---------- Gemini ----------
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

# ---------- Utils ----------
def save_user_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=4)

def is_blocked(user_id: int) -> bool:
    return user_id in blacklist

# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return

    key = str(user_id)
    if key not in user_data:
        user_data[key] = {
            "name": None,
            "warnings": 0,
        }
        save_user_data()
        await update.message.reply_text(
            "👋 Привет! Как тебя зовут?"
        )
    else:
        await update.message.reply_text("С возвращением! Пиши 👇")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_blocked(update.effective_user.id):
        return

    await update.message.reply_text(
        "💡 Команды:\n"
        "/start — начать\n"
        "/help — помощь\n"
        "/about — о боте\n"
        "/block <id> — блок (админ)\n"
        "/unblock <id> — анблок (админ)"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_blocked(update.effective_user.id):
        return

    await update.message.reply_text(
        "🤖 Telegram-бот на Gemini 2.5 Flash\n"
        "• google-genai SDK\n"
        "• анти-спам\n"
        "• blacklist"
    )

# ---------- Blacklist ----------
async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Только админ")
        return

    if not context.args:
        await update.message.reply_text("Использование: /block <user_id>")
        return

    try:
        uid = int(context.args[0])
        if uid not in blacklist:
            blacklist.append(uid)
            save_blacklist()
        await update.message.reply_text(f"✅ {uid} заблокирован")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Только админ")
        return

    if not context.args:
        await update.message.reply_text("Использование: /unblock <user_id>")
        return

    try:
        uid = int(context.args[0])
        if uid in blacklist:
            blacklist.remove(uid)
            save_blacklist()
        await update.message.reply_text(f"✅ {uid} разблокирован")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID")

# ---------- Messages ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return

    text = update.message.text.strip()
    now = time.time()

    # Rate limit
    if user_id in last_message_time and now - last_message_time[user_id] < RATE_LIMIT:
        await update.message.reply_text(
            f"⏱ Подожди {RATE_LIMIT} сек."
        )
        return
    last_message_time[user_id] = now

    key = str(user_id)

    # Имя
    if key in user_data and user_data[key]["name"] is None:
        user_data[key]["name"] = text
        save_user_data()
        await update.message.reply_text(f"Приятно познакомиться, {text}!")
        return

    prompt = (
        f"Пользователь {user_data[key]['name']} спрашивает: {text}"
        if key in user_data else text
    )

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        answer = response.text or "⚠️ Пустой ответ"
        await update.message.reply_text(answer)

    except Exception as e:
        logger.exception("Gemini error")
        await update.message.reply_text(
            f"❌ Gemini ошибка:\n{type(e).__name__}: {str(e)[:200]}"
        )

# ---------- Run ----------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CommandHandler("unblock", unblock_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ Бот запущен (polling)")
    app.run_polling()

if __name__ == "__main__":
    main()
