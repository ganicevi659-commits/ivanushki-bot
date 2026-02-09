mport os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Настройка Gemini
genai.configure(api_key="AIzaSyATxneFWXfIntvpcPf2zqtxoDBVQHPRmy4")
model = genai.GenerativeModel('gemini-1.5-flash')

# Функция обработки сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    try:
        # Генерируем ответ от ИИ
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при обращении к ИИ.")
        print(f"Ошибка: {e}")

# Запуск бота
if name == '__main__':
    print("Бот запущен...")
    application = Application.builder().token("8250295875:AAFAaOwraBoPYG9n-YUzKUUs0E8hYdVUltA").build()
    
    # Добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()
