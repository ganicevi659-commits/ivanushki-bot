import os
import logging
from contextlib import asynccontextmanager
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

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")  # должен быть без пробелов, кириллицы и т.д.

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY обязательны!")

if not WEBHOOK_SECRET:
    logger.warning("WEBHOOK_SECRET не задан → секрет проверяться не будет")

# Gemini (новый правильный способ в google-genai)
MODEL_NAME = "gemini-1.5-flash-latest"  # или gemini-1.5-flash-002 / gemini-2.0-flash

# Telegram приложение
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Пиши что угодно — отвечу с Gemini 🚀")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Чат очищен! Просто пиши дальше.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text:
        return

    logger.info(f"Получено сообщение: {text}")

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        # Правильное создание модели в новом SDK
        model = genai.GenerativeModel(MODEL_NAME)
        response = await model.generate_content_async(text)
        answer = response.text.strip()

        logger.info("Gemini ответил успешно")
        await update.message.reply_text(answer)

    except Exception as e:
        logger.error(f"Gemini ошибка: {str(e)}", exc_info=True)
        await update.message.reply_text(f"Ошибка: {str(e)[:250]}\nПопробуй позже")

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("new", clear_chat))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Lifespan — правильная инициализация и установка webhook
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await application.initialize()
    await application.start()

    webhook_url = "https://ivanushki-bot.onrender.com/webhook"
    try:
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True
        )
        logger.info(f"Webhook успешно установлен: {webhook_url}")
    except Exception as e:
        logger.error(f"Ошибка установки webhook: {e}")

    yield

    # Shutdown
    await application.stop()
    await application.shutdown()

# FastAPI с lifespan
app = FastAPI(lifespan=lifespan)

# Webhook
@app.post("/webhook")
async def webhook(request: Request):
    logger.info("Получен запрос на /webhook от Telegram")

    if WEBHOOK_SECRET:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != WEBHOOK_SECRET:
            logger.error(f"Неверный secret token: {secret}")
            raise HTTPException(status_code=403, detail="Неверный секрет")

    try:
        json_data = await request.json()
        logger.info("JSON успешно получен")
        update = Update.de_json(json_data, application.bot)
        if update:
            await application.process_update(update)
    except Exception as e:
        logger.error(f"Ошибка обработки обновления: {e}")

    return {"ok": True}

# Health-check
@app.get("/")
async def root():
    return {"status": "alive", "message": "Бот на webhook работает"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Запуск сервера на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port
