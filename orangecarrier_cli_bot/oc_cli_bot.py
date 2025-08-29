
# oc_cli_bot.py
# Scrape OrangeCarrier Live Calls page for CLI numbers and post last-5 digits to a Telegram group.
#
# Usage:
#   1) pip install -r requirements.txt
#   2) python -m playwright install
#   3) Copy .env.example to .env and fill in your values.
#   4) python oc_cli_bot.py
#
# Notes:
# - The script tries programmatic login first. If that fails, it will open the browser so you can log in manually once.
# - After a successful login, it saves session state to `.oc_storage.json` for reuse.
# - It polls the Live Calls table every few seconds and sends new CLIs (last 5 digits separated) to Telegram.

import os
import re
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

ORANGE_LOGIN_URL = os.getenv("ORANGE_LOGIN_URL", "https://www.orangecarrier.com/login")
ORANGE_LIVE_URL = os.getenv("ORANGE_LIVE_URL", "https://www.orangecarrier.com/live/calls")
ORANGE_EMAIL = os.getenv("ORANGE_EMAIL", "")
ORANGE_PASSWORD = os.getenv("ORANGE_PASSWORD", "")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")  # Group ID (negative number) or user ID
SEND_MODE = os.getenv("SEND_MODE", "both")  # "last5" | "cli" | "both"

HEADLESS = os.getenv("HEADLESS", "1")  # "1" = headless, "0" = show browser
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))

STORAGE_FILE = os.getenv("STORAGE_FILE", ".oc_storage.json")

PHONE_RE = re.compile(r"(?:^|\\D)(\\+?\\d{7,16})(?:\\D|$)")

def send_telegram(text: str) -> None:
    if not (BOT_TOKEN and CHAT_ID):
        print("[!] BOT_TOKEN or CHAT_ID not set, skipping Telegram send.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=payload, timeout=15)
        if r.status_code != 200:
            print(f"[!] Telegram send failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[!] Telegram exception: {e}")

def extract_cli_from_row_text(row_text: str) -> str | None:
    # Heuristic: First long-ish number in the row is the CLI (A-number)
    m = PHONE_RE.search(row_text.replace("\\n", " "))
    if not m:
        return None
    cli = re.sub(r"\\D", "", m.group(1))  # keep digits only
    if cli.startswith("00"):
        cli = cli[2:]
    return cli

def format_last5(cli: str) -> str:
    last5 = cli[-5:] if len(cli) >= 5 else cli
    return " ".join(list(last5))

def login_programmatically(page) -> bool:
    try:
        page.goto(ORANGE_LOGIN_URL, timeout=60000)
        # Try common selectors for email/username + password
        email_sel = "input[name='email'], input[type='email'], input[name='username']"
        pass_sel = "input[name='password'], input[type='password']"
        page.wait_for_selector(email_sel, timeout=15000)
        page.fill(email_sel, ORANGE_EMAIL)
        page.fill(pass_sel, ORANGE_PASSWORD)
        # Click a submit button
        # Try several possibilities
        selectors = [
            "button[type='submit']",
            "button:has-text('Login')",
            "input[type='submit']",
            "button:has-text('Sign in')",
        ]
        clicked = False
        for sel in selectors:
            try:
                page.click(sel, timeout=3000)
                clicked = True
                break
            except Exception:
                pass
        if not clicked:
            # Try pressing Enter
            page.keyboard.press("Enter")
        # If login works, we should be able to reach live calls page
        page.wait_for_timeout(2000)
        page.goto(ORANGE_LIVE_URL, timeout=60000)
        # Wait for a table to appear
        page.wait_for_selector("table", timeout=20000)
        return True
    except Exception as e:
        print(f"[i] Programmatic login failed or not found: {e}")
        return False

def ensure_logged_in(pw, use_headless: bool):
    if os.path.exists(STORAGE_FILE):
        context = pw.chromium.launch_persistent_context(
            user_data_dir="oc_user_data",
            headless=use_headless,
        )
        page = context.new_page()
        try:
            page.goto(ORANGE_LIVE_URL, timeout=60000)
            page.wait_for_selector("table", timeout=20000)
            return context, page
        except Exception:
            print("[i] Existing session not valid; will re-login.")
            context.close()

    browser = pw.chromium.launch(headless=use_headless)
    context = browser.new_context()
    page = context.new_page()

    # Try programmatic login first
    if ORANGE_EMAIL and ORANGE_PASSWORD and login_programmatically(page):
        # save storage for reuse
        context.storage_state(path=STORAGE_FILE)
        return context, page

    # Fallback: manual login
    print("[*] Manual login required. A browser window will open (set HEADLESS=0 for visibility).")
    if use_headless:
        print("[!] You set HEADLESS=1. Please set HEADLESS=0 and run again to complete manual login once.")
        raise SystemExit(1)
    page.goto(ORANGE_LOGIN_URL, timeout=60000)
    input(">> Log in manually, navigate to Live Calls page, then press ENTER here...")
    try:
        page.goto(ORANGE_LIVE_URL, timeout=60000)
        page.wait_for_selector("table", timeout=20000)
    except Exception as e:
        print(f"[!] Could not reach live calls table after manual login: {e}")
        raise SystemExit(1)
    context.storage_state(path=STORAGE_FILE)
    return context, page

def scrape_loop(page):
    seen = set()
    print("[*] Watching Live Calls...")
    while True:
        try:
            # Try to ensure we are on the Live Calls page
            if ORANGE_LIVE_URL not in page.url:
                page.goto(ORANGE_LIVE_URL, timeout=60000)
            # Grab all table rows
            rows = page.query_selector_all("table tbody tr")
            if not rows:
                # Some pages use div-based grids; fallback: scan all text blocks
                blocks = page.query_selector_all("tbody, .table, .dataTables_wrapper, body")
                texts = [b.inner_text() for b in blocks if b]
                row_texts = texts if texts else [page.inner_text("body")]
            else:
                row_texts = [r.inner_text() for r in rows]

            for rt in row_texts:
                # Deduplicate on full row text hash
                key = hash(rt)
                if key in seen:
                    continue
                cli = extract_cli_from_row_text(rt)
                if not cli:
                    continue
                # Send to Telegram
                last5_spaced = format_last5(cli)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if SEND_MODE == "last5":
                    msg = f"{last5_spaced}"
                elif SEND_MODE == "cli":
                    msg = f"{cli}"
                else:
                    msg = f"CLI: {cli}\nLast5: {last5_spaced}\n⏱ {now}"
                send_telegram(msg)
                print(f"[+] Sent: {msg.replace(os.linesep, ' | ')}")
                seen.add(key)

        except PlaywrightTimeoutError:
            print("[i] Timeout while reading the page; will retry.")
        except Exception as e:
            print(f"[!] Loop error: {e}")
        time.sleep(POLL_SECONDS)

def main():
    use_headless = HEADLESS != "0"
    with sync_playwright() as pw:
        context, page = ensure_logged_in(pw, use_headless)
        try:
            scrape_loop(page)
        finally:
            try:
                context.storage_state(path=STORAGE_FILE)
            except Exception:
                pass
            context.close()

if __name__ == "__main__":
    main()
