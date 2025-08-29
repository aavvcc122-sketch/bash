
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def shop_keyboard(countries):
    rows = []
    for c in countries:
        rows.append([InlineKeyboardButton(f"{c['code']} • {c['name']} • {c['price_cents']/100:.2f} ({c['capacity']})",
                                          callback_data=f"buy:{c['code']}")])
    return InlineKeyboardMarkup(rows)
