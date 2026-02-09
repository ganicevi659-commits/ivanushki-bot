import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from google import genai

# --- Веб-сервер для Render ---
app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Настройка API ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
G_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация нового клиента Gemini
client = genai.Client(api_key=G_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        try:
            # Новый способ вызова модели
            response = client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=update.message.text
            )
            await update.message.reply_text(response.text)
        except Exception as e:
            print(f"Ошибка Gemini: {e}")
            await update.message.reply_text(f"Произошла ошибка: {str(e)[:100]}")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Запуск бота на новом SDK...")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
