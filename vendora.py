from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os

# Admin Telegram User IDs
ADMIN_IDS = [6016683553, 6905447988]

# Tickets file
TICKET_FILE = "tickets.json"

# Ensure ticket file exists
if not os.path.exists(TICKET_FILE):
    with open(TICKET_FILE, "w") as f:
        json.dump({}, f)

# Load existing tickets
with open(TICKET_FILE, "r") as f:
    tickets = json.load(f)

# Safely calculate the next ticket number
TICKET_COUNTER = max([int(t.split('#')[-1]) for t in tickets if t.startswith("#")], default=1)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TICKET_COUNTER
    user = update.message.from_user
    ticket_id = f"#00{TICKET_COUNTER}"

    # Avoid duplicate ticket creation
    for t_id, info in tickets.items():
        if info.get("user_id") == user.id:
            await update.message.reply_text(
                f"⚠️ **You already have an open ticket:** `{t_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    # Create ticket
    tickets[ticket_id] = {
        "user_id": user.id,
        "username": user.username,
        "messages": []
    }
    TICKET_COUNTER += 1
    with open(TICKET_FILE, "w") as f:
        json.dump(tickets, f)

    await update.message.reply_text(
        "**👋 Welcome to *Vendora Exchange* 🚀**\n\n"
        "**💱 We support exchanges using:**\n"
        "— **Cash App**\n"
        "— **Apple Pay**\n"
        "— **Gift Cards**\n"
        "— **PayPal**\n\n"
        "**⚡ Start now by typing:** `/exchange`\n"
        f"**🎫 Your ticket ID:** `{ticket_id}`\n\n"
        "**_An admin will be with you shortly._**",
        parse_mode=ParseMode.MARKDOWN
    )

# /exchange command
async def exchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# Handle user messages
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
                    text=f"📨 **Message from @{user.username or user.id} in *{ticket_id}*:**\n\n{text}",
                    parse_mode=ParseMode.MARKDOWN
                )
            return

# Admin command to reply
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = update.message.from_user
    if admin.id not in ADMIN_IDS:
        return

    if len(context.args) < 2:
        await update.message.reply_text("❗ **Usage:** /reply <ticket_id> <message>")
        return

    ticket_id = context.args[0]
    message = " ".join(context.args[1:])

    if ticket_id in tickets:
        user_id = tickets[ticket_id]["user_id"]
        await context.bot.send_message(chat_id=user_id, text=f"💬 **Admin:** {message}", parse_mode=ParseMode.MARKDOWN)
        tickets[ticket_id]["messages"].append({"from": "admin", "text": message})
        with open(TICKET_FILE, "w") as f:
            json.dump(tickets, f)
    else:
        await update.message.reply_text("❌ **Ticket not found.**")

# Run the bot
def main():
    bot_token = os.environ.get("BOT_TOKEN") or "7581315978:AAGdkvo41jlY5E0vI91HFEZMpys1IhbXlDs"
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("exchange", exchange))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    print("Vendora Exchange Bot is live...")

    # Set up webhook
    webhook_url = os.environ.get("WEBHOOK_URL") or "https://yourdomain.com/webhook"
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    main()
