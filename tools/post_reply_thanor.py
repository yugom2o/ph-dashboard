import sys
from pathlib import Path

# パスの追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.publishers import ThreadsPublisher
from src.storage import Database

def main():
    db = Database()
    publisher = ThreadsPublisher()

    product_id = "thanorai"
    parent_post_id = "17968022529178904"

    post1_text = (
        "海外で話題の最新ツール「Thanor AI」を日本向けにアレンジ！\n\n"
        "AIでサクッと作った安っぽいLPを、一瞬で「日本企業が信頼する高級感あるデザイン」に自動ブラッシュアップ。\n\n"
        "日本のWeb制作の常識が変わる、AI時代の必須コーディング支援SaaSの勝機とは？\n\n"
        "#AIツール #Web制作 #SaaS #起業"
    )

    post2_text = (
        "🇯🇵 日本市場でのタイムマシン事業チャンス\n\n"
        "💡 コンセプト: 【Web制作会社・フリーランス向け】AI生成したチープなLPコードを取り込むだけで、日本のBtoB/BtoC商習慣に即した高級感あるデザインに自動リファインし即納品できるコーディング支援SaaS\n"
        "🎯 ターゲット: 日本のWeb制作会社、インハウスマーケター、フリーランスエンジニア\n"
        "🚀 勝機: Cursorやv0等で生成されたコードを取り込み、国内ビジネスで好まれる安心感ある配色・日本語フォント・余白設計に自動変換。\n\n"
        "🔗 公式サイト: https://thanor.ai/"
    )

    image_url = "https://ph-files.imgix.net/60d63dc0-cf89-4176-a672-f58e4c010c37.png?auto=format&format=jpeg&fit=crop&frame=1&h=512&w=1024"

    print(f"親ポスト {parent_post_id} に対するリプライを投稿中...")
    reply_id = publisher.publish_reply(parent_post_id=parent_post_id, text=post2_text)

    if reply_id:
        # DBに記録
        db.record_threads_post(
            product_id=product_id,
            post_id=parent_post_id,
            text=post1_text,
            image_url=image_url,
            reply_post_id=reply_id,
            reply_text=post2_text,
        )
        print(f"🎉 リプライ投稿＆DB記録完了！ (Reply ID: {reply_id})")
    else:
        print("❌ リプライ投稿失敗")

if __name__ == "__main__":
    main()
