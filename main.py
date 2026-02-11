import os
import logging
from io import BytesIO
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

from google import genai

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from moviepy.editor import VideoFileClip

# PDF
import PyPDF2
from fpdf import FPDF

# Audio
import speech_recognition as sr
from gtts import gTTS

# ----------------- SETUP -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("Нет TELEGRAM_TOKEN или GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"

os.makedirs("temp", exist_ok=True)

# ----------------- UTILS -----------------
def private_only(update: Update) -> bool:
    return update.effective_chat.type == "private"

# ----------------- COMMANDS -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update):
        return
    await update.message.reply_text(
        "Привет 👋\n"
        "Я AI-помощник.\n"
        "Могу работать с текстом, фото, видео, PDF и аудио."
    )

# ----------------- TEXT / AI -----------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update):
        return

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    response = client.models.generate_content(
        model=MODEL,
        contents=update.message.text
    )

    await update.message.reply_text(response.text or "Пустой ответ")

# ----------------- PHOTO -----------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update):
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    path = "temp/photo.jpg"
    await file.download_to_drive(path)

    img = Image.open(path).convert("RGB")
    img = img.resize((img.width // 2, img.height // 2))
    img = img.convert("L")  # Ч/Б

    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "AI BOT", fill=255)

    out = "temp/photo_out.jpg"
    img.save(out)

    await update.message.reply_photo(open(out, "rb"))

# ----------------- VIDEO -----------------
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update):
        return

    file = await update.message.video.get_file()
    path = "temp/video.mp4"
    await file.download_to_drive(path)

    clip = VideoFileClip(path).subclip(0, min(5, VideoFileClip(path).duration))
    gif_path = "temp/video.gif"
    clip.write_gif(gif_path)

    await update.message.reply_animation(open(gif_path, "rb"))

# ----------------- PDF -----------------
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update):
        return

    file = await update.message.document.get_file()
    path = "temp/file.pdf"
    await file.download_to_drive(path)

    # Чтение текста
    text = ""
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"

    if not text.strip():
        text = "❌ Нечего прочитать из PDF"

    await update.message.reply_text(text[:4000])  # ограничение Telegram

async def create_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update):
        return

    text = update.message.text
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)

    path = "temp/out.pdf"
    pdf.output(path)

    await update.message.reply_document(open(path, "rb"))

# ----------------- AUDIO -----------------
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update):
        return

    file = await update.message.voice.get_file() if update.message.voice else await update.message.audio.get_file()
    path = "temp/audio.ogg"
    await file.download_to_drive(path)

    # Конвертация через ffmpeg/основной путь в wav (moviepy можно добавить)
    wav_path = "temp/audio.wav"
    os.system(f"ffmpeg -y -i {path} {wav_path}")

    r = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = r.record(source)
        try:
            text = r.recognize_google(audio_data, language="ru-RU")
        except:
            text = "❌ Не удалось распознать аудио"

    await update.message.reply_text(f"📝 Распознано: {text}")

async def audio_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not private_only(update):
        return

    text = update.message.text
    tts = gTTS(text=text, lang="ru")
    path = "temp/tts.mp3"
    tts.save(path)

    await update.message.reply_audio(open(path, "rb"))

# ----------------- MAIN -----------------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^pdf "), create_pdf))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^tts "), audio_tts))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
