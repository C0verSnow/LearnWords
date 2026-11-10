import json
import os
import threading
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from src.content import FIELDS
from src.doubao import Doubao
from src.session import export_session


class BrowserPage(BaseHTTPRequestHandler):
    def do_GET(self):
        content = {"Word": "approach", **dict.fromkeys(FIELDS, "An example. 中文说明。")}
        page = """<!doctype html><meta charset="utf-8">
        <div id="account">test account</div><button id="new">new chat</button>
        <textarea></textarea><pre id="answer"></pre>
        <script>
        document.querySelector('#new').onclick = () => {
          document.querySelector('#answer').textContent = '';
        };
        document.querySelector('textarea').onkeydown = event => {
          if (event.key === 'Enter') {
            event.preventDefault();
            document.querySelector('#answer').textContent = RESPONSE;
          }
        };
        </script>""".replace("RESPONSE", json.dumps(json.dumps(content, ensure_ascii=False)))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode())

    def log_message(self, *args):
        pass


class BrowserTests(unittest.TestCase):
    def test_chrome_query_and_storage_restore_in_fresh_profile(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), BrowserPage)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = {"url": f"http://127.0.0.1:{server.server_port}/", "timeout": 20,
                  "input": "css:textarea", "answer": "css:#answer", "authenticated": "css:#account",
                  "new_chat": "css:#new", "generating": "css:#not-generating"}
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "session.json"
                with patch.dict(os.environ, {"SESSION_MODE": "none", "SUPABASE_URL": ""}):
                    browser = Doubao(config)
                    try:
                        browser.restore()
                        browser.page.set.local_storage("local-probe", "value")
                        browser.page.set.session_storage("session-probe", "value")
                        browser.page.set.cookies([{"name": "probe", "value": "ok", "domain": "127.0.0.1", "path": "/"}])
                        export_session(browser.page, path)
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
