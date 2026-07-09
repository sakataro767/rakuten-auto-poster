"""
メイン実行スクリプト。
楽天商品を検索 → 未投稿の商品を1件選ぶ → 投稿文を生成 → X / Instagramへ投稿。

定期実行の例（cron, 毎日9時・18時に実行）:
    0 9,18 * * * cd /path/to/rakuten_auto_poster && /usr/bin/python3 main.py >> log.txt 2>&1

安全運用のポイント:
- いきなり全自動にせず、最初は DRY_RUN=True で生成結果だけ確認する
- 投稿済み商品はファイルに記録し、重複投稿を防ぐ
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

from rakuten_client import search_items, pick_random_item, get_affiliate_url
from caption_generator import (
    generate_x_caption,
    generate_x_reply,
    generate_instagram_caption,
    generate_original_tip_post,
)
import post_to_x
import post_to_instagram

load_dotenv()

POSTED_LOG = Path("posted_items.json")
TIP_LOG = Path("posted_tips.json")
KEYWORD_INDEX_LOG = Path("keyword_index.json")
LATEST_ITEM_LOG = Path("latest_item.json")

# どのプラットフォームに投稿するか
ENABLE_X = True
ENABLE_INSTAGRAM = False  # 画像を公開URLで用意できるようになったらTrueに

# 商品紹介ばかりだと「似たような投稿の繰り返し」でスパム判定されるリスクがあるため、
# N回に1回はオリジナルの節約Tips投稿（商品紹介なし）を挟む
POST_COUNT_LOG = Path("post_count.json")
ORIGINAL_TIP_EVERY_N = int(os.environ.get("ORIGINAL_TIP_EVERY_N", "3"))


def load_posted_codes():
    if POSTED_LOG.exists():
        return set(json.loads(POSTED_LOG.read_text()))
    return set()


def save_posted_code(item_code, posted):
    posted.add(item_code)
    POSTED_LOG.write_text(json.dumps(list(posted), ensure_ascii=False))


def save_latest_item(item, affiliate_url):
    """
    直近で投稿した商品の情報を保存する。
    リンクまとめページ(index.html)がこのファイルをfetchで読みに来て、
    「今日のおすすめ商品」の表示・リンクを自動更新するために使う。
    """
    import datetime
    data = {
        "name": item["itemName"],
        "price": item["itemPrice"],
        "shop": item.get("shopName", ""),
        "url": affiliate_url,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    LATEST_ITEM_LOG.write_text(json.dumps(data, ensure_ascii=False))


def load_posted_tips():
    if TIP_LOG.exists():
        return set(json.loads(TIP_LOG.read_text()))
    return set()


def save_posted_tip(tip, posted_tips):
    posted_tips.add(tip)
    TIP_LOG.write_text(json.dumps(list(posted_tips), ensure_ascii=False))


def load_post_count():
    if POST_COUNT_LOG.exists():
        return json.loads(POST_COUNT_LOG.read_text())["count"]
    return 0


def save_post_count(count):
    POST_COUNT_LOG.write_text(json.dumps({"count": count}))


def get_keyword_list():
    """
    RAKUTEN_KEYWORDS（カンマ区切り）が設定されていればそれをローテーション対象にする。
    未設定の場合は従来通り RAKUTEN_SEARCH_KEYWORD 単体を使う（ローテーションなし）。
    例: RAKUTEN_KEYWORDS="掃除機,ふるさと納税,サブスク,家電,クレジットカード"
    """
    raw = os.environ.get("RAKUTEN_KEYWORDS", "")
    keywords = [k.strip() for k in raw.split(",") if k.strip()]
    if keywords:
        return keywords
    single = os.environ.get("RAKUTEN_SEARCH_KEYWORD")
    return [single] if single else ["日用品"]


def peek_current_keyword():
    """現在のローテーション位置のキーワードを返す（状態は変更しない）"""
    keywords = get_keyword_list()
    if KEYWORD_INDEX_LOG.exists():
        index = json.loads(KEYWORD_INDEX_LOG.read_text())["index"]
    else:
        index = 0
    index = index % len(keywords)
    return keywords[index], index


def advance_keyword_rotation(index, keywords):
    """ローテーション位置を1つ進めて保存する（本番投稿時のみ呼ぶ）"""
    next_index = (index + 1) % len(keywords)
    KEYWORD_INDEX_LOG.write_text(json.dumps({"index": next_index}))


def get_settings():
    """
    実行時に環境変数を読み直す。
    （Colabなど、モジュールを一度importした後に os.environ を書き換えても
    　グローバル変数のままだと反映されないため、呼び出しのたびに読み直す設計にしている）
    """
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    require_approval = os.environ.get("REQUIRE_APPROVAL", "true").lower() == "true"
    return dry_run, require_approval


def ask_approval(preview_label):
    """投稿前に人の目でチェックするための確認プロンプト"""
    answer = input(f"\n上記の内容を{preview_label}として投稿します。よろしいですか？ [y/N]: ")
    return answer.strip().lower() == "y"


def main():
    dry_run, _ = get_settings()
    count = load_post_count()
    is_tip_turn = ORIGINAL_TIP_EVERY_N > 0 and (count % ORIGINAL_TIP_EVERY_N == ORIGINAL_TIP_EVERY_N - 1)

    if is_tip_turn:
        run_original_tip_post()
    else:
        run_product_post()

    if not dry_run:
        save_post_count(count + 1)


def run_original_tip_post():
    """商品紹介を含まない、オリジナルの節約Tips投稿を行う（スパム判定回避のため）"""
    dry_run, require_approval = get_settings()
    posted_tips = load_posted_tips()
    text, tip = generate_original_tip_post(exclude_tips=posted_tips)

    print("----- オリジナルTips投稿（商品紹介なし） -----")
    print(text)

    if dry_run:
        print("\n[DRY_RUN] 実際には投稿していません。DRY_RUN=falseにすると投稿されます。")
        return

    if require_approval and not ask_approval("オリジナルTips投稿"):
        print("キャンセルしました。")
        return

    result = post_to_x.post_tweet(text)
    print("Xへ投稿完了:", result)
    save_posted_tip(tip, posted_tips)


def run_product_post():
    """楽天商品を検索し、通常のアフィリエイト紹介投稿を行う"""
    dry_run, require_approval = get_settings()
    posted = load_posted_codes()

    keywords = get_keyword_list()
    keyword, keyword_index = peek_current_keyword()
    print(f"今回の検索キーワード: {keyword}")

    items = search_items(
        keyword=keyword,
        genre_id=os.environ.get("RAKUTEN_GENRE_ID") or None,
        min_price=os.environ.get("RAKUTEN_MIN_PRICE") or None,
        max_price=os.environ.get("RAKUTEN_MAX_PRICE") or None,
        hits=30,
    )
    if not items:
        print("該当商品が見つかりませんでした。検索条件を見直してください。")
        return

    item = pick_random_item(items, exclude_item_codes=posted)
    if item is None:
        print("未投稿の候補が尽きました。posted_items.jsonをリセットするか条件を広げてください。")
        return

    affiliate_url = get_affiliate_url(item)
    print(f"選ばれた商品: {item['itemName']} / {item['itemPrice']}円")

    if ENABLE_X:
        # ツリー投稿：本文（URLなし）→ リプライ（URLのみ）
        # X APIはURL付き投稿の課金が高いため、この方式でコストを抑える
        x_main_text = generate_x_caption(item)
        x_reply_text = generate_x_reply(affiliate_url)
        print("----- X本文（メイン投稿） -----")
        print(x_main_text)
        print("----- Xリプライ（URL） -----")
        print(x_reply_text)

        if dry_run:
            print("\n[DRY_RUN] 実際には投稿していません。DRY_RUN=falseにすると投稿されます。")
        else:
            if require_approval and not ask_approval("商品紹介投稿"):
                print("キャンセルしました。")
                return
            result = post_to_x.post_tweet_thread(x_main_text, x_reply_text)
            print("Xへ投稿完了:", result)

    if ENABLE_INSTAGRAM:
        ig_caption = generate_instagram_caption(item)
        print("----- Instagram投稿文 -----")
        print(ig_caption)
        if not dry_run:
            # 画像は事前にどこかで公開URL化しておく必要がある
            image_url = item.get("mediumImageUrls", [{}])[0].get("imageUrl")
            if image_url:
                result = post_to_instagram.post_image(image_url, ig_caption)
                print("Instagramへ投稿完了:", result)
            else:
                print("画像URLが取得できなかったためInstagram投稿をスキップしました。")

    if not dry_run:
        save_posted_code(item["itemCode"], posted)
        advance_keyword_rotation(keyword_index, keywords)
        save_latest_item(item, affiliate_url)


if __name__ == "__main__":
    main()
