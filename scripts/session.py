import argparse
import os
import time
from pathlib import Path

from src.config import load_config
from src.doubao import Doubao, LoginExpired
from src.session import export_session, save_profile


def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="人工登录与会话恢复实验，不输出凭据")
    parser.add_argument("action", choices=("capture", "probe"))
    parser.add_argument("--profile", help="包含 ini 和用户目录的独立实验目录")
    args = parser.parse_args()
    directory = Path(args.profile or ".session/doubao-browser")
    browser = Doubao(config["doubao"], headless=args.action == "probe",
                      profile=directory / "profile" if args.action == "capture" else None,
                      ini_path=directory / "chrome.ini" if args.action == "capture" else None)
    try:
        if args.action == "capture":
            browser.page.get(config["doubao"]["url"])
            input("请在浏览器登录豆包，确认可以发消息后按回车：")
            browser.check_login()
            export_session(browser.page, Path(os.getenv("SESSION_FILE", ".session/doubao.json")))
            browser.close()
            browser = None
            save_profile(directory)
            print("ini 和完整用户目录已保存至私有 Supabase。")
        else:
            started = time.monotonic()
            if os.getenv("BROWSER_PROXY"):
                browser.page.get("https://www.cloudflare.com/cdn-cgi/trace")
                if "loc=HK" not in browser.page.ele("tag:body").text.splitlines():
                    raise RuntimeError("Chrome 的真实出口不是香港，停止豆包探测")
                print("Chrome exit country HK confirmed.", flush=True)
            browser.restore()
            browser.generate("approach")
            print(f"登录恢复及完整内容查询通过，用时 {time.monotonic() - started:.1f} 秒。")
    except (TimeoutError, LoginExpired):
        from scripts.remote_login import snapshot, storage

        storage("POST", "probe/doubao-diagnostic.json", {
            "mode": os.getenv("SESSION_MODE", "profile"), **snapshot(browser.page)})
        print("Probe failed; page diagnostic saved privately.", flush=True)
        raise
    finally:
        if browser is not None:
            browser.close()


if __name__ == "__main__":
    main()
