import os

import requests

HELP = "/make <数量> [next|random]：制卡\n/status：任务状态\n/release：最新卡包\n/help：帮助"
API_URL = "https://api.telegram.org"


def send_message(token, chat_id, text):
    try:
        response = requests.post(f"{API_URL}/bot{token}/sendMessage",
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


def send_document(token, chat_id, path):
    try:
        if path.stat().st_size > 50_000_000:
            raise RuntimeError("文件超过 Telegram 50 MB 上传上限")
        with path.open("rb") as stream:
            response = requests.post(f"{API_URL}/bot{token}/sendDocument",
                                     data={"chat_id": chat_id},
                                     files={"document": (path.name, stream, "application/octet-stream")},
                                     timeout=120)
        if not response.ok or not response.json().get("ok"):
            raise RuntimeError("Telegram 文件发送失败")
    except (OSError, requests.RequestException, ValueError):
        raise RuntimeError("Telegram 文件发送失败") from None
