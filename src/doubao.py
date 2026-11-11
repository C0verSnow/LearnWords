import os
import tempfile
import time

from src.content import parse_content, prompt
from src.session import read_session, restore_session


class LoginExpired(RuntimeError):
    pass


class Doubao:
    def __init__(self, config, headless=True, profile=None):
        from DrissionPage import ChromiumOptions, ChromiumPage

        self.config = config
        self.temp = tempfile.TemporaryDirectory(prefix="learnword-browser-") if profile is None else None
        options = ChromiumOptions().set_user_data_path(profile or self.temp.name)
        options.set_local_port(9222).headless(headless)
        options.set_argument("--no-sandbox")
        options.set_argument("--disable-dev-shm-usage")
        if os.getenv("CHROME_PATH"):
            options.set_browser_path(os.environ["CHROME_PATH"])
        self.page = ChromiumPage(options)

    def restore(self):
        self.page.get(self.config["url"])
        mode = os.getenv("SESSION_MODE", "none")
        if mode not in ("none", "cookies", "web_storage"):
            raise ValueError("SESSION_MODE 只能填 none、cookies 或 web_storage")
        if mode != "none":
            restore_session(self.page, read_session(), mode)
        self.check_login()

    def generate(self, word):
        self.page.get(self.config["url"])
        self.check_login()
        tab = self.page
        new_chat = tab.ele(self.config["new_chat"], timeout=10)
        if not new_chat:
            raise RuntimeError("未找到新建聊天按钮，请更新 new_chat 选择器")
        new_chat.click()
        # Keep the tab so an experimentally required sessionStorage survives new conversations.
        return self.wait_for_answer(tab, word)

    def wait_for_answer(self, tab, word):
        editor = tab.ele(self.config["input"], timeout=15)
        if not editor:
            raise LoginExpired("豆包输入框不可用，请检查登录和页面选择器")
        debug = os.getenv("LEARNWORDS_DEBUG") == "1"
        if debug:
            editors = tab.eles(self.config["input"], timeout=0)
            print("[DEBUG-lw-20261110] editors", len(editors),
                  [element.states.is_displayed for element in editors], flush=True)
        previous = [ele.text for ele in tab.eles(self.config["answer"], timeout=0)]
        editor.input(prompt(word))
        if debug:
            print("[DEBUG-lw-20261110] after-input-chars", len(editor.text), flush=True)
        send_button = tab.ele(self.config["send"], timeout=15)
        if not send_button:
            raise RuntimeError("未找到发送按钮，请更新 send 选择器")
        send_button.click()
        if debug:
            print("[DEBUG-lw-20261110] after-submit-chars",
                  [len(element.text) for element in tab.eles(self.config["input"], timeout=0)], flush=True)
            for control in tab.eles('css:[data-testid*="send"], [data-testid*="stop"]', timeout=0):
                print("[DEBUG-lw-20261110] send-control", control.tag,
                      control.attr("data-testid"), "visible", control.states.is_displayed,
                      "enabled", control.states.is_enabled, flush=True)
        deadline = time.monotonic() + self.config["timeout"]
        stable_since, last = time.monotonic(), ""
        parse_error = "not-attempted"
        while time.monotonic() < deadline:
            answers = tab.eles(self.config["answer"], timeout=0)
            text = answers[-1].text if answers else ""
            if text != last:
                stable_since, last = time.monotonic(), text
            busy = tab.ele(self.config["generating"], timeout=0)
            if text and text not in previous and not busy and time.monotonic() - stable_since >= 4:
                try:
                    return parse_content(text, word)
                except ValueError as error:
                    # A syntactically complete response is required even if streaming controls changed.
                    parse_error = str(error)
            time.sleep(1)
        if debug:
            body_text = tab.ele("tag:body").text
            print("[DEBUG-lw-20261110] timeout-state", "answers", len(answers),
                  "answer-chars", [len(element.text) for element in answers],
                  "editor-chars", [len(element.text) for element in tab.eles(self.config["input"], timeout=0)],
                  "busy", bool(busy),
                  "busy-visible", busy.states.is_displayed if busy else False,
                  "parse-error", parse_error, flush=True)
            print("[DEBUG-lw-20261110] page-signals",
                  {term: term in body_text for term in ("验证码", "访问受限", "发送失败", "网络异常", "重新登录")},
                  flush=True)
        raise TimeoutError("豆包未在时限内返回完整内容")

    def check_login(self):
        if not self.page.ele(self.config["authenticated"], timeout=15):
            if os.getenv("LEARNWORDS_DEBUG") == "1":
                print("[DEBUG-lw-20261110] login-state", "avatars",
                      len(self.page.eles('css:[data-testid="chat_header_avatar_button"]', timeout=0)),
                      "account-menus", len(self.page.eles('css:[data-sidebar-footer-account-menu]', timeout=0)),
                      "login-buttons", len(self.page.eles('xpath://button[normalize-space(.)="登录"]', timeout=0)),
                      "html-chars", len(self.page.html), flush=True)
            raise LoginExpired("豆包登录未确认，请重新登录并检查 authenticated 选择器")

    def close(self):
        self.page.quit()
        if self.temp:
            self.temp.cleanup()
