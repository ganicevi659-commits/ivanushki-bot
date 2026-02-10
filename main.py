import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai

# ---------- Логирование ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Переменные окружения ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY обязательны!")

MODEL_NAME = "gemini-1.5-flash-latest"
client = genai.Client(api_key=GEMINI_API_KEY)

# ---------- Обработчики ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я жив 👋 Пиши что угодно.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return

    logger.info(f"Получено сообщение: {text}")

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        # ---------- Вызов Gemini через asyncio.to_thread ----------
        response = await asyncio.to_thread(
            client.models.generate_content,
            MODEL_NAME,
            text
        )
        answer = response.text.strip()

        logger.info("Gemini ответил успешно")
        await update.message.reply_text(answer)

    except Exception as e:
        # Показываем реальную ошибку
        logger.exception("Gemini реальная ошибка")
        await update.message.reply_text(
            f"❌ Gemini ошибка:\n{type(e).__name__}: {str(e)[:300]}"
        )

# ---------- Основная функция ----------
async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен в polling режиме")
    await application.run_polling()

# ---------- Запуск ----------
if __name__ == "__main__":
    asyncio.run(main())
