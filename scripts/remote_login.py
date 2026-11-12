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
from src.doubao import Doubao
from src.session import save_profile
from src.network import verify_browser_exit


def main():
    config = load_config()["doubao"]
    directory = Path(".session/doubao-browser")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    browser = Doubao(config, profile=directory / "profile", ini_path=directory / "chrome.ini")
    try:
        page = browser.page
        verify_browser_exit(page)
        page.get(config["url"])
        if not page.ele(config["authenticated"], timeout=3):
            page.ele('xpath://button[normalize-space(.)="登录"]', timeout=20).click()
            phone_login = page.ele('text:手机号登录', timeout=10)
            if phone_login:
                phone_login.click()
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
                target = control_target(page, command)
                apply_command(target, config, command)
                time.sleep(2)
                storage("POST", prefix + "/status.json", {"phase": "waiting", "last_action": action,
                                                           "target": snapshot(target) if target is not page else None,
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


def control_target(page, command):
    tab_id = command.get("tab_id")
    if tab_id is not None:
        if not isinstance(tab_id, str) or not tab_id:
            raise ValueError("Invalid tab identifier")
        page = page.browser.get_tab(tab_id)
    frame = command.get("frame")
    if frame is not None:
        if not isinstance(frame, str) or not frame:
            raise ValueError("Invalid frame selector")
        page = page.get_frame(frame)
    return page


def apply_command(page, config, command):
    action = command.get("action")
    if action == "credentials":
        user, password = command.get("user"), command.get("password")
        if not isinstance(user, str) or not user or not isinstance(password, str) or not password:
            raise ValueError("Invalid credentials")
        user_field = page.ele(config["login_user"])
        fill_field(user_field, user)
        password_field = page.ele(config["login_password"])
        fill_field(password_field, password)
        if user_field.value != user or password_field.value != password:
            raise RuntimeError("Login fields did not match private input")
        if command.get("submit") is True:
            page.ele(config["login_submit"]).click()
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
            fill_field(element, value)
    elif action == "point":
        point = command.get("point")
        if (not isinstance(point, list) or len(point) != 2
                or any(not isinstance(value, int) or value < 0 for value in point)):
            raise ValueError("Invalid page point")
        page.actions.move_to(tuple(point)).click()
    elif action == "navigate":
        path = command.get("path")
        if path not in ("/", "/chat/"):
            raise ValueError("Unsupported Doubao path")
        page.get("https://www.doubao.com" + path)
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
    editors = page.run_js("""
        return [...document.querySelectorAll('[contenteditable="true"]')].map(e => ({
          tag:e.tagName, class:e.className, role:e.getAttribute('role'),
          testid:e.getAttribute('data-testid'), textLength:e.innerText.length,
          focused:e===document.activeElement, visible:!!e.getClientRects().length}));
    """)
    body = redact_phone(page.ele("tag:body").text)
    signals = {term: term in body for term in ("验证码", "验证失败", "操作频繁", "拖动", "滑块", "安全验证")}
    frames = [{"id": frame.attr("id"), "name": frame.attr("name"), "title": frame.attr("title"),
               "src": (frame.attr("src") or "").split("?")[0], "style": frame.attr("style"),
               "displayed": frame.states.is_displayed}
              for frame in page.get_frames(timeout=0)]
    tabs = [{"id": tab.tab_id, "url": tab.url.split("?")[0], "title": tab.title}
            for tab in page.browser.get_tabs()]
    return {"url": page.url.split("?")[0], "fields": fields, "editors": editors, "controls": controls, "signals": signals,
            "frames": frames, "tabs": tabs,
            "notice": body, "screenshot": base64.b64encode(page.get_screenshot(as_bytes="png")).decode()}


def fill_field(element, value):
    from DrissionPage.common import Keys

    element.run_js("this.focus(); this.select();")
    element.owner.actions.type(Keys.BACKSPACE)
    element.input(value)


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
