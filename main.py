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

# Логи — чтобы видеть, что происходит в Render
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "мой_секрет_123")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY обязательны!")

# Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash-latest"

app = FastAPI()

# Telegram приложение
application = Application.builder().token(TELEGRAM_TOKEN).build()

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

        # Самый стабильный способ сейчас (без start_chat)
        model = client.get_generative_model(MODEL_NAME)
        response = await model.generate_content_async(text)
        answer = response.text.strip()

        logger.info("Gemini ответил успешно")
        await update.message.reply_text(answer)

    except Exception as e:
        logger.error(f"Gemini ошибка: {str(e)}", exc_info=True)
        await update.message.reply_text(f"Ошибка: {str(e)[:250]}\nПопробуй позже или /start")

# Хендлеры
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("new", clear_chat))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook
@app.post("/webhook")
async def webhook(request: Request):
    logger.info("Запрос на /webhook от Telegram")

    if WEBHOOK_SECRET:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != WEBHOOK_SECRET:
            logger.error(f"Неверный secret: {secret}")
            raise HTTPException(status_code=403, detail="Неверный секрет")

    try:
        json_data = await request.json()
        logger.info("JSON получен")
        update = Update.de_json(json_data, application.bot)
        if update:
            await application.process_update(update)
    except Exception as e:
        logger.error(f"Ошибка обработки update: {e}")

    return {"ok": True}

# Для проверки, что сервер жив
@app.get("/")
async def root():
    return {"status": "alive", "message": "Бот на webhook работает"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Запуск на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
