"""Inspect DeepSeek access through TUN without submitting account credentials."""
import json
import os
import tempfile
import time
from urllib.parse import urlsplit

from DrissionPage import ChromiumOptions, ChromiumPage

from scripts.remote_login import snapshot, storage
from src.config import load_config


def main():
    load_config()
    with tempfile.TemporaryDirectory(prefix="learnword-deepseek-access-") as directory:
        options = ChromiumOptions(read_file=False)
        options.set_user_data_path(directory).set_local_port(9222).headless(False)
        options.set_argument("--no-sandbox")
        options.set_argument("--window-size=1440,1000")
        options.set_argument("--no-proxy-server")
        options.set_browser_path(os.environ["CHROME_PATH"])
        page = ChromiumPage(options)
        try:
            page.get("https://www.cloudflare.com/cdn-cgi/trace")
            if "loc=HK" not in page.ele("tag:body").text.splitlines():
                raise RuntimeError("Chrome 的 TUN 出口不是香港")
            print("Chrome TUN exit country HK confirmed.", flush=True)
            results = [inspect_page(page, path) for path in ("/", "/sign_in")]
            storage("POST", "probe/deepseek-access.json", {"results": results, **snapshot(page)})
            print("DeepSeek access inspection completed; private page diagnostic saved.", flush=True)
        finally:
            page.quit()


def inspect_page(page, path):
    page.listen.start("chat.deepseek.com")
    page.get("https://chat.deepseek.com" + path)
    time.sleep(8)
    body = page.ele("tag:body").text
    documents = [{"path": urlsplit(packet.url).path,
                  "status": None if packet.is_failed else packet.response.status,
                  "network_failed": packet.is_failed}
                 for packet in page.listen.steps(timeout=1)
                 if urlsplit(packet.url).path in ("/", "/sign_in")]
    result = {
        "requested_path": path, "final_path": urlsplit(page.url).path,
        "title": page.title, "documents": documents,
        "password_field": bool(page.ele('css:input[type="password"]', timeout=0)),
        "chat_input": bool(page.ele("tag:textarea", timeout=0)),
        "cloudfront_block": "403" in body and "cloudfront" in body.lower(),
        "browser_challenge": any(text in (page.title + " " + body).lower()
                                 for text in ("just a moment", "checking your browser", "verify you are human")),
    }
    print("DEEPSEEK_ACCESS " + json.dumps(result, ensure_ascii=False), flush=True)
    return result


if __name__ == "__main__":
    main()
