import argparse
import os
from pathlib import Path

from src.config import load_config
from src.doubao import Doubao
from src.session import export_session


def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="人工登录与会话恢复实验，不输出凭据")
    parser.add_argument("action", choices=("capture", "probe"))
    parser.add_argument("--profile", help="仅本机比较用户目录；不要提交或公开上传这个目录")
    args = parser.parse_args()
    browser = Doubao(config["doubao"], headless=args.action == "probe", profile=args.profile)
    try:
        if args.action == "capture":
            browser.page.get(config["doubao"]["url"])
            input("请在弹出的浏览器人工登录豆包，确认可以发消息后按回车：")
            browser.check_login()
            export_session(browser.page, Path(os.getenv("SESSION_FILE", ".session/doubao.json")))
            print("会话已写入忽略目录；请用全新浏览器分别测试 cookies 和 web_storage。")
        else:
            browser.restore()
            browser.generate("approach")
            print("本次恢复及消息查询通过；不代表跨系统或后续会话必定有效。")
    except TimeoutError:
        from scripts.remote_login import storage

        storage("POST", "probe/diagnostic.json", {
            "body": browser.page.ele("tag:body").text,
            "elements": [{"id": element.attr("data-testid"), "tag": element.tag,
                          "text": element.text}
                         for element in browser.page.eles('css:[data-testid]', timeout=0)],
        })
        print("[DEBUG-query] Query timed out; diagnostic saved privately.", flush=True)
        raise
    finally:
        browser.close()


if __name__ == "__main__":
    main()
