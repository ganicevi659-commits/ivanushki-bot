import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- 1. Мини-сервер для Render ---
app = Flask(__name__)

@app.route('/')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. Функция запроса к Gemini ---
def ask_gemini(text):
    api_key = os.getenv("GEMINI_API_KEY")
    # Используем стабильную ссылку v1
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": text}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        data = response.json()
        
        if "error" in data:
            return f"Ошибка Google: {data['error'].get('message')}"
            
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Ошибка соединения: {str(e)[:50]}"

# --- 3. Обработка Telegram ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        # Статус "печатает"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Получаем ответ
        answer = ask_gemini(update.message.text)
        
        # Отправляем обратно
        await update.message.reply_text(answer)

# --- 4. Старт бота ---
if __name__ == '__main__':
    # Запускаем веб-сервер в фоне
    threading.Thread(target=run_flask, daemon=True).start()
    
    token = os.getenv("TELEGRAM_TOKEN")
    print("Бот запускается...")
    
    # Запуск ТГ
    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
