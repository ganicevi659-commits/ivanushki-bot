import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- 1. Мини-сервер для поддержания жизни на Render ---
app = Flask(__name__)

@app.route('/')
def health():
    return "Бот онлайн и готов к работе!", 200

def run_flask():
    # Порт для Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. Функция запроса к Gemini API ---
def ask_gemini(text):
    g_key = os.getenv("GEMINI_API_KEY")
    # Используем стабильный эндпоинт v1
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={g_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": text}]
        }],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        result = response.json()
        
        # Если Google вернул ошибку, выводим её текст
        if 'error' in result:
            msg = result['error'].get('message', 'Неизвестная ошибка')
            print(f"Ошибка Google: {msg}")
            return f"Google API Error: {msg}"
            
        # Если всё Ок, возвращаем текст
        return result['candidates'][0]['content']['parts'][0]['text']
        
    except Exception as e:
        print(f"Системная ошибка: {e}")
        return f"Системная ошибка при запросе к ИИ: {str(e)[:50]}"

# --- 3. Обработка сообщений в Telegram ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    # Индикация "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Получаем ответ от функции
    answer = ask_gemini(update.message.text)
    
    # Отправляем пользователю
    await update.message.reply_text(answer)

# --- 4. Запуск ---
if __name__ == '__main__':
    t_token = os.getenv("TELEGRAM_TOKEN")
    
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Запуск бота Иванушка (Direct HTTP Mode)...")
    
    # Настройка Telegram бота
    application = Application.builder().token(t_token).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    application.run_polling()
