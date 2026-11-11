"""Keep one remote login browser alive; exchange inputs through private storage."""
import json
import os
import re
import time
import uuid
from pathlib import Path

import requests

from src.config import load_config
from src.doubao import Doubao
from src.session import export_session


def main():
    config = load_config()["doubao"]
    directory = Path(".session")
    directory.mkdir(mode=0o700, exist_ok=True)
    browser = Doubao(config, ini_path=directory / "remote-login.ini")
    try:
        page = browser.page
        page.get(config["url"])
        page.ele('xpath://button[normalize-space(.)="登录"]', timeout=20).click()
        phone_login = page.ele('text:手机号登录', timeout=10)
        if phone_login:
            phone_login.click()
        login_id = os.getenv("LOGIN_ID", "")
        if not login_id:
            print("LOGIN_FORM " + json.dumps(snapshot(page), ensure_ascii=False), flush=True)
            return
        uuid.UUID(login_id)
        prefix = "login/" + login_id
        storage("POST", prefix + "/status.json", {"phase": "ready", **snapshot(page)})
        print("Remote login browser ready; private controls only.", flush=True)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            command = storage("GET", prefix + "/command.json")
            if command is None:
                time.sleep(2)
                continue
            storage("DELETE", prefix + "/command.json")
            action = command.get("action")
            if action == "phone":
                value = command.get("value", "")
                if not isinstance(value, str) or not re.fullmatch(r"1[0-9]{10}", value):
                    raise ValueError("Invalid phone input")
                page.ele('css:input[placeholder="请输入手机号"]').input(value, clear=True)
            elif action == "agree":
                checkbox = page.ele('css:[role="checkbox"]')
                if checkbox.attr("aria-checked") != "true":
                    checkbox.click()
            elif action == "click":
                label = command.get("label")
                if label not in ("下一步", "获取验证码", "发送验证码", "登录", "验证并登录"):
                    raise ValueError("Unsupported login button")
                page.ele('xpath://button[normalize-space(.)="' + label + '"]', timeout=10).click()
            elif action == "code":
                value = command.get("value", "")
                if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4,8}", value):
                    raise ValueError("Invalid verification code")
                page.ele('css:input[placeholder*="验证码"]', timeout=10).input(value, clear=True)
            elif action != "inspect":
                raise ValueError("Unsupported login action")
            time.sleep(2)
            if page.ele(config["authenticated"], timeout=0):
                path = directory / "doubao.json"
                export_session(page, path)
                storage("POST", os.getenv("SUPABASE_SESSION_OBJECT", "doubao.json"),
                        json.loads(path.read_text()))
                storage("POST", prefix + "/status.json", {"phase": "saved"})
                print("Remote login completed; session saved privately.", flush=True)
                return
            storage("POST", prefix + "/status.json", {"phase": "waiting", **snapshot(page)})
        storage("POST", prefix + "/status.json", {"phase": "timeout"})
        raise TimeoutError("Remote login waiting window ended")
    except Exception as error:
        # Browser exceptions can include sensitive input arguments; report only their class.
        print("Remote login stopped: " + type(error).__name__, flush=True)
        raise SystemExit(1) from None
    finally:
        browser.close()


def snapshot(page):
    fields = [{"type": element.attr("type"), "placeholder": element.attr("placeholder")}
              for element in page.eles('tag:input', timeout=0) if element.states.is_displayed]
    buttons = [element.text for element in page.eles('tag:button', timeout=0)
               if element.states.is_displayed]
    agreements = [{"checked": element.attr("aria-checked"), "text": element.parent().text}
                  for element in page.eles('css:[role="checkbox"]', timeout=0)
                  if element.states.is_displayed]
    body = page.ele("tag:body").text
    signals = {term: term in body for term in ("重新获取", "验证码已发送", "验证码错误", "验证失败",
                                              "操作频繁", "拖动", "滑块", "安全验证")}
    return {"fields": fields, "buttons": buttons, "agreements": agreements, "signals": signals}


def storage(method, key, data=None):
    base = os.environ["SUPABASE_URL"].rstrip("/") + "/storage/v1/object/"
    bucket = os.getenv("SUPABASE_SESSION_BUCKET", "browser-sessions")
    headers = {"Authorization": "Bearer " + os.environ["SUPABASE_SERVICE_ROLE_KEY"],
               "apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"], "x-upsert": "true"}
    if method == "DELETE":
        response = requests.delete(base + bucket, headers=headers, json={"prefixes": [key]}, timeout=20)
    else:
        url = base + ("authenticated/" if method == "GET" else "") + bucket + "/" + key
        response = requests.request(method, url, headers=headers, json=data, timeout=20)
    if method == "GET" and (response.status_code == 404 or
                            (response.status_code == 400 and response.json().get("statusCode") == "404")):
        return None
    if not response.ok:
        raise RuntimeError("Private storage request failed")
    return response.json()


if __name__ == "__main__":
    main()
