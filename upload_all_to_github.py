import base64
import io
import os
import sys
from pathlib import Path

# Windows環境での文字化け・絵文字UnicodeEncodeError(cp932)防止
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from config import BASE_DIR, GITHUB_REPO, GITHUB_TOKEN


# アップロード対象の拡張子やファイル
INCLUDE_EXTS = {".py", ".html", ".md", ".txt", ".yml", ".yaml"}
EXCLUDE_DIRS = {".venv", ".git", "__pycache__", "scratch", ".system_generated"}
EXCLUDE_FILES = {".env"}  # .env はセキュリティ保護のため絶対に除外


def get_existing_tree(headers, repo, branch="main"):
    """GitHubリポジトリの既存ファイル一覧とSHAを取得"""
    url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        tree = resp.json().get("tree", [])
        return {item["path"]: item["sha"] for item in tree if item["type"] == "blob"}
    return {}


def upload_project():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[Error] .env ファイルに GITHUB_TOKEN と GITHUB_REPO を設定してください。")
        return

    print(f"==================================================")
    print(f"🚀 GitHub リポジトリへプロジェクト一括アップロード開始")
    print(f"ターゲット: {GITHUB_REPO}")
    print(f"==================================================")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 1. リポジトリの存在確認
    repo_url = f"https://api.github.com/repos/{GITHUB_REPO}"
    repo_resp = requests.get(repo_url, headers=headers)
    if repo_resp.status_code == 404:
        print(f"[Error] リポジトリ '{GITHUB_REPO}' が見つかりません。")
        print("GitHub上で事前にリポジトリを作成してください。")
        return
    elif repo_resp.status_code != 200:
        print(f"[Error] GitHub API エラー: {repo_resp.status_code} - {repo_resp.text}")
        return

    # 2. 対象ファイルの収集
    files_to_upload = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f in EXCLUDE_FILES:
                continue
            path = Path(root) / f
            if path.suffix.lower() in INCLUDE_EXTS or f in ["LICENSE", "Procfile"]:
                rel_path = path.relative_to(BASE_DIR).as_posix()
                files_to_upload.append((path, rel_path))

    print(f"-> アップロード対象ファイル数: {len(files_to_upload)} 件")

    # 3. アップロード実行 (既存ファイルのSHAを取得して更新)
    for idx, (local_path, rel_path) in enumerate(files_to_upload, start=1):
        file_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{rel_path}"
        sha = None

        # 既存SHAの確認
        get_res = requests.get(file_url, headers=headers)
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")

        content_bytes = local_path.read_bytes()
        content_b64 = base64.b64encode(content_bytes).decode("utf-8")

        payload = {
            "message": f"Sync {rel_path}",
            "content": content_b64,
        }
        if sha:
            payload["sha"] = sha

        put_res = requests.put(file_url, headers=headers, json=payload)
        if put_res.status_code in [200, 201]:
            print(f"  [{idx}/{len(files_to_upload)}] [OK] {rel_path}")
        else:
            print(f"  [{idx}/{len(files_to_upload)}] [FAIL] {rel_path} (HTTP {put_res.status_code})")

    print("\n==================================================")
    print("🎉 プロジェクトの一括アップロードが完了しました！")
    print("==================================================")


if __name__ == "__main__":
    upload_project()
