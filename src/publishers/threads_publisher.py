import io
import sys
import time
from typing import Any, Dict, Optional, Tuple

if sys.platform == "win32" and sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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

    def publish_image(self, text: str, image_url: str) -> Optional[str]:
        """画像付き投稿をThreadsに公開 (処理完了を待機後公開。失敗時は自動でテキスト投稿へフォールバック)"""
        if not self.is_configured:
            print("[Threads] エラー: THREADS_ACCESS_TOKEN が未設定です。")
            return None

        # ユーザーIDが未確定なら先に取得
        if not self.user_id:
            profile = self.get_user_profile()
            if not profile or not self.user_id:
                print("[Threads] エラー: ユーザーIDを取得できませんでした。")
                return None

        print(f"[Threads] 画像付き投稿処理を開始します (ユーザーID: {self.user_id})...")
        print(f"[Threads] 添付画像URL: {image_url}")

        # Step 1: メディアコンテナ作成 (IMAGE)
        create_url = f"{self.BASE_URL}/{self.user_id}/threads"
        create_payload = {
            "media_type": "IMAGE",
            "image_url": image_url,
            "text": text,
            "access_token": self.access_token,
        }

        try:
            c_resp = requests.post(create_url, data=create_payload, timeout=25)
            c_data = c_resp.json()

            if c_resp.status_code != 200 or "id" not in c_data:
                print(f"[Threads] 画像コンテナ作成に失敗しました: {c_data}")
                print("[Threads] -> テキストのみの投稿へフォールバックします...")
                return self.publish_text(text)

            creation_id = c_data["id"]
            print(f"[Threads] 画像コンテナ作成成功 (creation_id: {creation_id})")

            # Step 2: Metaサーバー側での画像処理待機 (ステータスポーリング: 最大30秒)
            status_url = f"{self.BASE_URL}/{creation_id}"
            is_ready = False
            for attempt in range(1, 11):
                time.sleep(3)
                try:
                    s_resp = requests.get(
                        status_url,
                        params={"fields": "status,error_message", "access_token": self.access_token},
                        timeout=15,
                    )
                    s_data = s_resp.json()
                    status = s_data.get("status")
                    if status == "FINISHED":
                        is_ready = True
                        break
                    elif status == "ERROR":
                        print(f"[Threads] 画像処理エラー: {s_data.get('error_message')}")
                        print("[Threads] -> テキストのみの投稿へフォールバックします...")
                        return self.publish_text(text)
                    elif status == "IN_PROGRESS":
                        print(f"[Threads] 画像処理中... (確認 {attempt}/10)")
                except Exception as poll_err:
                    print(f"[Threads] ステータス確認一時警告: {poll_err}")

            if not is_ready:
                print("[Threads] 処理待機がタイムアウトしたため、テキストのみの投稿へフォールバックします...")
                return self.publish_text(text)

            # Step 3: 投稿を公開 (threads_publish)
            publish_url = f"{self.BASE_URL}/{self.user_id}/threads_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token,
            }

            p_resp = requests.post(publish_url, data=publish_payload, timeout=20)
            p_data = p_resp.json()

            if p_resp.status_code == 200 and "id" in p_data:
                post_id = p_data["id"]
                print(f"[Threads] 🎉 画像付き投稿が正常に公開されました！ (Post ID: {post_id})")
                return post_id
            else:
                print(f"[Threads] 画像投稿の公開に失敗しました: {p_data}")
                print("[Threads] -> テキストのみの投稿へフォールバックします...")
                return self.publish_text(text)

        except Exception as e:
            print(f"[Threads] 画像投稿処理中に例外が発生しました: {e}")
            print("[Threads] -> テキストのみの投稿へフォールバックします...")
            return self.publish_text(text)

    def publish(self, text: str, image_url: Optional[str] = None) -> Optional[str]:
        """画像URLがあれば画像付きで、なければテキストのみでThreadsへ投稿"""
        if image_url:
            return self.publish_image(text=text, image_url=image_url)
        return self.publish_text(text=text)

    def publish_reply(self, parent_post_id: str, text: str) -> Optional[str]:
        """指定された親ポストにぶら下げるリプライ（ツリー投稿）を公開"""
        if not self.is_configured:
            print("[Threads] エラー: THREADS_ACCESS_TOKEN が未設定です。")
            return None

        # ユーザーIDが未確定なら先に取得
        if not self.user_id:
            profile = self.get_user_profile()
            if not profile or not self.user_id:
                print("[Threads] エラー: ユーザーIDを取得できませんでした。")
                return None

        print(f"[Threads] リプライ投稿処理を開始します (親Post ID: {parent_post_id})...")

        create_url = f"{self.BASE_URL}/{self.user_id}/threads"
        create_payload = {
            "media_type": "TEXT",
            "text": text,
            "reply_to_id": parent_post_id,
            "access_token": self.access_token,
        }

        try:
            c_resp = requests.post(create_url, data=create_payload, timeout=20)
            c_data = c_resp.json()

            if c_resp.status_code != 200 or "id" not in c_data:
                print(f"[Threads] リプライコンテナ作成に失敗しました: {c_data}")
                return None

            creation_id = c_data["id"]
            print(f"[Threads] リプライコンテナ作成成功 (creation_id: {creation_id})")

            # Threads側の処理待ち (2秒待機)
            time.sleep(2)

            publish_url = f"{self.BASE_URL}/{self.user_id}/threads_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token,
            }

            p_resp = requests.post(publish_url, data=publish_payload, timeout=20)
            p_data = p_resp.json()

            if p_resp.status_code == 200 and "id" in p_data:
                reply_id = p_data["id"]
                print(f"[Threads] 🎉 リプライが正常に公開されました！ (Reply ID: {reply_id})")
                return reply_id
            else:
                print(f"[Threads] リプライ公開に失敗しました: {p_data}")
                return None

        except Exception as e:
            print(f"[Threads] リプライ投稿処理中に例外が発生しました: {e}")
            return None

    def publish_thread(
        self,
        post1_text: str,
        post2_text: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        2段階ツリー投稿を実行:
        1通目（親ポスト: 画像付きまたはテキスト）を公開後、
        2通目（リプライ: 事業化考察＋公式リンク案内）を自動でぶら下げて投稿。
        """
        # Step 1: 親ポストの投稿
        parent_id = self.publish(text=post1_text, image_url=image_url)
        if not parent_id:
            return None, None

        if not post2_text:
            return parent_id, None

        # Step 2: Meta側のDB反映を待機 (4秒)
        print("[Threads] 親ポスト反映待ち (4秒待機後、2通目リプライを自動投稿)...")
        time.sleep(4)

        reply_id = self.publish_reply(parent_post_id=parent_id, text=post2_text)
        return parent_id, reply_id
