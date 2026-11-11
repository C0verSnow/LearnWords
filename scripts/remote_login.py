"""Keep one remote login browser alive; exchange inputs through private storage."""
import base64
import json
import os
import re
import time
import uuid
from pathlib import Path

import requests

from src.config import load_config
from src.deepseek import DeepSeek
from src.session import export_session, save_profile


def main():
    config = load_config()["deepseek"]
    directory = Path(".session/deepseek-browser")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    browser = DeepSeek(config, profile=directory / "profile", ini_path=directory / "chrome.ini")
    try:
        page = browser.page
        page.get("https://www.cloudflare.com/cdn-cgi/trace")
        if "loc=HK" not in page.ele("tag:body").text.splitlines():
            raise RuntimeError("远端浏览器出口不是香港")
        print("Login Chrome TUN exit country HK confirmed.", flush=True)
        page.get(config["login_url"])
        login_id = os.getenv("LOGIN_ID", "")
        if not login_id:
            state = snapshot(page)
            print("LOGIN_FORM " + json.dumps({key: state[key] for key in ("fields", "controls")},
                                              ensure_ascii=False), flush=True)
            return
        uuid.UUID(login_id)
        prefix = "login/" + login_id
        storage("POST", prefix + "/status.json", {"phase": "ready", **snapshot(page)})
        print("Remote login browser ready; private controls only.", flush=True)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            if page.ele(config["authenticated"], timeout=0):
                state = snapshot(page)
                path = directory / "deepseek.json"
                export_session(page, path)
                storage("POST", os.getenv("SUPABASE_SESSION_OBJECT", "deepseek.json"),
                        json.loads(path.read_text()))
                # Chrome must flush its databases before the profile is archived.
                browser.close()
                browser = None
                save_profile(directory)
                storage("POST", prefix + "/status.json", {"phase": "saved", **state})
                print("Remote login completed; session saved privately.", flush=True)
                return
            command = storage("GET", prefix + "/command.json")
            if command is None:
                time.sleep(2)
                continue
            storage("DELETE", prefix + "/command.json")
            action = command.get("action")
            try:
                apply_command(page, config, command)
                time.sleep(2)
                storage("POST", prefix + "/status.json", {"phase": "waiting", "last_action": action,
                                                           **snapshot(page)})
            except Exception as error:
                storage("POST", prefix + "/status.json", {"phase": "waiting", "last_action": action,
                                                           "last_error": type(error).__name__, **snapshot(page)})
        storage("POST", prefix + "/status.json", {"phase": "timeout"})
        raise TimeoutError("Remote login waiting window ended")
    except Exception as error:
        # Browser exceptions can include sensitive input arguments; report only their class.
        print("Remote login stopped: " + type(error).__name__, flush=True)
        raise SystemExit(1) from None
    finally:
        if browser is not None:
            browser.close()


def apply_command(page, config, command):
    action = command.get("action")
    if action == "credentials":
        user, password = command.get("user"), command.get("password")
        if not isinstance(user, str) or not user or not isinstance(password, str) or not password:
            raise ValueError("Invalid credentials")
        page.ele(config["login_user"]).input(user, clear=True)
        page.ele(config["login_password"]).input(password, clear=True)
    elif action in ("click", "input", "account"):
        selector = command.get("selector")
        if not isinstance(selector, str) or not selector:
            raise ValueError("Invalid selector")
        element = page.ele(selector, timeout=10)
        if action == "click":
            element.click()
        elif action == "account":
            if not element or not element.states.is_displayed:
                raise ValueError("Account control unavailable")
            config["authenticated"] = selector
        else:
            value = command.get("value")
            if not isinstance(value, str):
                raise ValueError("Invalid input")
            element.input(value, clear=True)
    elif action == "point":
        point = command.get("point")
        if (not isinstance(point, list) or len(point) != 2
                or any(not isinstance(value, int) or value < 0 for value in point)):
            raise ValueError("Invalid page point")
        page.actions.move_to(tuple(point)).click()
    elif action != "inspect":
        raise ValueError("Unsupported login action")


def snapshot(page):
    fields = [{"type": element.attr("type"), "placeholder": element.attr("placeholder"),
               "class": element.attr("class"), "parent_class": element.parent().attr("class"),
               "parent_text": redact_phone(element.parent().text), "value_length": len(element.value or "")}
              for element in page.eles('tag:input', timeout=0) if element.states.is_displayed]
    controls = [{"tag": element.tag, "class": element.attr("class"), "role": element.attr("role"),
                 "id": element.attr("id"), "testid": element.attr("data-testid"),
                 "checked": element.attr("aria-checked"), "text": redact_phone(element.text)[:200]}
                for element in page.eles('css:button,[role],a,[tabindex],.ds-button,.ds-checkbox,[class*="select"]', timeout=0)
                if element.states.is_displayed][:150]
    body = redact_phone(page.ele("tag:body").text)
    signals = {term: term in body for term in ("验证码", "验证失败", "操作频繁", "拖动", "滑块", "安全验证")}
    return {"url": page.url.split("?")[0], "fields": fields, "controls": controls, "signals": signals,
            "notice": body, "screenshot": base64.b64encode(page.get_screenshot(as_bytes="png")).decode()}


def redact_phone(text):
    return re.sub(r"1[0-9]{10}", "[phone]", text)


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
