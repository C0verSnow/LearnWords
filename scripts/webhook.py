import argparse

import requests

from src.config import load_config, required_env


def main():
    load_config()
    parser = argparse.ArgumentParser(description="从当前仓库 .env 读取配置并注册 Telegram Webhook")
    parser.add_argument("url")
    args = parser.parse_args()
    if not args.url.startswith("https://"):
        parser.error("Webhook 需要 https 地址")
    try:
        response = requests.post(f"https://api.telegram.org/bot{required_env('TELEGRAM_BOT_TOKEN')}/setWebhook",
                                 json={"url": args.url, "secret_token": required_env("TELEGRAM_WEBHOOK_SECRET"),
                                       "allowed_updates": ["message"]}, timeout=20)
        success = response.ok and response.json().get("ok")
    except (requests.RequestException, ValueError):
        success = False
    if not success:
        raise SystemExit("Webhook 注册失败，请检查配置与网络。")
    print("Webhook 注册成功。")


if __name__ == "__main__":
    main()
