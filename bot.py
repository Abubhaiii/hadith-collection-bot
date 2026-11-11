
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

TOKEN = os.environ["BOT_TOKEN"]
API = "https://ummahapi.com/api/hadith"

BOOKS = {
    "bukhari": "Sahih al-Bukhari",
    "muslim": "Sahih Muslim",
    "abudawud": "Sunan Abu Dawud",
    "tirmidhi": "Jami at-Tirmidhi",
    "nasai": "Sunan an-Nasa'i",
    "ibnmajah": "Sunan Ibn Majah",
}

def book_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=f"book:{key}")]
        for key, name in BOOKS.items()
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["book"] = context.user_data.get("book", "bukhari")
    await update.message.reply_text(
        "Assalamu Alaikum!\n\n"
        "Welcome to Hadith Collection Bot 📚\n"
        "Read Hadith in Arabic and English from six collections.\n\n"
        "Choose a collection below, or use /hadith bukhari 9",
        reply_markup=book_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 HADITH COLLECTION BOT — HELP\n\n"
        "How to use:\n\n"
        "1. /start — Start the bot and choose a collection.\n"
        "2. /hadith 9 — Get Hadith 9 from your selected collection.\n"
        "3. /hadith bukhari 9 — Get Bukhari Hadith 9.\n"
        "4. /hadith muslim 9 — Get Muslim Hadith 9.\n"
        "5. /books — Show all six collections.\n"
        "6. /help — Show this help message.\n\n"
        "Available collection codes:\n"
        "bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah\n\n"
        "Group example:\n"
        "/hadith bukhari 9\n\n"
        "The bot provides Arabic and English text when available."
    )

async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📚 Available Hadith Collections:\n"]
    for key, name in BOOKS.items():
        lines.append(f"• {name} — {key}")
    await update.message.reply_text("\n".join(lines), reply_markup=book_keyboard())

async def choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":", 1)[1]
    context.user_data["book"] = key
    await query.edit_message_text(
        f"Selected: {BOOKS[key]}\n\n"
        f"Now send /hadith 9 to get Hadith number 9."
    )

async def hadith_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if len(args) == 1:
        book = context.user_data.get("book", "bukhari")
        number = args[0]
    elif len(args) == 2:
        book = args[0].lower()
        number = args[1]
    else:
        await update.message.reply_text(
            "Usage:\n/hadith 9\n/hadith bukhari 9\n\n"
            "Use /help for instructions."
        )
        return

    if book not in BOOKS:
        await update.message.reply_text(
            "Unknown collection. Use /books to see available collections."
        )
        return

    if not number.replace(".", "", 1).isdigit():
        await update.message.reply_text("Please enter a valid Hadith number.")
        return

    await update.message.reply_text("Searching Hadith...")

    try:
        response = requests.get(
            f"{API}/{book}/{number}",
            timeout=20
        )
        if response.status_code == 404:
            await update.message.reply_text("Hadith not found.")
            return

        response.raise_for_status()
        result = response.json()
        data = result.get("data", {})

        if not isinstance(data, dict) or not data:
            await update.message.reply_text("Hadith not found.")
            return

        arabic = data.get("hadith_arabic")
        english = data.get("hadith_english")

        if not arabic and not english:
            await update.message.reply_text(
                "Text is not available for this Hadith."
            )
            return

        message = (
            f"📚 {BOOKS[book]}\n"
            f"Hadith No: {number}\n\n"
            f"العربية\n{arabic or 'Not available'}\n\n"
            f"ENGLISH\n{english or 'Not available'}"
        )

        for i in range(0, len(message), 4000):
            await update.message.reply_text(message[i:i + 4000])

    except requests.RequestException:
        await update.message.reply_text(
            "Database connection error. Please try again later."
        )
    except (ValueError, TypeError):
        await update.message.reply_text(
            "Could not read the Hadith data. Please try again."
        )

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("books", books_command))
app.add_handler(CommandHandler("hadith", hadith_command))
app.add_handler(CallbackQueryHandler(choose_book, pattern="^book:"))

app.run_polling()
                              
