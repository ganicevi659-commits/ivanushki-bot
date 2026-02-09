import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai

app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Настройка ключей
TOKEN = os.getenv("TELEGRAM_TOKEN")
G_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=G_KEY)
# Используем модель flash и создаем чат с памятью
model = genai.GenerativeModel('gemini-1.5-flash')
chat = model.start_chat(history=[])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        try:
            # Отправляем сообщение в чат
            response = chat.send_message(update.message.text)
            await update.message.reply_text(response.text)
        except Exception as e:
            # Печатаем РЕАЛЬНУЮ ошибку в логи Render
            print(f"!!! ОШИБКА GEMINI: {e}")
            await update.message.reply_text(f"Ошибка: {str(e)[:50]}...")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот перезапущен и готов к тестам!")
    application.run_polling()
