import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes
from config import GEMINI_API_KEY, logger

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not model:
        await update.message.reply_text("❌ AI features are disabled (No API key found).")
        return
        
    query = update.message.text.replace('/ai', '').strip()
    if not query:
        await update.message.reply_text("Please ask a question! Usage: `/ai your question`", parse_mode="Markdown")
        return
        
    await update.message.reply_chat_action("typing")
    try:
        response = model.generate_content(query)
        await update.message.reply_text(f"🤖 *AI Assistant:*\n\n{response.text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Gemini AI error: {e}")
        await update.message.reply_text("Sorry, I encountered an error while processing your request.")
