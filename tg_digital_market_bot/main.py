
import os, asyncio, logging, time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)

import db
from utils import is_filename_allowed, save_upload, price_to_str
from keyboards import shop_keyboard

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("marketbot")

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id)
    text = ("👋 স্বাগতম!\n\nএটা একটি **ল'ফুল ডিজিটাল গুডস** মার্কেটপ্লেস বট টেমপ্লেট।\n"
            "👉 ক্রেতা: /shop\n"
            "👉 বিক্রেতা হতে: /seller\n"
            "👉 ব্যালেন্স: /balance\n\n"
            "🔒 মনে রাখো: এখানে কোনো অ্যাকাউন্ট/ক্রেডেনশিয়াল/`tdata`/সেশন ফাইল বিক্রি করা যাবে না।")
    await update.message.reply_text(text)

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    help_text = (
        "🛠️ **Admin Panel**\n\n"
        "/add_country <CODE> <Name> price=<amount> capacity=<n> confirm=<Xm|Xh>\n"
        "/set_price <CODE> <amount>\n"
        "/set_capacity <CODE> <n>\n"
        "/set_confirm <CODE> <Xm|Xh>\n"
        "/countries – list\n"
        "/orders – recent orders\n"
        "/deliver <order_id>\n"
    )
    await update.message.reply_text(help_text)

def parse_money_to_cents(v: str) -> int:
    return int(round(float(v) * 100))

def parse_duration_to_minutes(v: str) -> int:
    v = v.lower().strip()
    if v.endswith("m"):
        return int(v[:-1])
    if v.endswith("h"):
        return int(v[:-1]) * 60
    return int(v)  # assume minutes

async def cmd_add_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("ব্যবহার: /add_country <CODE> <Name> price=<amount> capacity=<n> confirm=<Xm|Xh>")
        return
    code = context.args[0].upper()
    name = context.args[1]
    price = 0
    capacity = 0
    confirm = 30
    for arg in context.args[2:]:
        if arg.startswith("price="):
            price = parse_money_to_cents(arg.split("=",1)[1])
        elif arg.startswith("capacity="):
            capacity = int(arg.split("=",1)[1])
        elif arg.startswith("confirm="):
            confirm = parse_duration_to_minutes(arg.split("=",1)[1])
    db.add_country(code, name, price, capacity, confirm)
    await update.message.reply_text(f"✅ Country saved: {code} {name}, price={price/100:.2f}, capacity={capacity}, confirm={confirm}m")

async def cmd_set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("ব্যবহার: /set_price <CODE> <amount>")
        return
    code, amount = context.args
    db.set_price(code.upper(), parse_money_to_cents(amount))
    await update.message.reply_text("✅ Updated.")

async def cmd_set_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("ব্যবহার: /set_capacity <CODE> <n>")
        return
    code, n = context.args
    db.set_capacity(code.upper(), int(n))
    await update.message.reply_text("✅ Updated.")

async def cmd_set_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("ব্যবহার: /set_confirm <CODE> <Xm|Xh>")
        return
    code, dur = context.args
    minutes = parse_duration_to_minutes(dur)
    db.set_confirm_minutes(code.upper(), minutes)
    await update.message.reply_text("✅ Updated.")

async def cmd_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.list_countries()
    if not rows:
        await update.message.reply_text("কোনো country সেট করা নেই।")
        return
    lines = ["🌍 Countries:"]
    for r in rows:
        lines.append(f"- {r['code']} {r['name']}: price {price_to_str(r['price_cents'])}, cap {r['capacity']}, confirm {r['confirm_minutes']}m")
    await update.message.reply_text("\n".join(lines))

async def cmd_seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_role(update.effective_user.id, "seller")
    await update.message.reply_text("✅ তুমি এখন seller. `/upload <CODE>` দিয়ে আপলোড শুরু করো।")

async def cmd_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db.get_role(update.effective_user.id) != "seller":
        await update.message.reply_text("Seller হতে `/seller` চালাও।")
        return
    if not context.args:
        await update.message.reply_text("ব্যবহার: /upload <COUNTRY_CODE>")
        return
    code = context.args[0].upper()
    if not db.get_country(code):
        await update.message.reply_text("এই country কোডটি নেই। আগে admin add করুক।")
        return
    db.set_pending_upload(update.effective_user.id, code)
    await update.message.reply_text(f"✅ Country `{code}` সেট হয়েছে। এখন একটি **ফাইল পাঠাও** (zip/pdf/png/jpg/txt/csv).", parse_mode="Markdown")

async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    role = db.get_role(user.id)
    if role != "seller":
        return
    code = db.pop_pending_upload(user.id)
    if not code:
        return  # no pending upload intent
    doc = update.message.document
    name = doc.file_name or "file.bin"
    if not is_filename_allowed(name):
        await update.message.reply_text("⚠️ এই ফাইলটি অনুমোদিত নয়। (অ্যাকাউন্ট/session/tdata/json ইত্যাদি গ্রহণযোগ্য নয়)")
        return
    # download file
    file = await context.bot.get_file(doc.file_id)
    tf = await file.download_to_drive(custom_path=os.path.join(STORAGE_DIR, f"tmp_{doc.file_unique_id}"))
    saved_path, size = save_upload(tf.name, name)
    os.remove(tf.name)
    db.add_inventory(user.id, code, saved_path, name, size)
    await update.message.reply_text(f"✅ যোগ হয়েছে: `{name}` → {code}", parse_mode="Markdown")

async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # show countries with available inventory count <= capacity (simple: using capacity as stock ceiling)
    rows = db.list_countries()
    if not rows:
        await update.message.reply_text("Shop ফাঁকা।")
        return
    # For demo, show all countries; capacity shown; inventory count separately on buy.
    await update.message.reply_text("🛒 বেছে নাও:", reply_markup=shop_keyboard(rows))

async def on_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    if not data.startswith("buy:"):
        return
    code = data.split(":",1)[1]
    country = db.get_country(code)
    if not country:
        await query.message.reply_text("এই country পাওয়া যায়নি।")
        return
    inv = db.get_available_inventory(code)
    if not inv:
        await query.message.reply_text("স্টক শেষ। পরে চেষ্টা করো।")
        return
    order_id = db.create_order(query.from_user.id, code)
    price = country["price_cents"]
    # Notify buyer
    await query.message.reply_text(f"🧾 অর্ডার #{order_id} তৈরি হয়েছে {code} • মূল্য {price/100:.2f}\n"
                                   "পেমেন্ট সম্পন্ন হলে admin ডেলিভারি করবে।")
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, f"🔔 নতুন অর্ডার #{order_id} • দেশ {code} • Buyer {query.from_user.id}\n"
                                                     f"ডেলিভারি করতে: /deliver {order_id}")
        except Exception as e:
            pass

async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    rows = db.list_orders(20)
    if not rows:
        await update.message.reply_text("কোনো অর্ডার নেই।")
        return
    lines = ["🧾 সাম্প্রতিক অর্ডার:"]
    for r in rows:
        lines.append(f"#{r['id']} {r['country_code']} • {r['status']} • buyer {r['buyer_id']}")
    await update.message.reply_text("\n".join(lines))

async def cmd_deliver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("ব্যবহার: /deliver <order_id>")
        return
    oid = int(context.args[0])
    order = db.get_order(oid)
    if not order:
        await update.message.reply_text("অর্ডার পাওয়া যায়নি।")
        return
    if order["status"] != "pending":
        await update.message.reply_text("এই অর্ডার pending নেই।")
        return
    code = order["country_code"]
    country = db.get_country(code)
    inv = db.get_available_inventory(code)
    if not inv:
        await update.message.reply_text("স্টক শেষ। আগে ইনভেন্টরি যোগ করো।")
        return
    item = inv[0]
    # send the file to buyer
    try:
        await context.bot.send_document(chat_id=order["buyer_id"], document=InputFile(item["file_path"], filename=item["original_name"]),
                                        caption=f"অর্ডার #{oid} • {code}")
    except Exception as e:
        await update.message.reply_text(f"Buyer-কে ফাইল পাঠানো গেল না: {e}")
        return
    # mark used, set delivered & confirm_after
    db.mark_inventory_used(item["id"])
    confirm_after = int(time.time()) + country["confirm_minutes"] * 60
    db.set_order_delivered(oid, item["seller_id"], confirm_after)
    await update.message.reply_text(f"✅ ডেলিভারড। অর্ডার #{oid} • seller {item['seller_id']} • auto-release {country['confirm_minutes']} মিনিট পর")

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cents = db.get_balance(update.effective_user.id)
    await update.message.reply_text(f"💰 ব্যালেন্স: {cents/100:.2f}")

async def cmd_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db.get_role(update.effective_user.id) != "seller":
        await update.message.reply_text("Seller নও। `/seller` চালাও।")
        return
    if not context.args:
        await update.message.reply_text("ব্যবহার: /withdraw <amount>")
        return
    amt = float(context.args[0])
    cents = int(round(amt * 100))
    have = db.get_balance(update.effective_user.id)
    if cents <= 0 or cents > have:
        await update.message.reply_text("Invalid amount বা ব্যালেন্স কম।")
        return
    # For template, just record a payout request; admin will handle manually
    db.request_payout(update.effective_user.id, cents)
    await update.message.reply_text("✅ payout request নেয়া হয়েছে।")

async def escrow_sweeper(app):
    while True:
        try:
            now_ts = int(time.time())
            due = db.due_releases(now_ts)
            for r in due:
                # credit seller
                order = r
                if order["seller_id"]:
                    country = db.get_country(order["country_code"])
                    price = country["price_cents"] if country else 0
                    db.add_balance(order["seller_id"], price)
                db.release_order(order["id"])
                # notify seller
                try:
                    await app.bot.send_message(order["seller_id"], f"✅ অর্ডার #{order['id']} রিলিজ করা হয়েছে। ব্যালেন্স ক্রেডিট হয়েছে।")
                except Exception:
                    pass
        except Exception as e:
            log.error("escrow task error: %s", e)
        await asyncio.sleep(30)

async def on_startup(app):
    db.init_db()
    app.job = asyncio.create_task(escrow_sweeper(app))
    log.info("Bot started.")

async def on_shutdown(app):
    if hasattr(app, "job"):
        app.job.cancel()

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("add_country", cmd_add_country))
    app.add_handler(CommandHandler("set_price", cmd_set_price))
    app.add_handler(CommandHandler("set_capacity", cmd_set_capacity))
    app.add_handler(CommandHandler("set_confirm", cmd_set_confirm))
    app.add_handler(CommandHandler("countries", cmd_countries))

    app.add_handler(CommandHandler("seller", cmd_seller))
    app.add_handler(CommandHandler("upload", cmd_upload))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))

    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CallbackQueryHandler(on_buy_callback, pattern=r"^buy:"))

    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("deliver", cmd_deliver))

    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("withdraw", cmd_withdraw))

    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
