import base64
from pathlib import Path
from typing import Optional
import requests
from config import GITHUB_REPO, GITHUB_TOKEN


class GitHubUploader:
    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.repo = repo or GITHUB_REPO

    def upload_file(self, file_path: Path, target_path: str = "index.html", commit_message: str = "Update dashboard") -> bool:
        """GitHub REST API を使用してファイルをリポジトリにアップロード（Gitインストール不要）"""
        if not self.token or not self.repo:
            print("[Info] GitHub Token or Repo is not configured. Skipping GitHub upload.")
            return False

        url = f"https://api.github.com/repos/{self.repo}/contents/{target_path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # 既存ファイルのSHAを取得（更新に必須）
        sha = None
        try:
            get_resp = requests.get(url, headers=headers, timeout=15)
            if get_resp.status_code == 200:
                sha = get_resp.json().get("sha")
        except Exception as e:
            print(f"[Warning] Could not get existing file SHA from GitHub: {e}")

        # コンテンツをBase64エンコード
        content_bytes = file_path.read_bytes()
        content_b64 = base64.b64encode(content_bytes).decode("utf-8")

        payload = {
            "message": commit_message,
            "content": content_b64,
        }
        if sha:
            payload["sha"] = sha

        try:
            put_resp = requests.put(url, headers=headers, json=payload, timeout=20)
            if put_resp.status_code in [200, 201]:
                print(f"[Success] Successfully uploaded {target_path} to GitHub: {self.repo}")
                return True
            else:
                print(f"[Error] Failed to upload to GitHub: HTTP {put_resp.status_code} - {put_resp.text}")
                return False
        except Exception as e:
            print(f"[Error] Exception during GitHub upload: {e}")
            return False
