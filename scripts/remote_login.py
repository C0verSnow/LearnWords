"""Inspect the remote login form using DrissionPage's generated ini settings."""
import json
from pathlib import Path

from src.config import load_config
from src.doubao import Doubao


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
        fields = [{"tag": element.tag, "type": element.attr("type"),
                   "placeholder": element.attr("placeholder"),
                   "role": element.attr("role"),
                   "checked": element.attr("aria-checked")}
                  for element in page.eles('css:input, [role="checkbox"]', timeout=10)
                  if element.states.is_displayed]
        buttons = [element.text for element in page.eles('tag:button', timeout=0)
                   if element.states.is_displayed]
        agreements = [{"title": element.text, "url": element.attr("href")}
                      for element in page.eles('tag:a', timeout=0)
                      if any(term in element.text for term in ("协议", "政策"))]
        print("LOGIN_FORM " + json.dumps({"fields": fields, "buttons": buttons,
                                          "agreements": agreements}, ensure_ascii=False), flush=True)
    finally:
        browser.close()


if __name__ == "__main__":
    main()
