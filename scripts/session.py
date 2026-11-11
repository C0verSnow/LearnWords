import argparse
import io
import os
import tarfile
import tempfile
import time
from pathlib import Path

import requests

from src.config import load_config, required_env
from src.doubao import Doubao, LoginExpired
from src.session import restore_profile, save_profile


def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="人工登录与会话恢复实验，不输出凭据")
    parser.add_argument("action", choices=("capture", "probe", "migrate"))
    parser.add_argument("--profile", help="包含 ini 和完整用户目录的独立实验目录")
    args = parser.parse_args()
    if args.action == "migrate":
        migrate_legacy_profile()
        return
    directory = Path(args.profile or ".session/doubao-browser")
    browser = Doubao(config["doubao"],
                     profile=directory / "profile" if args.action == "capture" else None,
                     ini_path=directory / "chrome.ini" if args.action == "capture" else None)
    try:
        if args.action == "capture":
            browser.page.get(config["doubao"]["url"])
            input("请在浏览器登录豆包，确认可以发消息后按回车：")
            browser.check_login()
            browser.close()
            browser = None
            save_profile(directory)
            print("ini 和完整用户目录已加密保存至私有 Supabase。")
        else:
            started = time.monotonic()
            browser.restore()
            print("Doubao login restore confirmed.", flush=True)
            browser.page.listen.start("completion", method="POST")
            browser.generate("approach")
            print(f"登录恢复及完整内容查询通过，用时 {time.monotonic() - started:.1f} 秒。")
    except (TimeoutError, LoginExpired):
        from scripts.remote_login import snapshot, storage

        storage("POST", "probe/doubao-diagnostic.json", {
            "mode": os.getenv("SESSION_MODE", "profile"), **snapshot(browser.page),
            "completion": completion_status(browser.page)})
        print("Probe failed; page diagnostic saved privately.", flush=True)
        raise
    finally:
        if browser is not None:
            browser.close()


def migrate_legacy_profile():
    url = (required_env("SUPABASE_URL").rstrip("/") + "/storage/v1/object/authenticated/"
           + os.getenv("SUPABASE_SESSION_BUCKET", "browser-sessions") + "/doubao-profile.tar.gz")
    try:
        response = requests.get(url, headers={
            "Authorization": "Bearer " + required_env("SUPABASE_SERVICE_ROLE_KEY"),
            "apikey": required_env("SUPABASE_SERVICE_ROLE_KEY"),
        }, timeout=120)
    except requests.RequestException:
        raise RuntimeError("旧浏览器目录下载失败") from None
    if not response.ok:
        raise RuntimeError(f"旧浏览器目录下载失败（HTTP {response.status_code}）")
    with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as restored:
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
            archive.extractall(source, filter="data")
        save_profile(source)
        restore_profile(restored)
        source_files = {p.relative_to(source): p.read_bytes() for p in Path(source).rglob("*") if p.is_file()}
        restored_files = {p.relative_to(restored): p.read_bytes() for p in Path(restored).rglob("*") if p.is_file()}
        if source_files != restored_files:
            raise RuntimeError("加密迁移后的回读不一致，请保留旧对象排查")
    print("旧 profile 已加密迁移并回读核对一致；旧对象保留，登录有效性仍须独立 Probe。", flush=True)


def completion_status(page):
    results = []
    for packet in page.listen.steps(timeout=1):
        body = "" if packet.is_failed else str(packet.response.body)
        results.append({"network_failed": packet.is_failed,
                        "http_status": None if packet.is_failed else packet.response.status,
                        "stream_error": "STREAM_ERROR" in body,
                        "error_710022004": "710022004" in body,
                        "rate_limited": "rate limited" in body,
                        "semantic_verification": "semantic_reasoning" in body})
    return results


if __name__ == "__main__":
    main()
