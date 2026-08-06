import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from utils import add_points, deduct_points

async def quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Create Quiz", callback_data="quiz_create")],
        [InlineKeyboardButton("Play Quizzes", callback_data="quiz_play")],
        [InlineKeyboardButton("Pending Answers", callback_data="quiz_pending")],
        [InlineKeyboardButton("Back", callback_data="main_menu")]
    ]
    await query.edit_message_text("🧠 *Quiz Hub*\nSelect an option:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_quiz_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    user_id = query.from_user.id
    
    if action == "quiz_menu":
        await quiz_menu(update, context)
        
    elif action == "quiz_create":
        context.user_data['quiz_draft'] = {"id": str(uuid.uuid4())[:8], "creator": str(user_id), "type": "mcq", "questions": []}
        keyboard = [
            [InlineKeyboardButton("MCQ Format", callback_data="qcreate_mcq")],
            [InlineKeyboardButton("Subjective/Word", callback_data="qcreate_sub")]
        ]
        await query.edit_message_text("Select Quiz Type:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif action.startswith("qcreate_"):
        q_type = action.split("_")[1]
        context.user_data['quiz_draft']['type'] = q_type
        context.user_data['awaiting_quiz_title'] = True
        await query.edit_message_text("Enter the title for your Quiz:")
        
    elif action == "quiz_play":
        quizzes = [q for q in db.quizzes.values()]
        if not quizzes:
            await query.edit_message_text("No quizzes available.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="quiz_menu")]]))
            return
            
        keyboard = []
        for q in quizzes[:10]:
            keyboard.append([InlineKeyboardButton(f"{q['title']} ({q['type'].upper()})", callback_data=f"playq_{q['id']}")])
        keyboard.append([InlineKeyboardButton("Back", callback_data="quiz_menu")])
        await query.edit_message_text("Select a quiz to play:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif action.startswith("playq_"):
        quiz_id = action.split("_")[1]
        quiz = db.quizzes.get(quiz_id)
        if not quiz: return
        
        # Simple implementation: sending first question
        if quiz['type'] == 'mcq':
            await query.edit_message_text(f"Starting {quiz['title']}... (MCQ logic to be fully implemented)")
        else:
            await query.edit_message_text(f"Subjective Quiz: {quiz['title']}\nSend your answer as text (Logic to be fully implemented)")

async def handle_quiz_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if context.user_data.get('awaiting_quiz_title'):
        title = update.message.text
        context.user_data['quiz_draft']['title'] = title
        context.user_data['awaiting_quiz_title'] = False
        
        # Save dummy quiz for now
        draft = context.user_data['quiz_draft']
        db.quizzes[draft['id']] = draft
        await db.save_all()
        
        await update.message.reply_text("✅ Quiz created successfully! (Further question adding logic can be expanded here)")
        context.user_data['quiz_draft'] = None
