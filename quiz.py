import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from utils import is_banned, get_user_points, deduct_points, add_points, build_menu
from config import OWNER_ID, LOG_CHANNEL_ID

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if await is_banned(user_id):
        return

    # Check for document, video, photo, audio, voice, etc
    file_obj = None
    file_type = ""
    is_zip = False
    
    if update.message.document:
        file_obj = update.message.document
        file_type = "document"
        is_zip = (file_obj.file_name or "").lower().endswith(".zip")
    elif update.message.photo:
        file_obj = update.message.photo[-1]
        file_type = "photo"
    elif update.message.video:
        file_obj = update.message.video
        file_type = "video"
    elif update.message.audio:
        file_obj = update.message.audio
        file_type = "audio"
    elif update.message.voice:
        file_obj = update.message.voice
        file_type = "voice"
    else:
        return
        
    if not file_obj:
        return
        
    unique_id = str(uuid.uuid4())[:8]
    
    file_entry = {
        "id": unique_id,
        "file_id": file_obj.file_id,
        "name": getattr(file_obj, "file_name", f"{file_type}_{unique_id}"),
        "uploader": str(user_id),
        "type": file_type,
        "is_zip": is_zip,
        "points_required": 0,
        "is_public": False,
        "folder": None,
        "status": "pending", # Needs admin approval
        "date": datetime.now().isoformat()
    }
    
    # Store in pending approvals
    db.approvals[unique_id] = file_entry
    await db.save_all()
    
    # Notify Admin/Log Channel
    notify_id = LOG_CHANNEL_ID if LOG_CHANNEL_ID else OWNER_ID
    try:
        await context.bot.send_message(
            chat_id=notify_id,
            text=f"📤 *New File Upload*\nFile: `{file_entry['name']}`\nUser: `{user_id}`\nType: `{file_type}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{unique_id}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"reject_{unique_id}")]
            ])
        )
    except Exception as e:
        print("Log error:", e)
        
    await update.message.reply_text("✅ File uploaded! It is currently pending Admin approval.")

async def handle_file_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    user_id = query.from_user.id
    
    if action.startswith("approve_"):
        file_id = action.split("_")[1]
        if file_id in db.approvals:
            file_entry = db.approvals.pop(file_id)
            file_entry["status"] = "approved"
            db.files[file_id] = file_entry
            
            # Award points
            points = 5 if file_entry.get("is_zip") else 2
            await add_points(file_entry["uploader"], points)
            await db.save_all()
            
            try:
                await context.bot.send_message(
                    chat_id=int(file_entry["uploader"]),
                    text=f"🎉 Your file `{file_entry['name']}` was approved! You earned {points} points."
                )
            except:
                pass
            await query.edit_message_text("✅ Approved!")
            
    elif action.startswith("reject_"):
        file_id = action.split("_")[1]
        if file_id in db.approvals:
            file_entry = db.approvals.pop(file_id)
            await db.save_all()
            try:
                await context.bot.send_message(
                    chat_id=int(file_entry["uploader"]),
                    text=f"❌ Your file `{file_entry['name']}` was rejected."
                )
            except:
                pass
            await query.edit_message_text("❌ Rejected!")
            
    elif action == "my_files":
        user_files = [f for f in db.files.values() if f["uploader"] == str(user_id)]
        if not user_files:
            await query.edit_message_text("You have no files.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="main_menu")]]))
            return
            
        keyboard = []
        for f in user_files[:20]:
            keyboard.append([InlineKeyboardButton(f['name'], callback_data=f"edit_{f['id']}")])
        keyboard.append([InlineKeyboardButton("Back", callback_data="main_menu")])
        await query.edit_message_text("📚 *Your Files*\nSelect to edit:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif action.startswith("edit_"):
        file_id = action.split("_")[1]
        f = db.files.get(file_id)
        if not f or f["uploader"] != str(user_id):
            return
            
        status = "Public 🌐" if f["is_public"] else "Private 🔒"
        text = f"📄 *{f['name']}*\nPrivacy: {status}\nPrice: {f['points_required']} pts"
        
        keyboard = [
            [InlineKeyboardButton("Toggle Privacy", callback_data=f"togglepub_{file_id}")],
            [InlineKeyboardButton("Set Price", callback_data=f"setprice_{file_id}")],
            [InlineKeyboardButton("Back", callback_data="my_files")]
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif action.startswith("togglepub_"):
        file_id = action.split("_")[1]
        f = db.files.get(file_id)
        if f and f["uploader"] == str(user_id):
            f["is_public"] = not f["is_public"]
            await db.save_all()
            await query.answer("Privacy toggled!")
            # Re-trigger edit screen
            query.data = f"edit_{file_id}"
            await handle_file_callbacks(update, context)
            
    elif action.startswith("setprice_"):
        file_id = action.split("_")[1]
        f = db.files.get(file_id)
        if f and f["uploader"] == str(user_id):
            context.user_data['setting_price_for'] = file_id
            await query.edit_message_text("Send the new price (number of points):")

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Logic for downloading handled by a link system (e.g. /start file_ID)
    pass
