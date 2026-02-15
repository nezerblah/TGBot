import os
import requests
import json

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

if not BOT_TOKEN or not WEBHOOK_URL:
    print('Missing BOT_TOKEN or WEBHOOK_URL')
    exit(1)

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
# use JSON body and set secret_token so Telegram will include the header X-Telegram-Bot-Api-Secret-Token
payload = {"url": WEBHOOK_URL}
if WEBHOOK_SECRET:
    payload["secret_token"] = WEBHOOK_SECRET

r = requests.post(url, json=payload)
print(r.status_code, r.text)
