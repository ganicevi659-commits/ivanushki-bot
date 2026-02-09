import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai

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

# Настраиваем Gemini
genai.configure(api_key=G_KEY)

# Пробуем использовать модель 1.5-flash
model = genai.GenerativeModel('gemini-1.5-flash')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        try:
            # Генерация контента
            response = model.generate_content(update.message.text)
            
            # Проверка, есть ли текст в ответе
            if response.text:
                await update.message.reply_text(response.text)
            else:
                await update.message.reply_text("ИИ прислал пустой ответ.")
                
        except Exception as e:
            error_msg = str(e)
            print(f"!!! ОШИБКА: {error_msg}")
            
            # Если это проблема с регионом (РФ), мы это увидим
            if "User location is not supported" in error_msg:
                await update.message.reply_text("Ошибка: Google блокирует запросы из этого региона.")
            else:
                await update.message.reply_text(f"Произошла ошибка: {error_msg[:100]}")

if __name__ == '__main__':
    # Запуск "заплатки" для порта
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Бот запускается...")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
