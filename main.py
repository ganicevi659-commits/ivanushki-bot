import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- 1. Мини-сервер для Render ---
app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. Функция запроса к Gemini (Обход блокировок) ---
def ask_gemini_direct(text):
    api_key = os.getenv("GEMINI_API_KEY")
    # Используем стабильную версию v1 и прямой URL
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": text}]
        }],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"}
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        result = response.json()
        
        if 'error' in result:
            err_msg = result['error'].get('message', '')
            # Если всё равно ошибка региона, мы это увидим
            if "location" in err_msg.lower():
                return "Google всё еще блокирует этот IP. Попробуй создать НОВЫЙ ключ API в новом проекте Google AI Studio."
            return f"Ошибка Google: {err_msg}"
            
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Системная ошибка: {str(e)[:50]}"

# --- 3. Обработка сообщений Telegram ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    # Показываем статус "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Получаем ответ через прямой запрос
    answer = ask_gemini_direct(update.message.text)
    
    await update.message.reply_text(answer)

# --- 4. Запуск бота ---
if __name__ == '__main__':
    # Запуск Flask в фоне
    threading.Thread(target=run_flask, daemon=True).start()
    
    token = os.getenv("TELEGRAM_TOKEN")
    print("Бот запускается в режиме обхода (Direct HTTP)...")
    
    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Важно: удаляем старые вебхуки, если они были
    application.run_polling(drop_pending_updates=True)
