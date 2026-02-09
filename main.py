import os
from google import genai                          # ← правильный импорт для нового SDK
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("TELEGRAM_TOKEN и GEMINI_API_KEY обязательны!")

# Новый способ — создаём клиента (Client)
client = genai.Client(api_key=GEMINI_API_KEY)

# Модель (можно менять)
MODEL_NAME = "gemini-1.5-flash-latest"          # или gemini-2.0-flash / gemini-1.5-pro-latest

chats = {}  # user_id → chat session

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот на базе Google Gemini.\nПиши что угодно — отвечу 😄"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text:
        return

    if user_id not in chats:
        model = client.models.get_model(MODEL_NAME)     # ← получаем модель через client
        chats[user_id] = model.start_chat(history=[])   # ← чат тоже через модель

    chat = chats[user_id]

    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        # Отправка сообщения (асинхронно)
        response = await chat.send_message_async(text)
        answer = response.text

        await update.message.reply_text(answer)

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            await update.message.reply_text("Лимит Gemini — подожди 1–2 мин.")
        else:
            await update.message.reply_text(f"Ошибка: {error_msg[:400]}")

# /new для очистки чата
async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in chats:
        del chats[user_id]
    await update.message.reply_text("Чат очищен!")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", clear_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен (polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
