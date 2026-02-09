import os, threading, requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

def ask_gemini(text):
    g_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={g_key}"
    payload = {"contents": [{"parts": [{"text": text}]}]}
    try:
        response = requests.post(url, json=payload)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "Ошибка ИИ. Проверь регион в Render (поставь Frankfurt)."

async def handle_message(update, context):
    if update.message.text:
        await update.message.reply_text(ask_gemini(update.message.text))

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    token = os.getenv("TELEGRAM_TOKEN")
    app_tg = Application.builder().token(token).build()
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_tg.run_polling()
