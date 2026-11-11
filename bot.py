
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.environ["BOT_TOKEN"]

BOOKS = {
    "bukhari": "Sahih al-Bukhari",
    "muslim": "Sahih Muslim",
    "abudawud": "Sunan Abu Dawud",
    "tirmidhi": "Jami at-Tirmidhi",
    "nasai": "Sunan an-Nasa'i",
    "ibnmajah": "Sunan Ibn Majah",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=key)]
        for key, name in BOOKS.items()
    ]
    await update.message.reply_text(
        "Welcome to Hadith Collection Bot!\nSelect a Hadith book:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["book"] = query.data
    await query.edit_message_text(
        f"{BOOKS[query.data]} selected.\nSend Hadith number:"
    )

async def number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    book = context.user_data.get("book")
    n = update.message.text.strip()

    if not book:
        await update.message.reply_text("First use /start")
        return

    if not n.isdigit():
        await update.message.reply_text("Send a valid Hadith number.")
        return

    await update.message.reply_text("Searching...")

    try:
        url = f"https://ummahapi.com/api/hadith/{book}/{n}"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        result = r.json()
        data = result.get("data")

        if not isinstance(data, dict):
            await update.message.reply_text("Hadith not found.")
            return

        arabic = data.get("hadith_arabic") or data.get("arabic") or "Not available"
        english = data.get("hadith_english") or data.get("english") or "Not available"

        text = (
            f"📚 {BOOKS[book]}\nHadith No: {n}\n\n"
            f"العربية\n{arabic}\n\n"
            f"ENGLISH\n{english}"
        )

        await update.message.reply_text(text[:4000])

    except requests.RequestException:
        await update.message.reply_text("Database error. Try again later.")
    except (ValueError, TypeError):
        await update.message.reply_text("Could not read the database response.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Use /start to select a book and search by Hadith number."
    )

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CallbackQueryHandler(choose))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, number))

app.run_polling()
