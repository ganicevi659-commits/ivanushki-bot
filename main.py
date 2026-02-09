import os
import asyncio
from google import genai
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Переменные из окружения (Render → Environment)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY обязательны!")

# Настройка Gemini (новый SDK)
genai.configure(api_key=GEMINI_API_KEY)

# Используем самую стабильную и быструю модель на февраль 2026
MODEL_NAME = "gemini-1.5-flash-002"   # или "gemini-2.0-flash" / "gemini-1.5-flash-latest"

chats = {}  # user_id → chat session

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот на базе Google Gemini.\nПросто пиши — отвечу максимально быстро 😄"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text:
        return

    if user_id not in chats:
        model = genai.GenerativeModel(MODEL_NAME)
        chats[user_id] = model.start_chat(history=[])

    chat = chats[user_id]

    try:
        # Показываем, что бот "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        # Отправляем сообщение в Gemini (асинхронно)
        response = await chat.send_message_async(text)
        answer = response.text

        await update.message.reply_text(answer, parse_mode=None)  # без лишнего форматирования

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            await update.message.reply_text("Лимит запросов к Gemini. Подожди 1–2 минуты и попробуй снова.")
        else:
            await update.message.reply_text(f"Ошибка:\n{error_msg[:400]}")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in chats:
        del chats[user_id]
    await update.message.reply_text("Чат очищен. Можно начинать новый разговор!")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", clear_chat))       # /new — очистить историю
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен (polling mode)")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
