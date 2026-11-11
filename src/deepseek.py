import os
import tempfile
import time
from pathlib import Path

from src.content import parse_content, prompt
from src.session import read_session, restore_profile, restore_session


class LoginExpired(RuntimeError):
    pass


class DeepSeek:
    def __init__(self, config, headless=False, profile=None, ini_path=None):
        from DrissionPage import ChromiumOptions, ChromiumPage

        self.config = config
        self.temp = tempfile.TemporaryDirectory(prefix="learnword-browser-") if profile is None else None
        if profile is None and os.getenv("SESSION_MODE") == "profile":
            directory = Path(self.temp.name)
            restore_profile(directory)
            profile, ini_path = directory / "profile", directory / "chrome.ini"
        options = (ChromiumOptions(ini_path=str(ini_path))
                   if ini_path and Path(ini_path).exists() else ChromiumOptions())
        options.set_user_data_path(str(profile or self.temp.name))
        options.set_local_port(9222).headless(headless)
        options.set_argument("--no-sandbox")
        options.set_argument("--window-size=1440,1000")
        if os.getenv("MIHOMO_TUN") == "1":
            options.set_argument("--no-proxy-server")
        elif os.getenv("BROWSER_PROXY"):
            options.set_proxy(os.environ["BROWSER_PROXY"])
        if os.getenv("CHROME_PATH"):
            options.set_browser_path(os.environ["CHROME_PATH"])
        if ini_path:
            options.save(str(ini_path))
            options = ChromiumOptions(ini_path=str(ini_path))
        self.page = ChromiumPage(options)

    def restore(self):
        self.page.get(self.config["url"])
        mode = os.getenv("SESSION_MODE", "none")
        if mode not in ("none", "cookies", "web_storage", "profile"):
            raise ValueError("SESSION_MODE 只能填 none、cookies、web_storage 或 profile")
        if mode in ("cookies", "web_storage"):
            restore_session(self.page, read_session(), mode)
        self.check_login()

    def generate(self, word):
        self.page.get(self.config["url"])
        self.check_login()
        tab = self.page
        if self.config.get("new_chat"):
            new_chat = tab.ele(self.config["new_chat"], timeout=10)
            if not new_chat:
                raise RuntimeError("未找到新建聊天按钮，请更新 new_chat 选择器")
            new_chat.click()
        return self.wait_for_answer(tab, word)

    def wait_for_answer(self, tab, word):
        editor = tab.ele(self.config["input"], timeout=15)
        if not editor:
            raise LoginExpired("DeepSeek输入框不可用，请检查登录和页面选择器")
        previous = [ele.text for ele in tab.eles(self.config["answer"], timeout=0)]
        editor.input(prompt(word))
        if self.config.get("send"):
            send_button = tab.ele(self.config["send"], timeout=15)
            if not send_button:
                raise RuntimeError("未找到发送按钮，请更新 send 选择器")
            send_button.click()
        else:
            from DrissionPage.common import Keys

            editor.input(Keys.ENTER)
        deadline = time.monotonic() + self.config["timeout"]
        stable_since, last = time.monotonic(), ""
        while time.monotonic() < deadline:
            if self.config.get("failed") and tab.ele(self.config["failed"], timeout=0):
                raise LoginExpired("DeepSeek发送失败，请检查网络出口或页面验证后再重试")
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
        raise TimeoutError("DeepSeek未在时限内返回完整内容")

    def check_login(self):
        if not self.page.ele(self.config["authenticated"], timeout=15):
            raise LoginExpired("DeepSeek登录未确认，请重新登录并检查 authenticated 选择器")

    def close(self):
        self.page.quit()
        if self.temp:
            self.temp.cleanup()
