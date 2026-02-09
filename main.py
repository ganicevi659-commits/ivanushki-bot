import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- Мини-сервер для Render ---
app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Настройка ключей ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
G_KEY = os.getenv("GEMINI_API_KEY")

def ask_gemini(text):
    # Прямой URL к стабильной версии API Gemini 1.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={G_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": text}]
        }]
    }
    
    response = requests.post(url, json=payload)
    result = response.json()
    
    # Вытаскиваем текст из сложного JSON ответа Google
    try:
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Ошибка парсинга: {result}")
        return f"Ошибка ИИ: {result.get('error', {}).get('message', 'Неизвестная ошибка')}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        user_text = update.message.text
        # Отправляем статус "печатает", чтобы пользователь видел активность
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        answer = ask_gemini(user_text)
        await update.message.reply_text(answer)

if __name__ == '__main__':
    # Запуск фласка
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Бот запущен через Direct API Mode...")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
