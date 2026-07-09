import os
import requests


def send_telegram_alert(company: str, title: str, url: str, reasoning: str = ""):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(f"[NO TELEGRAM CONFIGURED] Would have alerted: {company} - {title} - {url}")
        return

    text = f"🆕 *{title}*\n🏢 {company}\n{('💡 ' + reasoning) if reasoning else ''}\n🔗 {url}"
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    if not resp.ok:
        print(f"Telegram send failed: {resp.status_code} {resp.text}")
