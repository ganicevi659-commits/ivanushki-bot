import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# --- 1. Мини-сервер для Render (чтобы не было ошибки Port Binding) ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Бот работает!", 200

def run_flask():
    # Render сам назначит порт, мы его просто берем
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. Настройка Gemini и Telegram ---
# Берем ключи, которые ты ввел в Dashboard Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если пришло текстовое сообщение
    if update.message and update.message.text:
        try:
            # Отправляем текст в Gemini
            response = model.generate_content(update.message.text)
            # Отправляем ответ пользователю в ТГ
            await update.message.reply_text(response.text)
        except Exception as e:
            print(f"Ошибка Gemini: {e}")
            await update.message.reply_text("Извини, ИИ задумался. Попробуй еще раз позже.")

# --- 3. Запуск всего вместе ---
if __name__ == '__main__':
    # Запускаем Flask в фоновом режиме
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Запускаю бота...")
    
    # Создаем приложение Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Начинаем слушать сообщения
    application.run_polling()
