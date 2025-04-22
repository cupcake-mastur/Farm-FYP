# bot_token = "7613014862:AAEPedcrFspIzJ28wvkPAecfxhmpntibiYw"

import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# States
SELECTING_DATA, ENTERING_VALUE, UPLOADING_IMAGE, CONFIRMING = range(4)

DATA_FIELDS = [
    "Body Weight",
    "Body Temperature",
    "Vaccination/Medication",
    "Infection Symptoms"
]

# In-memory user session data
user_session_data = {}

# DB Setup
def init_db():
    conn = sqlite3.connect("poultry_data.db")
    print(f"DB Path: {os.path.abspath('poultry_data.db')}")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS poultry_health (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        data_type TEXT,
        value TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_session_data:
        user_session_data[user_id] = {}  # only initialize if not present

    keyboard = [[InlineKeyboardButton(field, callback_data=field)] for field in DATA_FIELDS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 Select data to enter:", reply_markup=reply_markup)
    return SELECTING_DATA

# Handle field selection
async def select_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selection = query.data
    context.user_data["current_field"] = selection
    await query.edit_message_text(f"📝 Enter value for *{selection}*:", parse_mode="Markdown")
    return ENTERING_VALUE

# Handle text input for field
async def enter_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    field = context.user_data["current_field"]
    value = update.message.text.strip()

    # Field-specific validation
    if field == "Body Weight":
        try:
            weight = float(value)
            if not (0.03 <= weight <= 30):  # poultry weight range in kg
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid weight in kg (e.g., 1.5).")
            return ENTERING_VALUE

    elif field == "Body Temperature":
        try:
            temp = float(value)
            if not (30 <= temp <= 45):  # typical poultry body temp range
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid temperature in °C (e.g., 41.5).")
            return ENTERING_VALUE

    elif field == "Vaccination/Medication":
        if len(value) < 2:
            await update.message.reply_text("❌ Please enter more details (at least 2 characters).")
            return ENTERING_VALUE

    # Save to session
    if user_id not in user_session_data:
        user_session_data[user_id] = {}
    user_session_data[user_id][field] = {"value": value}

    if field == "Infection Symptoms":
        await update.message.reply_text("📷 You can now upload an image (optional) or type /skip if none.")
        return UPLOADING_IMAGE
    else:
        return await start(update, context)


# Handle image upload for Infection Symptoms
async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    field = "Infection Symptoms"

    if user_id not in user_session_data or field not in user_session_data[user_id]:
        await update.message.reply_text("❌ No field in progress to attach image.")
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_path = f"images/{user_id}_{file.file_id}.jpg"
    await file.download_to_drive(image_path)

    user_session_data[user_id][field]["image"] = image_path

    await show_confirmation(update, context)
    return CONFIRMING

# Skip uploading image
async def skip_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_confirmation(update, context)
    return CONFIRMING

# Show all collected data for confirmation
async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = user_session_data.get(user_id, {})
    
    await update.message.reply_text("📋 Here's the data you've entered:")

    for field, content in data.items():
        msg = f"📌 *{field}*\n📝 {content['value']}"
        if field == "Infection Symptoms" and "image" in content:
            # await update.message.reply_photo(photo=InputFile(content["image"]), caption=msg, parse_mode="Markdown")
            try:
                with open(content["image"], "rb") as img_file:
                    await update.message.reply_photo(photo=img_file, caption=msg, parse_mode="Markdown")
            except FileNotFoundError:
                await update.message.reply_text(f"{msg}\n⚠️ Image file not found.")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")

    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Save", callback_data="confirm_save")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_entry")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Do you want to save this data?", reply_markup=reply_markup)

# Handle confirmation
async def confirm_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("✅ confirm_save called")
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        session_data = user_session_data.get(user_id, {})
        print(f"Saving session_data for user {user_id}: {session_data}")    
        print(f"Session data items: {session_data.items()}")    
        conn = sqlite3.connect("poultry_data.db")
        c = conn.cursor()

        for field, content in session_data.items():
            if field == "Infection Symptoms":
                continue  # Don't save this field
            c.execute(
                "INSERT INTO poultry_health (user, data_type, value) VALUES (?, ?, ?)",
                (str(user_id), field, content["value"])
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ DB Write Error: {e}")

    await query.edit_message_text("✅ Data saved successfully (except 'Infection Symptoms').")
    user_session_data.pop(user_id, None)
    return ConversationHandler.END

# Cancel handler
async def cancel_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_session_data.pop(user_id, None)
    await query.edit_message_text("❌ Entry cancelled.")
    return ConversationHandler.END

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# Main
def main():
    init_db()
    os.makedirs("images", exist_ok=True)
    bot_token = "7685786328:AAEilDDS65J7-GB43i1LlaCJWJ3bx3i7nWs"
    app = Application.builder().token(bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_DATA: [CallbackQueryHandler(select_data)],
            ENTERING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_value)],
            UPLOADING_IMAGE: [
                MessageHandler(filters.PHOTO, upload_image),
                CommandHandler("skip", skip_image)
            ],
            CONFIRMING: [
                CallbackQueryHandler(confirm_save, pattern="confirm_save"),
                CallbackQueryHandler(cancel_entry, pattern="cancel_entry")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
