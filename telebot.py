import os
import logging
import pip
from datetime import datetime
from dotenv import load_dotenv
import psutil
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils import get_weather, get_prayer_times, get_today_schedule, get_quote, get_eight_ball, ask_groq, ask_local

# ── Config ──────────────────────────────────────────────────────────────────
load_dotenv()

TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
YOUR_CHAT_ID    = os.getenv("CHAT_ID")
ALLOWED_USER_ID = int(os.getenv("CHAT_ID"))

logging.basicConfig(level=logging.INFO)

# ── Auth Guard ──────────────────────────────────────────────────────────────
def is_authorized(update: Update) -> bool:
    return update.effective_user.id == ALLOWED_USER_ID

# ── Scheduled Briefing ──────────────────────────────────────────────────────
async def send_morning_briefing(app):
    try:
        await app.bot.send_message(chat_id=YOUR_CHAT_ID, text=(
            f"🌅 Morning, Affan.\n"
            f"📆 {datetime.now().strftime('%A, %d %B %Y')}\n\n"
            f"{get_prayer_times()}\n\n"
            f"{get_today_schedule()}\n\n"
            f"{get_quote()}"
        ))
    except Exception as e:
        logging.error(f"Briefing error: {e}")

# ── Commands ────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text(
        "Paideia online. Welcome, Affan. 🤖\n\n"
        "/start — Start bot\n"
        "/stats — PN41 system stats\n"
        "/today — Today's schedule\n"
        "/prayer — Prayer times\n"
        "/weather — Current weather\n"
        "/8ball — Ask a question\n"
        "/terra — Ask local\n"
        "/shutdown — Shut down PN41\n\n"
        "Type anything to chat."
    )

# -- HANDLERS ---------------------------------------------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    net  = psutil.net_io_counters()
    sent = net.bytes_sent // (1024 ** 2)
    recv = net.bytes_recv // (1024 ** 2)
    await update.message.reply_text(
        f"🖥️ PN41 Stats\n"
        f"CPU: {cpu}%\n"
        f"RAM: {ram}%\n"
        f"Storage: {disk}% used\n"
        f"Net: ↑ {sent}MB ↓ {recv}MB"
    )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text(get_today_schedule())

async def prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text(get_prayer_times())

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text(get_weather())

async def eight_ball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text(
            "Ask me a question!\nExample: `/8ball will today be good?`",
            parse_mode="Markdown"
        )
        return
    await update.message.reply_text(f"❓ {question}\n\n{get_eight_ball()}")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text("PN41 is shutting down. Goodbye.")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

# ── AI Chat Cloud ─────────────────────────────────────────────────────────────────
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text("🌌 Aether: ")
    reply = ask_groq(update.message.text)
    if   "429"   in reply: await update.message.reply_text("⚠️ AI quota reached.")
    elif "401"   in reply: await update.message.reply_text("⚠️ Invalid API key.")
    elif "ERROR" in reply: await update.message.reply_text("❌ AI error.")
    else:                  await update.message.reply_text(reply)
# -- AI Chat Local ---------------------------------------------------------------------
async def local(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("Usage: `/terra what is 2+2`", parse_mode="Markdown")
        return
    await update.message.reply_text("🌍 Terra:")
    reply = ask_local(question)
    await update.message.reply_text(reply)

# ── App Entry ────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Scheduler
    scheduler = AsyncIOScheduler(timezone="Asia/Singapore")
    scheduler.add_job(send_morning_briefing, 'cron', hour=7, minute=0, args=[app])

    # Handlers
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("stats",    stats))
    app.add_handler(CommandHandler("today",    today))
    app.add_handler(CommandHandler("prayer",   prayer))
    app.add_handler(CommandHandler("weather",  weather))
    app.add_handler(CommandHandler("8ball",    eight_ball))
    app.add_handler(CommandHandler("shutdown", shutdown))
    app.add_handler(CommandHandler("terra", local))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    async def on_startup(app):
        scheduler.start()
        logging.info("Scheduler started — morning briefing at 7:00 AM SGT")

    app.post_init = on_startup

    print("Paideia is running. Morning briefing set for 7:00 AM SGT.")
    app.run_polling()

if __name__ == "__main__":
    main()