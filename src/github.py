import base64
import json
from urllib.parse import quote

import requests


class GitHubError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"GitHub 请求失败（HTTP {status}）")


class GitHub:
    def __init__(self, token, repository, ref="main", api_url="https://api.github.com"):
        self.repository = repository
        self.ref = ref
        self.base = f"{api_url}/repos/{repository}"
        self.http = requests.Session()
        self.http.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def request(self, method, path, **kwargs):
        try:
            response = self.http.request(method, self.base + path, timeout=20, **kwargs)
        except requests.RequestException:
            raise GitHubError(503) from None
        if not response.ok:
            raise GitHubError(response.status_code)
        return response.json() if response.content else None

    def read_file(self, path):
        data = self.request("GET", f"/contents/{path}", params={"ref": self.ref})
        return json.loads(base64.b64decode(data["content"])), data["sha"]

    def write_file(self, path, value, sha=None):
        payload = {
            "message": "Record Telegram card request",
            "branch": self.ref,
            "content": base64.b64encode(json.dumps(value).encode()).decode(),
        }
        if sha:
            payload["sha"] = sha
        return self.request("PUT", f"/contents/{path}", json=payload)

    def claim(self, request_id, payload):
        path = f"docs/requests/{request_id}.json"
        try:
            self.write_file(path, payload)
            return True
        except GitHubError as error:
            if error.status not in (409, 422):
                raise
            # A contents conflict only counts as a duplicate if this exact request exists.
            self.read_file(path)
            return False

    def dispatch(self, inputs):
        return self.request("POST", "/actions/workflows/make-cards.yml/dispatches",
                            json={"ref": self.ref, "inputs": inputs})

    def latest_status(self, chat_id):
        runs = self.request("GET", "/actions/workflows/make-cards.yml/runs",
                            params={"per_page": 100, "branch": self.ref})["workflow_runs"]
        for run in runs:
            if run["display_title"].endswith(f"chat-{chat_id}"):
                return f"任务状态：{run['conclusion'] or run['status']}\n{run['html_url']}"
        return "还没有这个聊天的制卡任务。"

    def latest_release(self):
        try:
            release = self.request("GET", "/releases/latest")
            return release["html_url"]
        except GitHubError as error:
            if error.status == 404:
                return "还没有发布卡包。"
            raise

    def find_release(self, task_id):
        try:
            return self.request("GET", f"/releases/tags/{quote(f'learnword-{task_id}', safe='')}")
        except GitHubError as error:
            if error.status != 404:
                raise
            return None

    def download_asset(self, task_id, path):
        release = self.find_release(task_id)
        if release is None or release["draft"]:
            raise GitHubError(404)
        asset = next((asset for asset in release["assets"] if asset["name"] == path.name), None)
        if asset is None:
            raise GitHubError(404)
        try:
            with self.http.get(f"{self.base}/releases/assets/{asset['id']}",
                               headers={"Accept": "application/octet-stream"},
                               stream=True, timeout=120) as response:
                if not response.ok:
                    raise GitHubError(response.status_code)
                with path.open("wb") as stream:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        stream.write(chunk)
        except requests.RequestException:
            raise GitHubError(503) from None

    def publish(self, task_id, files, body, commit):
        release = self.find_release(task_id)
        if release is None:
            release = self.request("POST", "/releases", json={
                "tag_name": f"learnword-{task_id}", "target_commitish": commit, "name": f"LearnWord {task_id}",
                "body": body, "draft": True,
            })
        assets = {asset["name"]: asset for asset in release["assets"]}
        if not release["draft"]:
            return release["html_url"]
        for path in files:
            if path.name in assets:
                self.request("DELETE", f"/releases/assets/{assets[path.name]['id']}")
            upload_url = release["upload_url"].split("{")[0]
            try:
                with path.open("rb") as stream:
                    response = self.http.post(upload_url, params={"name": path.name}, data=stream,
                                              headers={"Content-Type": "application/octet-stream"},
                                              timeout=120)
            except requests.RequestException:
                raise GitHubError(503) from None
            if not response.ok:
                raise GitHubError(response.status_code)
        release = self.request("PATCH", f"/releases/{release['id']}", json={"draft": False})
        return release["html_url"]
