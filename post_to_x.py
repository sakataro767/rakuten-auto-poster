"""
X (Twitter) API v2 へ自動投稿するモジュール。
投稿には OAuth 1.0a User Context 認証が必要（tweepyが対応）。

事前準備:
1. https://developer.x.com/ でアプリを作成
2. アプリの権限を "Read and Write" に設定
3. Consumer Keys / Access Token & Secret を発行
4. console.x.com で従量課金クレジット($5〜)をチャージ
   （2026年時点で新規アカウントは無料枠が使えないため必須）
"""
import os
import tweepy


def get_client():
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def post_tweet(text, image_path=None):
    """
    テキスト（+任意で画像1枚）を投稿する。
    画像を付ける場合は v1.1 API（メディアアップロード用）も必要。
    """
    client = get_client()

    media_ids = None
    if image_path:
        auth = tweepy.OAuth1UserHandler(
            os.environ["X_API_KEY"],
            os.environ["X_API_SECRET"],
            os.environ["X_ACCESS_TOKEN"],
            os.environ["X_ACCESS_TOKEN_SECRET"],
        )
        api_v1 = tweepy.API(auth)
        media = api_v1.media_upload(image_path)
        media_ids = [media.media_id]

    response = client.create_tweet(text=text, media_ids=media_ids)
    return response


def post_tweet_thread(main_text, reply_text, image_path=None):
    """
    ツリー投稿：①URLなしの本文を投稿 → ②その投稿へのリプライとしてURLを投稿。
    X APIの課金体系（URL付き投稿が高額）を回避するための方式。

    Returns: dict {"main": <本文の投稿結果>, "reply": <リプライの投稿結果>}
    """
    client = get_client()

    main_result = post_tweet(main_text, image_path=image_path)
    main_tweet_id = main_result.data["id"]

    reply_result = client.create_tweet(
        text=reply_text,
        in_reply_to_tweet_id=main_tweet_id,
    )

    return {"main": main_result, "reply": reply_result}


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = post_tweet_thread(
        main_text="動作確認テスト投稿です。",
        reply_text="これはリプライのテストです。https://example.com",
    )
    print(result)
