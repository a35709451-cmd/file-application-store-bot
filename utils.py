from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import OWNER_ID
from database import db

async def is_owner(user_id):
    return user_id == OWNER_ID

async def is_banned(user_id):
    user_data = db.users.get(str(user_id), {})
    return user_data.get("banned", False)

async def get_user_points(user_id):
    return db.users.get(str(user_id), {}).get("points", 0)

async def add_points(user_id, amount):
    uid = str(user_id)
    if uid not in db.users:
        db.users[uid] = {"points": 0}
    db.users[uid]["points"] += amount
    await db.save_all()

async def deduct_points(user_id, amount):
    uid = str(user_id)
    if uid not in db.users:
        db.users[uid] = {"points": 0}
    db.users[uid]["points"] = max(0, db.users[uid]["points"] - amount)
    await db.save_all()

def build_menu(buttons, n_cols):
    return [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
