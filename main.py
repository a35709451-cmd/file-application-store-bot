import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import BOT_TOKEN, logger
from database import db
from handlers.admin import handle_admin_callbacks, handle_admin_text, admin_panel
from handlers.files import handle_file_upload, handle_file_callbacks
from handlers.quiz import handle_quiz_callbacks, handle_quiz_text, quiz_menu
from handlers.ai import handle_ai_chat

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in db.users:
        db.users[user_id] = {"points": 0, "banned": False}
        await db.save_all()
        
    # Check if starting with file ID (e.g. t.me/bot?start=file_123)
    args = context.args
    if args and args[0].startswith("file_"):
        file_id = args[0].replace("file_", "")
        if file_id in db.files:
            file = db.files[file_id]
            points_req = file.get("points_required", 0)
            user_points = db.users[user_id].get("points", 0)
            if user_points < points_req:
                await update.message.reply_text(f"❌ You need {points_req} points to download this. You have {user_points}.")
                return
            
            # Send file logic (Simplified)
            try:
                if file['type'] == 'document':
                    await update.message.reply_document(file['file_id'])
                elif file['type'] == 'photo':
                    await update.message.reply_photo(file['file_id'])
                # Deduct points
                if points_req > 0:
                    db.users[user_id]["points"] -= points_req
                    await db.save_all()
            except Exception as e:
                logger.error(e)
            return

    keyboard = [
        [InlineKeyboardButton("📚 My Files", callback_data="my_files")],
        [InlineKeyboardButton("🧠 Quiz Hub", callback_data="quiz_menu")],
        [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")]
    ]
    
    await update.message.reply_text(
        "🎓 *Welcome to Student Hub Bot!*\n\n"
        "• Send ANY file/media to upload.\n"
        "• Use `/ai [question]` to ask the AI assistant.\n"
        "• Play quizzes to earn points!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def main_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    
    if action == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📚 My Files", callback_data="my_files")],
            [InlineKeyboardButton("🧠 Quiz Hub", callback_data="quiz_menu")],
            [InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")]
        ]
        await query.edit_message_text("🎓 *Student Hub Main Menu*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif action == "admin_panel":
        await admin_panel(update, context)
    elif action.startswith("admin_"):
        await handle_admin_callbacks(update, context)
    elif action.startswith("approve_") or action.startswith("reject_") or action.startswith("my_files") or action.startswith("edit_") or action.startswith("togglepub_") or action.startswith("setprice_"):
        await handle_file_callbacks(update, context)
    elif action.startswith("quiz_") or action.startswith("qcreate_") or action.startswith("playq_"):
        await handle_quiz_callbacks(update, context)

async def handle_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.startswith("/ai"):
        await handle_ai_chat(update, context)
        return
        
    # Check if awaiting admin input
    if context.user_data.get('awaiting_ban_id') or context.user_data.get('awaiting_broadcast'):
        await handle_admin_text(update, context)
        return
        
    # Check if awaiting quiz input
    if context.user_data.get('awaiting_quiz_title'):
        await handle_quiz_text(update, context)
        return
        
    # Check if setting price
    if context.user_data.get('setting_price_for'):
        file_id = context.user_data['setting_price_for']
        try:
            price = int(update.message.text)
            if file_id in db.files:
                db.files[file_id]["points_required"] = price
                await db.save_all()
                await update.message.reply_text(f"✅ Price updated to {price} points.")
            context.user_data['setting_price_for'] = None
        except:
            await update.message.reply_text("Please enter a valid number.")
        return
        
    await update.message.reply_text("I didn't understand that. Send a file to upload, or use the menu.")

async def post_init(application: Application):
    await db.load_all()
    logger.info("Bot is ready!")

def main():
    if not BOT_TOKEN:
        logger.error("No BOT_TOKEN provided!")
        return
        
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(main_callback_handler))
    
    # Text messages and AI
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))
    app.add_handler(CommandHandler("ai", handle_ai_chat))
    
    # File uploads (Document, Photo, Video, Audio, Voice)
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_file_upload))
    
    logger.info("Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
