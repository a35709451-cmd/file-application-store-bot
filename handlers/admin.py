from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from utils import is_owner
from config import OWNER_ID

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not await is_owner(user_id):
        return

    keyboard = [
        [InlineKeyboardButton("Pending Approvals", callback_data="admin_approvals")],
        [InlineKeyboardButton("All Users", callback_data="admin_users")],
        [InlineKeyboardButton("Ban/Unban", callback_data="admin_ban")],
        [InlineKeyboardButton("Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("Back to Menu", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        "👑 *Admin Dashboard*\n\nSelect an option below:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    user_id = query.from_user.id
    
    if not await is_owner(user_id):
        return

    if action == "admin_approvals":
        await view_pending_approvals(update, context)
    elif action == "admin_users":
        await query.answer("Total Users: " + str(len(db.users)))
    elif action == "admin_ban":
        context.user_data['awaiting_ban_id'] = True
        await query.edit_message_text("Send the User ID to ban/unban:")
    elif action == "admin_broadcast":
        context.user_data['awaiting_broadcast'] = True
        await query.edit_message_text("Send the message to broadcast:")

async def view_pending_approvals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    pending = [uid for uid, item in db.approvals.items() if item['status'] == 'pending']
    if not pending:
        await query.edit_message_text("No pending approvals.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin_panel")]]))
        return
        
    uid = pending[0]
    item = db.approvals[uid]
    
    text = f"📄 *Pending File*\nName: `{item['name']}`\nType: `{item['type']}`\nUploader ID: `{item['uploader']}`"
    
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")],
        [InlineKeyboardButton("Back", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not await is_owner(user_id):
        return
        
    if context.user_data.get('awaiting_ban_id'):
        target_id = update.message.text.strip()
        is_banned = db.users.get(target_id, {}).get("banned", False)
        if target_id not in db.users:
            db.users[target_id] = {}
        db.users[target_id]["banned"] = not is_banned
        await db.save_all()
        await update.message.reply_text(f"User {target_id} banned status: {not is_banned}")
        context.user_data['awaiting_ban_id'] = False
        
    elif context.user_data.get('awaiting_broadcast'):
        msg = update.message.text
        sent = 0
        for uid in db.users.keys():
            try:
                await context.bot.send_message(chat_id=int(uid), text=f"📢 Broadcast:\n\n{msg}")
                sent += 1
            except:
                pass
        await update.message.reply_text(f"Broadcast sent to {sent} users.")
        context.user_data['awaiting_broadcast'] = False
