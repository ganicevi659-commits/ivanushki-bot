import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from google import genai

# Настройка логирования (чтобы видеть ошибки в Render)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения (добавь в Render → Environment)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "мой_секрет_123")  # опционально, для защиты

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY обязательны!")

# Gemini клиент
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash-latest"  # или gemini-1.5-flash-002 / gemini-2.0-flash

chats = {}  # user_id → chat

app = FastAPI()

# Инициализация Application один раз
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Обработчики (как раньше)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Пиши что угодно — отвечу с Gemini 🚀")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in chats:
        del chats[user_id]
    await update.message.reply_text("Чат очищен! /start")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text:
        return

    if user_id not in chats:
        model = client.models.get_model(MODEL_NAME)
        chats[user_id] = model.start_chat(history=[])

    chat = chats[user_id]

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        response = await chat.send_message_async(text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Gemini ошибка: {e}")
        await update.message.reply_text("Что-то сломалось... Попробуй позже 😅")

# Регистрируем обработчики
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("new", clear_chat))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint (Telegram будет слать POST сюда)
@app.post("/webhook")
async def webhook(request: Request):
    if WEBHOOK_SECRET:
        auth_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if auth_header != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Неверный секрет")

    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    if update:
        await application.process_update(update)
    return {"ok": True}

# Запуск сервера (uvicorn сам подхватит)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
