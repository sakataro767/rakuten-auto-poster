"""
楽天ウェブサービス「商品検索API」から商品データを取得するモジュール。
公式ドキュメント: https://webservice.rakuten.co.jp/documentation/ichiba-item-search

【2026年API移行対応】
2026年2月〜5月の楽天API仕様変更により、以下が変更されている。
- エンドポイントのドメインが app.rakuten.co.jp → openapi.rakuten.co.jp/ichibams/api に変更
- applicationId に加えて accessKey が必須パラメータとして追加された
- Origin / Referer ヘッダーが必須（アプリ登録時の「アプリケーションURL」と一致させる）
"""
import os
import requests
import random

SEARCH_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"


def search_items(keyword=None, genre_id=None, min_price=None, max_price=None,
                  hits=30, page=1, sort="-updateTimestamp"):
    """
    楽天市場から条件に合う商品を検索して返す。

    Returns: list[dict] 商品情報のリスト（生のAPIレスポンスのItem部分）
    """
    app_id = os.environ["RAKUTEN_APP_ID"]
    access_key = os.environ["RAKUTEN_ACCESS_KEY"]
    affiliate_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "")
    # アプリ登録時に「アプリケーションURL」欄に入力したURLと同じものを指定する
    site_url = os.environ.get("RAKUTEN_SITE_URL", "")

    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "affiliateId": affiliate_id,
        "keyword": keyword,
        "genreId": genre_id,
        "minPrice": min_price,
        "maxPrice": max_price,
        "hits": hits,
        "page": page,
        "sort": sort,
        "imageFlag": 1,  # 画像がある商品のみ
        "format": "json",
    }
    # None の項目は送らない
    params = {k: v for k, v in params.items() if v not in (None, "")}

    headers = {}
    if site_url:
        headers["Origin"] = site_url
        headers["Referer"] = site_url

    resp = requests.get(SEARCH_ENDPOINT, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    return [item["Item"] for item in data.get("Items", [])]


def pick_random_item(items, exclude_item_codes=None):
    """まだ投稿していない商品をランダムに1件選ぶ（重複投稿防止用）"""
    exclude_item_codes = exclude_item_codes or set()
    candidates = [i for i in items if i["itemCode"] not in exclude_item_codes]
    if not candidates:
        return None
    return random.choice(candidates)


def get_affiliate_url(item):
    """アフィリエイトリンクを取得（affiliateUrlが空の場合は通常URLにフォールバック）"""
    return item.get("affiliateUrl") or item.get("itemUrl")


if __name__ == "__main__":
    # 動作確認用
    from dotenv import load_dotenv
    load_dotenv()
    items = search_items(
        keyword=os.environ.get("RAKUTEN_SEARCH_KEYWORD", "掃除機"),
        min_price=os.environ.get("RAKUTEN_MIN_PRICE"),
        max_price=os.environ.get("RAKUTEN_MAX_PRICE"),
        hits=5,
    )
    for item in items:
        print(item["itemName"], item["itemPrice"], get_affiliate_url(item))
