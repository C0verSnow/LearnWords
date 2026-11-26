import os
import time
from pathlib import Path

from src.content import parse_content, prompt
from src.config import ROOT
from src.network import verify_browser_exit
from src.session import read_session, restore_profile, restore_session, save_profile


class LoginExpired(RuntimeError):
    pass


class ChatInputUnavailable(RuntimeError):
    pass


class Doubao:
    def __init__(self, config, headless=False, profile=None, ini_path=None):
        from DrissionPage import ChromiumOptions, ChromiumPage

        self.config = config
        self.directory = Path(os.getenv("BROWSER_DIRECTORY", ".session/doubao-browser")).resolve()
        self.persist = False
        if profile is None and os.getenv("SESSION_MODE") == "profile":
            restore_profile(self.directory)
            profile, ini_path = self.directory / "profile", self.directory / "chrome.ini"
        profile = Path(profile or self.directory / "profile").resolve()
        ini_path = Path(ini_path or self.directory / "chrome.ini").resolve()
        profile.mkdir(mode=0o700, parents=True, exist_ok=True)
        options = ChromiumOptions(ini_path=str(ini_path if ini_path.exists() else ROOT / "configs/dp.ini"))
        options.set_user_data_path(str(profile))
        options.set_local_port(9222).headless(headless)
        options.set_argument("--no-sandbox")
        options.set_argument("--window-size=1440,1000")
        options.set_argument("--no-first-run")
        options.remove_argument("--proxy-server")
        options.set_argument("--no-proxy-server")
        # Linux runners have no shared desktop keyring; encryption at rest is handled by the archive.
        options.set_argument("--password-store=basic")
        if os.getenv("CHROME_PATH"):
            options.set_browser_path(os.environ["CHROME_PATH"])
        options.save(str(ini_path))
        options = ChromiumOptions(ini_path=str(ini_path))
        self.page = ChromiumPage(options)

    def restore(self):
        if os.getenv("TS_EXIT_NODE"):
            verify_browser_exit(self.page)
        self.page.get(self.config["url"])
        self._wait_page_ready(self.page)
        mode = os.getenv("SESSION_MODE", "none")
        if mode not in ("none", "cookies", "web_storage", "profile"):
            raise ValueError("SESSION_MODE 只能填 none、cookies、web_storage 或 profile")
        if mode in ("cookies", "web_storage"):
            restore_session(self.page, read_session(), mode)
        self.check_login()
        self.persist = mode == "profile"

    def generate(self, word, *, reopen=False):
        if reopen:
            url = self.config["url"]
            if self.page.url == url:
                self.page.refresh()
            else:
                self.page.get(url)
            self._wait_page_ready(self.page)
        self.check_login()
        tab = self.page
        if self.config.get("new_chat"):
            self._click_new_chat(tab)
            self._wait_page_ready(tab)
        return self.wait_for_answer(tab, word)

    def wait_for_answer(self, tab, word):
        from DrissionPage.common import Keys
        from DrissionPage.errors import ElementLostError

        for attempt in range(3):
            editor = self.find_chat_input(tab)
            previous = [ele.text for ele in tab.eles(self.config["answer"], timeout=0)]
            try:
                editor.click()
                if editor.tag == "textarea":
                    editor.run_js("this.select();")
                else:
                    # DrissionPage's Ctrl+A clear can retain contenteditable drafts; select only this editor.
                    editor.run_js("""this.focus();
                        const range = document.createRange(); range.selectNodeContents(this);
                        const selection = window.getSelection();
                        selection.removeAllRanges(); selection.addRange(range);""")
                tab.actions.type(Keys.BACKSPACE)
                editor.input(prompt(word))
                break
            except ElementLostError:
                if attempt == 2:
                    raise
                time.sleep(0.5)
        if self.config.get("send"):
            self._click_send(tab)
        else:
            editor.input(Keys.ENTER)
        deadline = time.monotonic() + self.config["timeout"]
        stable_since, last = time.monotonic(), ""
        while time.monotonic() < deadline:
            if self.config.get("failed") and tab.ele(self.config["failed"], timeout=0):
                raise LoginExpired("豆包发送失败，请检查网络出口或页面验证后再重试")
            answers = tab.eles(self.config["answer"], timeout=0)
            text = answers[-1].text if answers else ""
            if text != last:
                stable_since, last = time.monotonic(), text
            busy = tab.ele(self.config["generating"], timeout=0)
            if text and text not in previous and not busy and time.monotonic() - stable_since >= 4:
                try:
                    return parse_content(text, word)
                except ValueError:
                    pass
            time.sleep(1)
        raise TimeoutError("豆包未在时限内返回完整内容")

    def find_chat_input(self, tab):
        from DrissionPage.errors import ElementLostError

        selectors = [self.config["input"], *self.config.get("input_fallbacks", [])]
        deadline = time.monotonic() + self.config.get("page_timeout", 30)
        while time.monotonic() < deadline:
            for selector in selectors:
                for editor in tab.eles(selector, timeout=0):
                    try:
                        if editor.states.has_rect and editor.states.is_displayed and editor.states.is_enabled:
                            return editor
                    except ElementLostError:
                        continue
            time.sleep(0.25)
        raise ChatInputUnavailable("豆包输入框不可用，请检查页面加载和输入框选择器")

    def _wait_page_ready(self, tab, timeout=None):
        deadline = time.monotonic() + (timeout or self.config.get("page_timeout", 30))
        while time.monotonic() < deadline:
            try:
                if tab.run_js("return document.readyState") == "complete":
                    break
            except Exception:
                pass
            time.sleep(0.2)
        settle = self.config.get("render_settle", 1.0)
        if settle > 0:
            time.sleep(settle)

    def _click_new_chat(self, tab):
        from DrissionPage.errors import ElementLostError

        page_timeout = self.config.get("page_timeout", 30)
        deadline = time.monotonic() + page_timeout
        while time.monotonic() < deadline:
            remaining = max(0.5, deadline - time.monotonic())
            new_chat = tab.ele(self.config["new_chat"], timeout=remaining)
            if not new_chat:
                break
            try:
                new_chat.click()
                return
            except ElementLostError:
                time.sleep(0.25)
        raise RuntimeError("未找到新建聊天按钮，请更新 new_chat 选择器")

    def _click_send(self, tab):
        from DrissionPage.errors import ElementLostError

        page_timeout = self.config.get("page_timeout", 30)
        deadline = time.monotonic() + page_timeout
        found = False
        while time.monotonic() < deadline:
            send_button = tab.ele(self.config["send"], timeout=0)
            if send_button:
                found = True
                try:
                    ready = (send_button.states.is_displayed
                             and send_button.states.is_enabled
                             and send_button.attr("aria-disabled") != "true")
                    if ready and send_button.click(timeout=max(1, deadline - time.monotonic())):
                        return
                except ElementLostError:
                    pass
            time.sleep(0.25)
        if not found:
            raise RuntimeError("未找到发送按钮，请更新 send 选择器")
        raise RuntimeError("豆包发送按钮未就绪，消息未发送，请稍后重跑任务")

    def check_login(self):
        body = self.page.ele("tag:body").text
        for message in ("受区域限制", "当前地区暂不支持", "访问过于频繁"):
            if message in body:
                self.persist = False
                raise LoginExpired("豆包页面提示：" + message)
        if not self.page.ele(self.config["authenticated"], timeout=self.config.get("page_timeout", 30)):
            self.persist = False
            raise LoginExpired("豆包登录未确认，请重新登录并检查 authenticated 选择器")

    def close(self):
        self.page.quit()
        if self.persist:
            save_profile(self.directory)
