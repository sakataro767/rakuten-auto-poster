"""
商品データから投稿文を自動生成するモジュール。
テンプレート方式（無料・API不要）と、Claude APIで自然文生成する方式の
どちらも用意しています。
"""
import random

# ---------- テンプレート方式（コスト0円） ----------

# URLを含めない「本文ツイート」用テンプレート
# （X APIはURL付き投稿が$0.20/件と高いため、URLはリプライ側に分離する）
# URLを含めない「本文ツイート」用テンプレート
# （X APIはURL付き投稿が$0.20/件と高いため、URLはリプライ側に分離する）
# ※テンプレートが少ないと「似たような投稿の繰り返し」とみなされスパム判定の
#   リスクがあるため、できるだけバリエーションを多く用意する
X_TEMPLATES = [
    "【{shop}】\n{name}\n\n{price}円\n\n{tags}\n\n👇詳細・購入はリプ欄から",
    "気になっていた「{name}」\n価格: {price}円（{shop}）\n\n{tags}\n\n👇リンクはこちら",
    "楽天でチェック👀\n{name}\n{price}円〜\n\n{tags}\n👇購入はリプ欄で",
    "節約家目線でチェックした商品📝\n{name}\n{price}円（{shop}）\n\n{tags}\n👇詳細はリプ欄",
    "これ、コスパ良さそうです。\n{name}\n{price}円〜\n{shop}にて\n\n{tags}\n👇購入はこちら（リプ欄）",
    "{shop}で見つけた気になるアイテム。\n{name}\n価格：{price}円\n\n{tags}\n👇リンクはリプへ",
    "買い時かもしれません。\n{name}（{price}円）\n{shop}\n\n{tags}\n👇詳細はリプ欄をチェック",
    "家計簿つけてて気になった商品📒\n{name}\n{price}円\n\n{tags}\n👇リプ欄にリンクあります",
    "コスト意識高めの人向け。\n{name}\n{price}円（{shop}）\n\n{tags}\n👇気になる方はリプ欄へ",
    "地味に便利そうなアイテム発見。\n{name}\n価格：{price}円\n{shop}\n\n{tags}\n👇リンクはリプ欄",
    "投資して損はなさそうな一品。\n{name}（{price}円）\n\n{tags}\n👇詳細・購入はリプ欄から",
    "{shop}をチェックしてたら見つけました。\n{name}\n{price}円\n\n{tags}\n👇購入リンクはリプへ",
    "節約しつつ満足度も欲しい方に。\n{name}\n{price}円（{shop}）\n\n{tags}\n👇リプ欄からどうぞ",
    "家計に優しいかもしれない選択肢。\n{name}\n価格：{price}円\n\n{tags}\n👇詳細はリプ欄で",
    "ふと目に留まった商品です。\n{name}（{price}円・{shop}）\n\n{tags}\n👇気になったらリプ欄へ",
]

# リプライ（URLのみ・課金は$0.01/件のまま）
X_REPLY_TEMPLATE = "こちらから購入できます🛒\n{url}\n※アフィリエイトリンクを含みます"

# ---------- オリジナル投稿（商品紹介ではない、独自コンテンツ） ----------
# 商品紹介ばかりだと「似たような投稿の繰り返し」とみなされスパム判定の
# リスクが高まるため、お金・節税・節約ジャンルのオリジナルTipsを定期的に混ぜる。
# アフィリエイトリンクは含めない（純粋な情報発信ツイート）。
ORIGINAL_TIPS = [
    "ふるさと納税は年収だけでなく家族構成でも控除上限額が変わります。年末に慌てないよう、夏のうちにシミュレーションしておくのがおすすめです。",
    "電気代を見直すなら、契約アンペア数の変更が地味に効きます。使っていない容量に毎月基本料金を払っていないか、一度確認してみてください。",
    "ポイ活は「貯める」より「使い切る」意識の方が節約効果は大きいです。失効ポイントがないか、月1回はアプリをチェックする習慣を。",
    "医療費控除は家族分の領収書を合算できます。1年間で10万円を超えそうなら、確定申告で戻ってくる可能性があるので保管しておきましょう。",
    "サブスクの見直し、半年に1回はやった方がいいです。使っていないサービスが1つでもあれば、年間で数千〜数万円変わってきます。",
    "iDeCoやNISAは「非課税」という制度上のメリットが本体です。まずは制度の仕組みを理解してから、商品選びに進むのがおすすめです。",
    "クレジットカードのポイント還元率、実は「基本還元率」より「特定店舗での還元率」の方が家計への影響が大きいことが多いです。",
    "節約は我慢よりも固定費の見直しの方が効果が長続きします。通信費・保険・サブスクから手をつけるのが定石です。",
    "生命保険や医療保険は、加入時のまま何年も見直していないケースが多いです。ライフステージが変わったタイミングで一度保障内容を確認してみましょう。",
    "所得税は「今年の所得」に、住民税は「前年の所得」にかかります。転職や退職の翌年は住民税の負担感が変わりやすいので覚えておくと安心です。",
    "ポイント経済圏はあれこれ手を出すより、1〜2つに絞った方が還元率もポイント管理も効率的になりやすいです。",
    "家計簿は費目を細かく分けすぎると続かなくなりがちです。まずは「固定費」「変動費」「特別費」の3つくらいから始めるのがおすすめです。",
    "会社員でも副業の所得が年20万円を超えると、原則として確定申告が必要になります。年末調整だけで済ませられるかは早めに確認しておきましょう。",
    "QRコード決済やクレジットカードのキャンペーンは、条件次第で複数のキャンペーンを重ねて適用できることがあります。エントリー忘れがないか要チェックです。",
    "家電の買い替えは型落ちモデルが安くなるタイミング（新モデル発売直後など）を狙うと、性能はほぼ変わらず価格だけ下がることが多いです。",
]

X_TIP_TEMPLATES = [
    "{tip}\n\n{tags}",
    "知っておくと得するかもしれません。\n{tip}\n\n{tags}",
    "家計管理のメモ📝\n{tip}\n\n{tags}",
    "今日の気づき。\n{tip}\n\n{tags}",
]

TIP_TAGS = ["#節約", "#マネーリテラシー", "#家計管理"]

IG_TEMPLATE = (
    "{name}\n\n価格: {price}円\nショップ: {shop}\n\n"
    "{tags}\n\n"
    "詳細・購入はプロフィールのリンクから🔗\n"
    "※楽天アフィリエイトを含みます"
)


def _make_tags(item):
    genre_words = ["#楽天", "#楽天room", "#おすすめ商品"]
    return " ".join(genre_words)


def generate_x_caption(item):
    """
    Xのメイン投稿文（280字目安、URLなし）を生成。
    URLはコストの安いリプライ側に分離する（generate_x_reply参照）。
    """
    tpl = random.choice(X_TEMPLATES)
    text = tpl.format(
        shop=item.get("shopName", ""),
        name=_truncate(item["itemName"], 60),
        price=f"{item['itemPrice']:,}",
        tags=_make_tags(item),
    )
    return text[:280]


def generate_x_reply(affiliate_url):
    """メイン投稿へのリプライ文（URLのみ）を生成"""
    return X_REPLY_TEMPLATE.format(url=affiliate_url)


def generate_original_tip_post(exclude_tips=None):
    """
    商品紹介を含まないオリジナルの節約/マネーTips投稿を生成する。
    スパム判定回避のため、商品投稿の合間に定期的に挟むことを想定。

    Returns: (text, tip) のタプル。tip は重複回避のための識別用。
    """
    exclude_tips = exclude_tips or set()
    candidates = [t for t in ORIGINAL_TIPS if t not in exclude_tips]
    if not candidates:
        candidates = ORIGINAL_TIPS  # 全部使い切ったら一周してリセット

    tip = random.choice(candidates)
    tpl = random.choice(X_TIP_TEMPLATES)
    text = tpl.format(tip=tip, tags=" ".join(TIP_TAGS))
    return text[:280], tip


def generate_instagram_caption(item):
    """
    Instagram用キャプション（リンクは貼らずbio誘導にする）
    ※アフィリエイトURLはInstagram本文ではクリックできないため含めない
    """
    text = IG_TEMPLATE.format(
        name=_truncate(item["itemName"], 80),
        price=f"{item['itemPrice']:,}",
        shop=item.get("shopName", ""),
        tags=_make_tags(item),
    )
    return text


def _truncate(text, max_len):
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


# ---------- Claude APIで自然文生成する方式（任意・高品質） ----------

def generate_caption_with_claude(item, affiliate_url, platform="x"):
    """
    Anthropic APIを使って、より自然な紹介文を生成する（ANTHROPIC_API_KEY必須）。
    テンプレート方式で十分なら使わなくてOK。

    注意: これは「1投稿にURLを含める」旧方式です。X APIのURL付き投稿は
    課金が高いため、ツリー投稿（本文→リプライ）で運用する場合は
    generate_x_caption / generate_x_reply を使ってください。
    """
    import os
    import requests

    prompt = (
        f"以下の商品情報をもとに、{platform}向けの魅力的な紹介文を1つ作成してください。"
        f"誇大表現や薬機法・景表法に抵触する表現は避け、事実に基づいた自然な文章にしてください。\n\n"
        f"商品名: {item['itemName']}\n"
        f"価格: {item['itemPrice']}円\n"
        f"ショップ: {item.get('shopName', '')}\n\n"
        f"出力は本文のみ（説明や前置き不要）。"
    )
    if platform == "x":
        prompt += " 280字以内。最後にURLを入れる場所として[URL]と書いてください。"

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"]
    if platform == "x":
        text = text.replace("[URL]", affiliate_url)
    return text
