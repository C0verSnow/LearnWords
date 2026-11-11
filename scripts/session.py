import argparse
import io
import os
import tarfile
import tempfile
import time
import json
from urllib.parse import urlsplit
from pathlib import Path

import requests

from scripts.tailscale_split import target_addresses
from src.config import load_config, required_env
from src.doubao import Doubao
from src.session import restore_profile, save_profile


def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="人工登录与会话恢复实验，不输出凭据")
    parser.add_argument("action", choices=("capture", "probe", "migrate", "domains"))
    parser.add_argument("--profile", help="包含 ini 和完整用户目录的独立实验目录")
    args = parser.parse_args()
    if args.action == "migrate":
        migrate_legacy_profile()
        return
    if args.action == "domains":
        inspect_page_domains(config["doubao"])
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
            browser.page.listen.start(("www.doubao.com", "accounts.doubao.com", "mssdk.bytedance.com"), method="POST")
            browser.restore()
            print("Doubao login restore confirmed.", flush=True)
            browser.generate("approach")
            print(f"登录恢复及完整内容查询通过，用时 {time.monotonic() - started:.1f} 秒。")
    except (TimeoutError, RuntimeError):
        from scripts.remote_login import snapshot, storage

        storage("POST", "probe/doubao-diagnostic.json", {
            "mode": os.getenv("SESSION_MODE", "profile"), **snapshot(browser.page),
            "network": request_status(browser.page)})
        print("Probe failed; page diagnostic saved privately.", flush=True)
        raise
    finally:
        if browser is not None:
            browser.close()


def inspect_page_domains(config):
    directory = Path(".session/domain-observation")
    browser = Doubao(config, profile=directory / "profile", ini_path=directory / "chrome.ini")
    try:
        browser.page.listen.start(True)
        browser.page.get(config["url"])
        time.sleep(15)
        hosts = {}
        for packet in browser.page.listen.steps(timeout=1):
            host = urlsplit(packet.url).hostname
            if not host:
                continue
            hosts.setdefault(host, set()).add("failed" if packet.is_failed else str(packet.response.status))
        print("豆包匿名页面实际请求域名与状态（无路径、正文或凭据）：", flush=True)
        print(json.dumps({host: sorted(statuses) for host, statuses in sorted(hosts.items())}, ensure_ascii=False), flush=True)
    finally:
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
        archived_files = save_profile(source)
        restore_profile(restored)
        source_files = {path: (Path(source) / path).read_bytes() for path in archived_files}
        restored_files = {p.relative_to(restored): p.read_bytes() for p in Path(restored).rglob("*") if p.is_file()}
        if source_files != restored_files:
            raise RuntimeError("加密迁移后的回读不一致，请保留旧对象排查")
    print("旧 profile 已加密迁移并回读核对一致；旧对象保留，登录有效性仍须独立 Probe。", flush=True)


def request_status(page):
    targets = target_addresses()
    pending = [{"host": urlsplit(packet.url).hostname, "path": urlsplit(packet.url).path,
                "completion": "completion" in urlsplit(packet.url).path}
               for packet in list(page.listen._request_ids.values())]
    results = []
    for packet in page.listen.steps(count=200, timeout=1):
        response = packet._raw_response or {}
        body = None if packet.is_failed else packet.response.body
        code = next((body[key] for key in ("code", "status_code", "statusCode", "error_code")
                     if isinstance(body.get(key), int)), None) if isinstance(body, dict) else None
        results.append({"host": urlsplit(packet.url).hostname, "path": urlsplit(packet.url).path,
                        "network_failed": packet.is_failed,
                        "http_status": response.get("status"), "code": code,
                        "error": (packet._raw_fail_info or {}).get("errorText"),
                        "protocol": response.get("protocol"), "ip": response.get("remoteIPAddress"),
                        "worker": response.get("fromServiceWorker", False),
                        "cached": response.get("fromDiskCache", False),
                        "in_target_set": response.get("remoteIPAddress") in targets,
                        "send_gate": status_fields(body) if urlsplit(packet.url).path == "/im/message/send_rate_limit" else None})
    return {"completed": results, "inflight": pending}


def status_fields(value):
    # Rate decisions can contain verification credentials; retain only status data.
    if isinstance(value, dict):
        return {key: status_fields(item) for key, item in value.items()}
    if isinstance(value, list):
        return [status_fields(item) for item in value[:10]]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if value in ("verify", "normal", "allow", "deny", "semantic_reasoning", "doubao_message_web"):
        return value
    return {"string_length": len(value)}


if __name__ == "__main__":
    main()
