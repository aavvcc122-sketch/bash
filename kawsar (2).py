import time
import requests
import logging
import json
import os
import re
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TimedOut
import asyncio

# === CONFIG ===
BOT_TOKEN = '7460329945:AAGDTo3lW0kgf-ZVkzwRhjCYdIxcNghvu6Y'
CHAT_ID = '-1002597441798'
USERNAME = 'Nayemislam1010'
PASSWORD = 'Aaccaacc12$'
BASE_URL = "http://193.70.33.154"
LOGIN_PAGE_URL = BASE_URL + "/ints/login"
LOGIN_POST_URL = BASE_URL + "/ints/signin"
DATA_URL = BASE_URL + "/ints/agent/res/data_smscdr.php"

bot = Bot(token=BOT_TOKEN)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

logging.basicConfig(level=logging.INFO, format='%(message)s')

def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )

def save_already_sent(already_sent):
    with open("already_sent.json", "w") as f:
        json.dump(list(already_sent), f)

def load_already_sent():
    if os.path.exists("already_sent.json"):
        with open("already_sent.json", "r") as f:
            return set(json.load(f))
    return set()

def login():
    try:
        resp = session.get(LOGIN_PAGE_URL)
        match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
        if not match:
            logging.error("Captcha not found.")
            return False
        num1, num2 = int(match.group(1)), int(match.group(2))
        captcha_answer = num1 + num2

        payload = {
            "username": USERNAME,
            "password": PASSWORD,
            "capt": captcha_answer
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": LOGIN_PAGE_URL
        }

        resp = session.post(LOGIN_POST_URL, data=payload, headers=headers)
        if "dashboard" in resp.text.lower() or "logout" in resp.text.lower():
            logging.info("Login successful ✅")
            return True
        else:
            logging.error("Login failed ❌")
            return False
    except Exception as e:
        logging.error(f"Login error: {e}")
        return False

def build_api_url():
    start_date = "2025-04-27"
    end_date = "2026-01-01"
    return (
        f"{DATA_URL}?fdate1={start_date}%2000:00:00&fdate2={end_date}%2023:59:59&"
        "frange=&fnum=&fcli=&fgdate=&fgmonth=&fgrange=&fgnumber=&fgcli=&fg=0&"
        "sEcho=1&iColumns=7&sColumns=%2C%2C%2C%2C%2C%2C&iDisplayStart=0&iDisplayLength=25&"
        "mDataProp_0=0&sSearch_0=&bRegex_0=false&bSearchable_0=true&bSortable_0=true&"
        "mDataProp_1=1&sSearch_1=&bRegex_1=false&bSearchable_1=true&bSortable_1=true&"
        "mDataProp_2=2&sSearch_2=&bRegex_2=false&bSearchable_2=true&bSortable_2=true&"
        "mDataProp_3=3&sSearch_3=&bRegex_3=false&bSearchable_3=true&bSortable_3=true&"
        "mDataProp_4=4&sSearch_4=&bRegex_4=false&bSearchable_4=true&bSortable_4=true&"
        "mDataProp_5=5&sSearch_5=&bRegex_5=false&bSearchable_5=true&bSortable_5=true&"
        "mDataProp_6=6&sSearch_6=&bRegex_6=false&bSearchable_6=true&bSortable_6=true&"
        "sSearch=&bRegex=false&iSortCol_0=0&sSortDir_0=desc&iSortingCols=1"
    )

def fetch_data():
    url = build_api_url()
    headers = {
        "X-Requested-With": "XMLHttpRequest"
    }

    try:
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logging.error(f"[!] JSON decode error: {e}")
                logging.debug("Partial response:\n" + response.text[:300])
                return None
        elif response.status_code == 403 or "login" in response.text.lower():
            logging.warning("Session expired. Re-logging...")
            if login():
                return fetch_data()
            return None
        else:
            logging.error(f"Unexpected error: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Fetch error: {e}")
        return None

already_sent = load_already_sent()

async def sent_messages():
    logging.info("🔍 Checking for messages...\n")
    data = fetch_data()

    if data and 'aaData' in data:
        for row in data['aaData']:
            date = str(row[0]).strip()
            number = str(row[2]).strip()
            service = str(row[3]).strip()
            message = str(row[4]).strip()

            match = re.search(r'\d{3}-\d{3}|\d{4,6}', message)
            otp = match.group() if match else None

            if otp:
                unique_key = f"{number}|{otp}"
                if unique_key not in already_sent:
                    already_sent.add(unique_key)

                    # Build HTML Message
                    text = (
                        "✨ <b>OTP Received</b> ✨\n\n"
                        f"⏰ <b>Time:</b> {escape_html(date)}\n"
                        f"📞 <b>Number:</b> {escape_html(number)}\n"
                        f"🔧 <b>Service:</b> {escape_html(service)}\n"
                        f"🔐 <b>OTP Code:</b> <code>{escape_html(otp)}</code>\n"
                        f"📝 <b>Msg:</b> <i>{escape_html(message)}</i>\n\n"
                        
                    )

                    # Buttons (inline keyboard)
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("👨‍💻 Bot Owner", url="3")],
                        [InlineKeyboardButton("🔁 Backup Channel", url="r")]
                    ])

                    try:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=text,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                            reply_markup=keyboard
                        )
                        save_already_sent(already_sent)
                        logging.info(f"[+] Sent OTP: {otp}")
                    except TimedOut:
                        logging.error("Telegram TimedOut")
                    except Exception as e:
                        logging.error(f"Telegram error: {e}")
            else:
                logging.info(f"No OTP found in: {message}")
    else:
        logging.info("No data or invalid response.")

async def main():
    if login():
        while True:
            await sent_messages()
            await asyncio.sleep(3)
    else:
        logging.error("Initial login failed. Exiting...")

# Run bot
asyncio.run(main())
