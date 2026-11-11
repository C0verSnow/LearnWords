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
from src.session import save_profile


def main():
    config = load_config()["deepseek"]
    login_id = os.getenv("LOGIN_ID", "")
    if login_id:
        uuid.UUID(login_id)
    prefix = "login/" + login_id
    directory = Path(".session/deepseek-browser")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    browser = DeepSeek(config, profile=directory / "profile", ini_path=directory / "chrome.ini")
    try:
        page = browser.page
        page.get(config["url"])
        if not login_id:
            state = snapshot(page)
            print("LOGIN_FORM " + json.dumps({key: state[key] for key in ("fields", "buttons")},
                                              ensure_ascii=False), flush=True)
            return
        storage("POST", prefix + "/status.json", {"phase": "ready", **snapshot(page)})
        print("Remote login browser ready; private controls only.", flush=True)
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            if page.ele(config["authenticated"], timeout=0):
                # Chrome must flush its databases before the full profile is archived.
                browser.close()
                browser = None
                save_profile(directory)
                storage("POST", prefix + "/status.json", {"phase": "saved"})
                print("Remote login completed; ini and profile saved privately.", flush=True)
                return
            command = storage("GET", prefix + "/command.json")
            if command is None:
                time.sleep(2)
                continue
            storage("DELETE", prefix + "/command.json")
            action = command.get("action")
            if action == "credentials":
                user, password = command.get("user"), command.get("password")
                if not isinstance(user, str) or not user or not isinstance(password, str) or not password:
                    raise ValueError("Invalid credentials")
                page.ele(config["login_user"]).input(user, clear=True)
                page.ele(config["login_password"]).input(password, clear=True)
            elif action == "submit":
                page.ele(config["login_submit"]).click()
            elif action == "point":
                point = command.get("point")
                if (not isinstance(point, list) or len(point) != 2
                        or any(not isinstance(value, int) or value < 0 for value in point)):
                    raise ValueError("Invalid page point")
                page.actions.move_to(tuple(point)).click()
            elif action != "inspect":
                raise ValueError("Unsupported login action")
            time.sleep(2)
            storage("POST", prefix + "/status.json", {"phase": "waiting", "last_action": action,
                                                       **snapshot(page)})
        storage("POST", prefix + "/status.json", {"phase": "timeout"})
        raise TimeoutError("Remote login waiting window ended")
    except Exception as error:
        # Browser exceptions can include sensitive input arguments; report only their class.
        print("Remote login stopped: " + type(error).__name__, flush=True)
        if login_id:
            storage("POST", prefix + "/status.json", {"phase": "failed", "error": type(error).__name__})
        raise SystemExit(1) from None
    finally:
        if browser is not None:
            browser.close()


def snapshot(page):
    fields = [{"type": element.attr("type"), "placeholder": element.attr("placeholder"),
               "value_length": len(element.value or "")}
              for element in page.eles('tag:input', timeout=0) if element.states.is_displayed]
    buttons = [element.text for element in page.eles('tag:button', timeout=0)
               if element.states.is_displayed]
    body = re.sub(r"1[0-9]{10}", "[phone]", page.ele("tag:body").text)
    return {"fields": fields, "buttons": buttons, "notice": body,
            "screenshot": base64.b64encode(page.get_screenshot(as_bytes="png")).decode()}


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
