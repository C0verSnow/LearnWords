import json
import io
import os
import threading
import tempfile
import tarfile
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from src.content import FIELDS
from src.doubao import Doubao
from src.session import export_session, save_profile


class BrowserPage(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/storage/v1/object/authenticated/"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self.server.profile_archive)
            return
        content = {"Word": "approach", **dict.fromkeys(FIELDS, "An example. 中文说明。")}
        page = """<!doctype html><meta charset="utf-8">
        <div id="account">test account</div><button id="new">new chat</button>
        <div id="editor" contenteditable="true"></div><button id="send">send</button>
        <pre id="answer"></pre>
        <script>
        document.querySelector('#new').onclick = () => {
          document.querySelector('#answer').textContent = '';
        };
        document.querySelector('#editor').onkeydown = event => {
          if (event.key === 'Enter') {
            event.preventDefault();
          }
        };
        document.querySelector('#send').onclick = () => {
          document.querySelector('#answer').textContent = RESPONSE;
          document.querySelector('#editor').textContent = '';
        };
        </script>""".replace("RESPONSE", json.dumps(json.dumps(content, ensure_ascii=False)))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode())

    def do_POST(self):
        self.server.profile_archive = self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{}')

    def log_message(self, *args):
        pass


class BrowserTests(unittest.TestCase):
    def test_chrome_query_and_storage_restore_in_fresh_profile(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), BrowserPage)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = {"url": f"http://127.0.0.1:{server.server_port}/", "timeout": 20,
                  "input": "css:#editor", "send": "css:#send", "answer": "css:#answer", "authenticated": "css:#account",
                  "new_chat": "css:#new", "generating": "css:#not-generating"}
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "session.json"
                bundle = Path(directory) / "browser"
                bundle.mkdir()
                with patch.dict(os.environ, {"SESSION_MODE": "none", "SUPABASE_URL": ""}):
                    browser = Doubao(config, profile=bundle / "profile", ini_path=bundle / "chrome.ini")
                    try:
                        browser.restore()
                        browser.page.set.local_storage("local-probe", "value")
                        browser.page.set.session_storage("session-probe", "value")
                        browser.page.set.cookies([{"name": "probe", "value": "ok", "domain": "127.0.0.1", "path": "/", "expires": time.time() + 3600}])
                        export_session(browser.page, path)
                    finally:
                        browser.close()
                with patch.dict(os.environ, {"SESSION_MODE": "profile",
                                             "SUPABASE_URL": config["url"].rstrip("/"),
                                             "SUPABASE_SERVICE_ROLE_KEY": "test-key",
                                             "SUPABASE_SESSION_BUCKET": "browser-sessions",
                                             "SUPABASE_PROFILE_OBJECT": "doubao-profile.tar.gz"}):
                    cache = bundle / "profile/Default/Cache"
                    cache.mkdir(exist_ok=True)
                    (cache / "discard-me").write_text("Cached asset")
                    save_profile(bundle)
                    with tarfile.open(fileobj=io.BytesIO(server.profile_archive), mode="r:gz") as archive:
                        self.assertNotIn("./profile/Default/Cache/discard-me", archive.getnames())
                        self.assertIn("./chrome.ini", archive.getnames())
                    browser = Doubao(config)
                    try:
                        browser.restore()
                        self.assertTrue((Path(browser.temp.name) / "chrome.ini").is_file())
                        self.assertEqual(browser.page.local_storage("local-probe"), "value")
                        self.assertIn("probe", [cookie["name"] for cookie in browser.page.cookies()])
                        self.assertEqual(browser.generate("approach")["Word"], "approach")
                    finally:
                        browser.close()
                with patch.dict(os.environ, {"SESSION_MODE": "web_storage", "SESSION_FILE": str(path), "SUPABASE_URL": ""}):
                    browser = Doubao(config)
                    try:
                        browser.restore()
                        self.assertEqual(browser.page.local_storage("local-probe"), "value")
                        self.assertEqual(browser.page.session_storage("session-probe"), "value")
                        self.assertIn("probe", [cookie["name"] for cookie in browser.page.cookies()])
                        self.assertEqual(browser.generate("approach")["Word"], "approach")
                        self.assertEqual(browser.page.session_storage("session-probe"), "value")
                    finally:
                        browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
