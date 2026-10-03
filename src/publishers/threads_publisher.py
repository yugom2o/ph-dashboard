import time
from typing import Any, Dict, Optional
import requests
from config import THREADS_ACCESS_TOKEN, THREADS_USER_ID


class ThreadsPublisher:
    BASE_URL = "https://graph.threads.net/v1.0"

    def __init__(
        self,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.access_token = access_token or THREADS_ACCESS_TOKEN
        self.user_id = user_id or THREADS_USER_ID
        self.username = None

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """アカウント情報の取得＆トークンの疎通確認"""
        if not self.is_configured:
            print("[Threads] エラー: THREADS_ACCESS_TOKEN が設定されていません。")
            return None

        url = f"{self.BASE_URL}/me"
        params = {
            "fields": "id,username,name,threads_profile_picture_url",
            "access_token": self.access_token,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()

            if resp.status_code == 200 and "id" in data:
                self.user_id = data["id"]
                self.username = data.get("username")
                return data
            else:
                print(f"[Threads] プロフィール取得失敗: {data}")
                return None
        except Exception as e:
            print(f"[Threads] 通信エラー: {e}")
            return None

    def publish_text(self, text: str) -> Optional[str]:
        """テキストをThreadsに投稿 (成功時は投稿IDを返却)"""
        if not self.is_configured:
            print("[Threads] エラー: THREADS_ACCESS_TOKEN が未設定です。")
            return None

        # ユーザーIDが未確定なら先に取得
        if not self.user_id:
            profile = self.get_user_profile()
            if not profile or not self.user_id:
                print("[Threads] エラー: ユーザーIDを取得できませんでした。")
                return None

        print(f"[Threads] 投稿処理を開始します (ユーザーID: {self.user_id})...")

        # Step 1: メディアコンテナ作成 (TEXT)
        create_url = f"{self.BASE_URL}/{self.user_id}/threads"
        create_payload = {
            "media_type": "TEXT",
            "text": text,
            "access_token": self.access_token,
        }

        try:
            c_resp = requests.post(create_url, data=create_payload, timeout=20)
            c_data = c_resp.json()

            if c_resp.status_code != 200 or "id" not in c_data:
                print(f"[Threads] コンテナ作成に失敗しました: {c_data}")
                return None

            creation_id = c_data["id"]
            print(f"[Threads] コンテナ作成成功 (creation_id: {creation_id})")

            # Threads側の処理待ち (2秒待機)
            time.sleep(2)

            # Step 2: 投稿を公開 (threads_publish)
            publish_url = f"{self.BASE_URL}/{self.user_id}/threads_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token,
            }

            p_resp = requests.post(publish_url, data=publish_payload, timeout=20)
            p_data = p_resp.json()

            if p_resp.status_code == 200 and "id" in p_data:
                post_id = p_data["id"]
                print(f"[Threads] 🎉 投稿が正常に公開されました！ (Post ID: {post_id})")
                return post_id
            else:
                print(f"[Threads] 公開に失敗しました: {p_data}")
                return None

        except Exception as e:
            print(f"[Threads] 投稿処理中に例外が発生しました: {e}")
            return None
