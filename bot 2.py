
from telegram import Update, Bot, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os

ADMIN_IDS = [6016683553, 6905447988]
TICKET_FILE = "tickets.json"
TICKET_COUNTER = 0

if not os.path.exists(TICKET_FILE):
    with open(TICKET_FILE, "w") as f:
        json.dump({}, f)

with open(TICKET_FILE, "r") as f:
    tickets = json.load(f)

if tickets:
    TICKET_COUNTER = max([int(t.split('#')[-1]) for t in tickets]) + 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TICKET_COUNTER
    user = update.message.from_user
    ticket_id = f"#00{TICKET_COUNTER}"
    tickets[ticket_id] = {
        "user_id": user.id,
        "username": user.username,
        "messages": []
    }
    TICKET_COUNTER += 1
    with open(TICKET_FILE, "w") as f:
        json.dump(tickets, f)

    await update.message.reply_text(
        "**👋 Welcome to *Vendora Exchange*!**

"
        "**To get started, please type `/exchange`** to open a support ticket.
"
        f"**Your ticket ID:** `{ticket_id}`

"
        "An admin will be with you shortly!",
        parse_mode=ParseMode.MARKDOWN
    )

async def exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    for ticket_id, ticket in tickets.items():
        if ticket["user_id"] == user.id:
            await update.message.reply_text(
                f"**🔁 Ticket {ticket_id} already created. You can now message us here.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    await start(update, context)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text

    for ticket_id, ticket in tickets.items():
        if ticket["user_id"] == user.id:
            ticket["messages"].append({"from": "user", "text": text})
            with open(TICKET_FILE, "w") as f:
                json.dump(tickets, f)

            for admin_id in ADMIN_IDS:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📩 Message from {user.username or user.id} in Ticket {ticket_id}:

{text}"
                )
            break

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = update.message.from_user
    if admin.id not in ADMIN_IDS:
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reply <ticket_id> <message>")
        return

    ticket_id = context.args[0]
    message = " ".join(context.args[1:])

    if ticket_id in tickets:
        user_id = tickets[ticket_id]["user_id"]
        await context.bot.send_message(chat_id=user_id, text=f"💬 Admin: {message}")
        tickets[ticket_id]["messages"].append({"from": "admin", "text": message})
        with open(TICKET_FILE, "w") as f:
            json.dump(tickets, f)
    else:
        await update.message.reply_text("❌ Ticket not found.")

def main():
    bot_token = os.environ.get("BOT_TOKEN") or "your-telegram-bot-token"
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("exchange", exchange))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
