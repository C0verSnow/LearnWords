import os

import requests

HELP = "/make <数量> [next|random]：制卡\n/status：任务状态\n/release：最新卡包\n/help：帮助"


def send_message(token, chat_id, text):
    try:
        response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                 json={"chat_id": chat_id, "text": text[:4000]}, timeout=15)
        if not response.ok or not response.json().get("ok"):
            raise RuntimeError("Telegram 通知失败")
    except (requests.RequestException, ValueError):
        raise RuntimeError("Telegram 通知失败") from None


def notify(chat_id, text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        return
    try:
        send_message(token, chat_id, text)
    except RuntimeError:
        print("Telegram 通知失败；请查看 Actions 和 Release。", flush=True)
