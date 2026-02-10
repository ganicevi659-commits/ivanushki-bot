import os
import json
import time
import logging
import re
from dotenv import load_dotenv
from telegram import Update, ChatPermissions
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
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x]

RATE_LIMIT = int(os.getenv("RATE_LIMIT",3))
MAX_WARNINGS = int(os.getenv("MAX_WARNINGS",3))

DATA_FILE = "users.json"
BLACKLIST_FILE = "blacklist.json"
LOG_FILE = "violations.log"

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY обязательны!")

# ---------- Загружаем память ----------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
else:
    users = {}

# ---------- Загружаем черный список ----------
if os.path.exists(BLACKLIST_FILE):
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        blacklist = json.load(f)
else:
    blacklist = []

# ---------- Хранение времени последнего сообщения ----------
last_msg_time = {}

# ---------- Gemini 2.5 Flash ----------
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"

# ---------- Сохраняем данные ----------
def save():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=4)

# ---------- Проверки ----------
def is_admin(uid):
    return uid in ADMIN_IDS

def is_blocked(uid):
    return uid in blacklist

# ---------- Логи нарушений ----------
def log_violation(user_id, reason, msg_text=""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.ctime()} | User {user_id} | {reason} | {msg_text}\n")

# ---------- AI-анализ токсичности ----------
def is_toxic(message: str) -> bool:
    # Простейший пример: содержит грубые слова
    toxic_words = ["дурак", "идиот", "лох", "тупой"]  # можно расширять
    return any(word.lower() in message.lower() for word in toxic_words)

# ---------- Анти-линки ----------
def contains_link(message: str) -> bool:
    url_pattern = r"(https?://|www\.)\S+"
    return bool(re.search(url_pattern, message))

# ---------- Команды ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return
    user_key = str(user_id)
    if user_key not in users:
        users[user_key] = {"name": None, "warns": 0}
        save()
        text = "Привет! Я бот на Gemini 2.5 Flash 🚀\nНапиши своё имя, и я тебя запомню!"
        image_url = "https://i.imgur.com/5cX9a9k.jpg"
        await context.bot.send_photo(chat_id=update.effective_chat.id,
                                     photo=image_url,
                                     caption=text)
    else:
        await update.message.reply_text("С возвращением! Пиши что угодно — я отвечу.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_blocked(update.effective_user.id):
        return
    text = (
        "💡 Список команд:\n"
        "/start - Запустить бота\n"
        "/help - Показать это сообщение\n"
        "/about - Информация о боте\n"
        "/warn - Предупреждение (только админ, ответом на сообщение)\n"
        "/ishak - Роль ИШАК 🐴 (ответом)\n"
        "/picinoz - Прикол 😎\n"
    )
    await update.message.reply_text(text)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_blocked(update.effective_user.id):
        return
    text = (
        "🤖 Бот на Gemini 2.5 Flash\n"
        "Память: имя пользователя, предупреждения\n"
        "Защита: rate-limit сообщений, черный список, анти-линки, токсичность\n"
"Fun: приколы /ishak, /picinoz"
    )
    await update.message.reply_text(text)

# ---------- Fun команды ----------
async def ishak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответь на сообщение пользователя для роли ИШАК 🐴")
        return
    await update.message.reply_text("🐴 Роль ИШАК присвоена!")

async def picinoz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🍕 Пичиноц активирован 😎")

# ---------- Админ предупреждения ----------
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответь на сообщение пользователя для предупреждения")
        return
    uid = update.message.reply_to_message.from_user.id
    key = str(uid)
    users.setdefault(key, {"name": None, "warns": 0})
    users[key]["warns"] += 1
    w = users[key]["warns"]
    save()
    log_violation(uid, f"warn {w}", update.message.reply_to_message.text)
    if w >= MAX_WARNINGS:
        blacklist.append(uid)
        save()
        log_violation(uid, "auto-ban", update.message.reply_to_message.text)
        await update.message.reply_text("🚫 Пользователь заблокирован за нарушения!")
    else:
        await update.message.reply_text(f"⚠️ Предупреждение {w}/{MAX_WARNINGS}")

# ---------- Обработка сообщений ----------
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_blocked(user_id):
        return

    now = time.time()
    if user_id in last_msg_time and now - last_msg_time[user_id] < RATE_LIMIT:
        await update.message.reply_text(f"⏱️ Подожди {RATE_LIMIT} секунд перед следующим сообщением")
        return
    last_msg_time[user_id] = now

    user_key = str(user_id)
    text = update.message.text.strip()

    # ---------- Проверка на токсичность ----------
    if is_toxic(text):
        log_violation(user_id, "toxic_message", text)
        users.setdefault(user_key, {"name": None, "warns": 0})
        users[user_key]["warns"] += 1
        save()
        await update.message.reply_text(f"⚠️ Сообщение считается токсичным! Предупреждение {users[user_key]['warns']}/{MAX_WARNINGS}")
        if users[user_key]["warns"] >= MAX_WARNINGS:
            blacklist.append(user_id)
            save()
            await update.message.reply_text("🚫 Пользователь заблокирован за токсичность!")
        return

    # ---------- Проверка на ссылки ----------
    if contains_link(text):
        log_violation(user_id, "link_detected", text)
        await update.message.delete()
        await update.message.reply_text("⚠️ Ссылки запрещены!")
        return

    # ---------- Сохраняем имя ----------
    if users[user_key]["name"] is None:
        users[user_key]["name"] = text
        save()
        await update.message.reply_text(f"Приятно познакомиться, {text}!")
        return

    # ---------- Отправка в Gemini ----------
    prompt = f"{users[user_key]['name']} спрашивает: {text}"
    logger.info(f"Запрос к Gemini: {prompt}")
    try:
        model = genai.GenerativeModel(MODEL)
        resp = model.generate_content(prompt)
        await update.message.reply_text(resp.text[:4000])
    except Exception as e:
        logger.exception("Gemini ошибка")
        await update.message.reply_text(f"❌ Gemini ошибка: {type(e).__name__}: {str(e)[:300]}")

# ---------- Основной запуск ----------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("ishak", ishak))
    app.add_handler(CommandHandler("picinoz", picinoz))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    logger.nfo("✅ Бот запущен в polling режиме")
    app.run_polling()

if __name__ == "__main__":
    main()
