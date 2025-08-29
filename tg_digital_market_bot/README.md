
# Telegram Digital Goods Marketplace Bot (Compliant Template)

**IMPORTANT:** This template is ONLY for lawful digital goods (e.g., e‑books, templates, icons, course files, stock photos, license keys).
It **must not** be used to buy/sell/transfer platform accounts, credentials, `tdata`, session files, or any material that violates terms of service or applicable laws.

## Features
- Country‑wise pricing and capacity (inventory limits)
- Sellers can upload digital items per country
- Buyers can browse and create orders by country
- Admins can deliver an item from inventory to fulfill an order
- Escrow: after delivery, the bot auto‑releases funds to the seller after a configurable time (per country)
- Seller balances & payout requests (manual approval)
- SQLite for storage; simple file storage in `./storage`
- **Content gate**: rejects suspicious filenames (e.g., `tdata`, `.session`, `.json` intended for account/session distribution)

## Quick Start

1. **Create a bot** with BotFather and get your token.
2. Copy `.env.example` to `.env` and fill values:
   ```env
   BOT_TOKEN=123456:ABC...
   ADMIN_IDS=123456789,987654321
   DB_PATH=./market.db
   STORAGE_DIR=./storage
   ```
3. Install dependencies:
   ```bash
   python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
   pip install -r requirements.txt
   ```
4. Initialize the database (auto on first run). Start the bot:
   ```bash
   python main.py
   ```

## Admin Commands
- `/admin` – show admin help
- `/add_country BD Bangladesh price=5 capacity=100 confirm=30m`
- `/set_price BD 6`
- `/set_capacity BD 120`
- `/set_confirm BD 45m`
- `/countries` – list country configurations
- `/orders` – list recent orders
- `/deliver <order_id>` – deliver an available inventory item to the buyer

## Seller Commands
- `/seller` – register as seller
- `/upload <COUNTRY_CODE>` – set the next uploaded file to attach to the chosen country
- Send a **file** right after `/upload` – it will be stored and added to inventory
- `/balance` – view balance
- `/withdraw <amount>` – request payout (manual)

## Buyer Commands
- `/shop` – browse available items by country and create orders
- `/my_orders` – view your orders

## Notes
- Payments are **manual** in this template. Replace/extend with your gateway (Stripe, SSLCommerz, bKash, etc.).
- The auto‑release task runs in the background and credits sellers after the country's confirmation window.
- The bot **rejects** suspicious file names (e.g., contains `tdata`, `.session`, or ends with `.json`). Adjust in `utils.py` if needed.

## Legal
Use at your own responsibility. Ensure compliance with all applicable laws and platform terms. This template forbids trading accounts or security credentials.
