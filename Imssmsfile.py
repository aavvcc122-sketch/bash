# Coded by MD Hridoy Hossain
import requests
import re
import time
from datetime import datetime
from telegram import Bot, ParseMode

# Telegram bot config
BOT_TOKEN = '8068434240:AAF2xLDW3YJQ95wwYcI5Ir_m4x636EEIsck'
CHAT_ID = '-1002690127627'
bot = Bot(token=BOT_TOKEN)

# Country flag finder
def get_flag(number):
    if number.startswith("880"):
        return "🇧🇩"
    elif number.startswith("91"):
        return "🇮🇳"
    elif number.startswith("1"):
        return "🇺🇸"
    elif number.startswith("44"):
        return "🇬🇧"
    elif number.startswith("966"):
        return "🇸🇦"
    elif number.startswith("971"):
        return "🇦🇪"
    elif number.startswith("92"):
        return "🇵🇰"
    elif number.startswith("81"):
        return "🇯🇵"
    elif number.startswith("7"):
        return "🇷🇺"
    else:
        return "🌐"

# Platform icon
def get_icon(source):
    icons = {
        "WhatsApp": "🟢 WhatsApp",
        "Facebook": "🔵 Facebook",
        "Telegram": "🔷 Telegram",
        "Google": "🟥 Google",
    }
    return icons.get(source, f"📲 {source}")

# Extract OTP code
def extract_code(msg):
    match = re.findall(r'\b\d{3,8}[-]?\d*\b', msg)
    return match[0] if match else "N/A"

# Extract phone number from message (880... style)
def extract_number(msg):
    match = re.findall(r'\b(880\d{7,11})\b', msg)
    return match[0] if match else "Unknown"

# Already sent messages cache
sent = set()

# Main loop
while True:
    try:
        cookies = {'PHPSESSID': 'dccmla9705qtu6gjqbllhr4alg'}
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10)',
            'Referer': 'https://imssms.org/client/agent/SMSCDRReports',
            'X-Requested-With': 'XMLHttpRequest',
        }

        url = "https://imssms.org/client/res/data_smscdr.php?fdate1=2025-07-04%2000:00:00&fdate2=2025-07-04%2023:59:59"
        response = requests.get(url, headers=headers, cookies=cookies, verify=False)
        data = response.json().get("aaData", [])

        for row in data:
            range = row[1].strip()
            cctt = row[4]
            timet = row[0].strip()
            cli = row[3].strip()
            app = row[2].strip() or "Unknown"
            message = row[4].strip()
            unique_key = app + message

            if unique_key not in sent:
                sent.add(unique_key)

                extracted_number = extract_number(message)
                flag = get_flag(extracted_number)
                app_icon = get_icon(app)
                code = extract_code(message)
                time_now = datetime.now().strftime('%H:%M:%S')

                telegram_message = (
                    f"<b>✨NEW SMS ALERT✨</b>\n\n"
                    f"<b>⏰Time : </b><code>{timet}</code>\n"


                    f"<b>📞Number : </b><code>{app}</code>\n"
                    f"<b>🔧Platform : </b><code>{cli}</code>\n\n"
                    f"<b>🔑One Time Code : </b><code>{code}</code>\n\n"

                    #f"<pre>🧾 <b>Message:</b>\n"
                    f"<pre>{message}</pre>\n"
                )

                bot.send_message(chat_id=CHAT_ID, text=telegram_message, parse_mode=ParseMode.HTML)

        time.sleep(1)

    except Exception as e:
        print(f"Error: {e}")

