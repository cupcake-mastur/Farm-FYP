from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

# Define states
FARM_NAME, CROP_TYPE, FARM_SIZE = range(3)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the FarmBot! Let's start filling in your form.\nWhat's your Farm Name?")
    return FARM_NAME

# Step 1: Get Farm Name
async def get_farm_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['farm_name'] = update.message.text
    await update.message.reply_text("Great! What crop are you growing?")
    return CROP_TYPE

# Step 2: Get Crop Type
async def get_crop_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['crop_type'] = update.message.text
    await update.message.reply_text("Got it! How big is your farm (in acres)?")
    return FARM_SIZE

# Step 3: Get Farm Size and finish
async def get_farm_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['farm_size'] = update.message.text

    # Send summary
    summary = (
        f"Thanks! Here's what you've submitted:\n"
        f"🌾 Farm Name: {context.user_data['farm_name']}\n"
        f"🌱 Crop Type: {context.user_data['crop_type']}\n"
        f"📏 Farm Size: {context.user_data['farm_size']} acres"
    )
    await update.message.reply_text(summary)

    # Here, you'd call your backend API to validate & store the form
    return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Form cancelled. Type /start to begin again.")
    return ConversationHandler.END

# Main bot setup
def main():
    app = ApplicationBuilder().token("7020100788:AAHwAgmmocZHULAdthkhzI7vMxbks3G8NVs").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FARM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_farm_name)],
            CROP_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_crop_type)],
            FARM_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_farm_size)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
