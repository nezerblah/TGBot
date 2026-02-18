import os
import httpx

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not BOT_TOKEN or not WEBHOOK_URL or not WEBHOOK_SECRET:
    print("Missing BOT_TOKEN, WEBHOOK_URL or WEBHOOK_SECRET. Set them as environment variables.")
    exit(1)

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
payload = {"url": WEBHOOK_URL, "secret_token": WEBHOOK_SECRET}

with httpx.Client(timeout=30.0) as client:
    r = client.post(url, json=payload)
    print(r.status_code, r.text)
