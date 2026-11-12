
import os
import asyncio
import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------------- CONFIG ----------------

TOKEN = os.getenv("BOT_TOKEN")

HADITH_API = "https://ummahapi.com/api/hadith"

FAWAZ_API = (
    "https://cdn.jsdelivr.net/gh/fawazahmed0/"
    "hadith-api@1/editions"
)

QURAN_API = "https://api.alquran.cloud/v1"

ROMAN_HINDI_BASE = (
    "https://cdn.jsdelivr.net/gh/fawazahmed0/"
    "quran-api@1/editions/hin-maulanaazizulha-la"
)

BOOKS = {
    "bukhari": "Sahih al-Bukhari",
    "muslim": "Sahih Muslim",
    "abudawud": "Sunan Abu Dawud",
    "tirmidhi": "Jami at-Tirmidhi",
    "nasai": "Sunan an-Nasa'i",
    "ibnmajah": "Sunan Ibn Majah",
}


# ---------------- API HELPERS ----------------

def get_json(url):
    response = requests.get(url, timeout=25)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Invalid API response")

    return data


async def fetch_json(url):
    return await asyncio.to_thread(get_json, url)


def get_hadith_text(data, language):
    """Read Hadith fields from different API response formats."""

    if isinstance(data.get("data"), dict):
        data = data["data"]

    if language == "arabic":
        return (
            data.get("arabic")
            or data.get("hadith_arabic")
            or data.get("text_arabic")
            or ""
        )

    return (
        data.get("english")
        or data.get("hadith_english")
        or data.get("text")
        or ""
    )


def get_muslim_hadith(number):
    """
    Fawaz dataset: source records 1-92 are introductory.
    User-facing Hadith 1 was tested against source record 93.
    """

    source_number = number + 92

    arabic_url = f"{FAWAZ_API}/ara-muslim/{source_number}.json"
    english_url = f"{FAWAZ_API}/eng-muslim/{source_number}.json"

    arabic_data = get_json(arabic_url)
    english_data = get_json(english_url)

    arabic_records = arabic_data.get("hadiths", [])
    english_records = english_data.get("hadiths", [])

    if not arabic_records or not english_records:
        raise ValueError("Hadith not found")

    arabic_record = arabic_records[0]
    english_record = english_records[0]

    if int(arabic_record.get("hadithnumber", -1)) != source_number:
        raise ValueError("Arabic Hadith number mismatch")

    if int(english_record.get("hadithnumber", -1)) != source_number:
        raise ValueError("English Hadith number mismatch")

    arabic = arabic_record.get("text", "")
    english = english_record.get("text", "")

    if not arabic or not english:
        raise ValueError("Hadith translation unavailable")

    return arabic, english


# ---------------- MESSAGE HELPER ----------------

async def send_long_message(message, text):
    """Split long messages to fit Telegram message limits."""

    limit = 3500

    while text:
        if len(text) <= limit:
            await message.reply_text(text)
            break

        split_at = text.rfind("\n", 0, limit)

        if split_at == -1:
            split_at = limit

        chunk = text[:split_at]
        text = text[split_at:].lstrip()

        await message.reply_text(chunk)


# ---------------- START / HELP ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Assalamu Alaikum!\n\n"
        "Welcome to Hadith & Quran Bot.\n\n"
        "📚 Hadith Commands:\n"
        "/books - View all Hadith collections\n"
        "/hadith 9 - Get Hadith from selected collection\n"
        "/hadith bukhari 9 - Get a specific Hadith\n"
        "/hadith muslim 1 - Get Muslim Hadith\n\n"
        "📖 Quran Commands:\n"
        "/quran 2 255 - Get a specific Ayah\n"
        "/surah 1 - Get a complete Surah\n\n"
        "Languages: Arabic, English and Roman Hindi."
    )

    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ---------------- HADITH BOOKS ----------------

async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []

    for key, name in BOOKS.items():
        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"book_{key}"
            )
        ])

    await update.message.reply_text(
        "📚 Select a Hadith collection:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def choose_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    book = query.data.replace("book_", "")

    if book not in BOOKS:
        await query.edit_message_text("Invalid collection.")
        return

    context.user_data["selected_book"] = book

    await query.edit_message_text(
        f"Selected: {BOOKS[book]}\n\n"
        "Now use:\n"
        "/hadith 1"
    )


# ---------------- HADITH COMMAND ----------------

async def hadith_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage:\n"
            "/hadith 9\n"
            "/hadith bukhari 9\n"
            "/hadith muslim 1"
        )
        return

    if len(args) >= 2 and args[0].lower() in BOOKS:
        book = args[0].lower()
        number_text = args[1]
    else:
        book = context.user_data.get("selected_book", "bukhari")
        number_text = args[0]

    try:
        number = int(number_text)

        if number < 1:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "Please enter a valid Hadith number."
        )
        return

    if book not in BOOKS:
        await update.message.reply_text("Invalid Hadith collection.")
        return

    try:
        if book == "muslim":
            arabic, english = await asyncio.to_thread(
                get_muslim_hadith,
                number
            )

        else:
            data = await fetch_json(
                f"{HADITH_API}/{book}/{number}"
            )

            arabic = get_hadith_text(data, "arabic")
            english = get_hadith_text(data, "english")

            if not arabic or not english:
                raise ValueError("Hadith not found")

        text = (
            f"📚 {BOOKS[book]}\n"
            f"Hadith No: {number}\n\n"
            f"العربية:\n{arabic}\n\n"
            f"English:\n{english}"
        )

        await send_long_message(update.message, text)

    except (requests.RequestException, ValueError, TypeError,
            KeyError, IndexError, OverflowError) as error:

        print("Hadith error:", error)

        await update.message.reply_text(
            "Hadith not found or API is temporarily unavailable."
        )


# ---------------- QURAN HELPERS ----------------

async def get_quran_ayah(surah, ayah, edition):
    url = f"{QURAN_API}/ayah/{surah}:{ayah}/{edition}"
    return await fetch_json(url)


async def get_roman_ayah(surah, ayah):
    url = f"{ROMAN_HINDI_BASE}/{surah}/{ayah}.json"
    return await fetch_json(url)


async def get_roman_surah(surah):
    url = f"{ROMAN_HINDI_BASE}/{surah}.json"
    return await fetch_json(url)


# ---------------- QURAN AYAH COMMAND ----------------

async def quran_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage:\n/quran 2 255"
        )
        return

    try:
        surah = int(context.args[0])
        ayah = int(context.args[1])

        if not 1 <= surah <= 114 or ayah < 1:
            raise ValueError

        arabic_data, english_data, roman_data = await asyncio.gather(
            get_quran_ayah(surah, ayah, "quran-uthmani"),
            get_quran_ayah(surah, ayah, "en.sahih"),
            get_roman_ayah(surah, ayah)
        )

        arabic = arabic_data["data"]["text"]
        english = english_data["data"]["text"]

        if (
            roman_data["chapter"] != surah
            or roman_data["verse"] != ayah
        ):
            raise ValueError("Roman Hindi Ayah mismatch")

        roman = roman_data["text"]

        text = (
            f"📖 Quran - Surah {surah}, Ayah {ayah}\n\n"
            f"العربية:\n{arabic}\n\n"
            f"English:\n{english}\n\n"
            f"Hindi (Roman):\n{roman}"
        )

        await send_long_message(update.message, text)

    except (requests.RequestException, ValueError, KeyError,
            TypeError, IndexError) as error:

        print("Quran error:", error)

        await update.message.reply_text(
            "Ayah not found or Quran API is temporarily unavailable."
        )


# ---------------- COMPLETE SURAH COMMAND ----------------

async def surah_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage:\n/surah 1"
        )
        return

    try:
        surah = int(context.args[0])

        if not 1 <= surah <= 114:
            raise ValueError

        arabic_data, english_data, roman_data = await asyncio.gather(
            fetch_json(
                f"{QURAN_API}/surah/{surah}/quran-uthmani"
            ),
            fetch_json(
                f"{QURAN_API}/surah/{surah}/en.sahih"
            ),
            get_roman_surah(surah)
        )

        arabic_ayahs = arabic_data["data"]["ayahs"]
        english_ayahs = english_data["data"]["ayahs"]
        roman_ayahs = roman_data["chapter"]

        if not isinstance(roman_ayahs, list):
            raise ValueError("Invalid Roman Hindi Surah response")

        if not (
            len(arabic_ayahs)
            == len(english_ayahs)
            == len(roman_ayahs)
        ):
            raise ValueError("Ayah count mismatch")

        surah_name = arabic_data["data"]["name"]

        text = f"📖 {surah_name}\nSurah {surah}\n\n"

        for a, e, r in zip(
            arabic_ayahs,
            english_ayahs,
            roman_ayahs
        ):
            ayah_number = a["numberInSurah"]

            if (
                ayah_number != e["numberInSurah"]
                or ayah_number != r["verse"]
                or r["chapter"] != surah
            ):
                raise ValueError("Ayah number mismatch")

            text += (
                f"━━━━━━━━━━━━━━\n"
                f"Ayah {ayah_number}\n\n"
                f"{a['text']}\n\n"
                f"English:\n{e['text']}\n\n"
                f"Hindi (Roman):\n{r['text']}\n\n"
            )

        await send_long_message(update.message, text)

    except (requests.RequestException, ValueError, KeyError,
            TypeError, IndexError) as error:

        print("Surah error:", error)

        await update.message.reply_text(
            "Surah could not be loaded. Please try again."
        )


# ---------------- MAIN ----------------

def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(CommandHandler("books", books_command))
    app.add_handler(CallbackQueryHandler(choose_book))

    app.add_handler(CommandHandler("hadith", hadith_command))

    app.add_handler(CommandHandler("quran", quran_command))
    app.add_handler(CommandHandler("surah", surah_command))

    print("Hadith & Quran Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
