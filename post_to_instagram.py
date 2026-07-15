"""
Instagram Graph API（Content Publishing API）へ自動投稿するモジュール。

事前準備:
1. Instagramアカウントを「プロアカウント（ビジネス）」に切り替え
2. Facebookページと連携
3. Meta for Developersでアプリを作成し、Instagramビジネスアカウント連携
4. 長期の Page Access Token を発行

制約:
- 画像は事前に公開URLとしてアクセス可能な状態にしておく必要がある
  （ローカル画像を直接アップロードすることはできない）
- キャプション内のURLはリンクとして機能しない
  → 「詳細はプロフィールのリンクから」という誘導文にするのが定石
"""
import os
import time
import requests

GRAPH_BASE = "https://graph.facebook.com/v21.0"


def post_image(image_url, caption):
    """
    公開されている画像URLとキャプションを渡してInstagramに投稿する。
    2段階：①メディアコンテナ作成 → ②公開(publish)
    """
    access_token = os.environ["IG_ACCESS_TOKEN"]
    ig_user_id = os.environ["IG_BUSINESS_ACCOUNT_ID"]

    # ① メディアコンテナを作成
    create_resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    if not create_resp.ok:
        # エラーの詳細（Metaが返す具体的な原因）をそのまま例外メッセージに含める
        raise RuntimeError(f"メディアコンテナ作成に失敗: {create_resp.status_code} {create_resp.text}")
    creation_id = create_resp.json()["id"]

    # 処理完了を少し待つ（画像取得・エンコードに数秒かかることがある）
    time.sleep(3)

    # ② 公開する
    publish_resp = requests.post(
        f"{GRAPH_BASE}/{ig_user_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": access_token,
        },
        timeout=30,
    )
    if not publish_resp.ok:
        raise RuntimeError(f"公開処理に失敗: {publish_resp.status_code} {publish_resp.text}")
    return publish_resp.json()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = post_image(
        image_url="https://example.com/sample.jpg",
        caption="動作確認テスト投稿です。",
    )
    print(result)
