import os
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ["ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])


@app.route("/")
def index():
    return "You call index()"


@app.route("/callback", methods=["POST"])
def callback():
    """Messaging APIからの呼び出し関数"""
    # LINEがリクエストの改ざんを防ぐために付与する署名を取得
    signature = request.headers["X-Line-Signature"]
    # リクエストの内容をテキストで取得
    body = request.get_data(as_text=True)
    # ログに出力
    app.logger.info("Request body: " + body)

    try:
        # signature と body を比較することで、リクエストがLINEから送信されたものであることを検証
        handler.handle(body, signature)
    except InvalidSignatureError:
        # クライアントからのリクエストに誤りがあったことを示すエラーを返す
        abort(400)

    return "OK"


def search_address(zipcode):
    """郵便番号APIで郵便番号から住所を取得する"""
    url = "https://zipcloud.ibsnet.co.jp/api/search"
    params = {"zipcode": zipcode}

    response = requests.get(url, params=params, timeout=5)
    response.raise_for_status()

    data = response.json()
    results = data["results"]

    if results is None:
        return "該当する住所が見つかりませんでした。"

    address = results[0]
    return f'{address["address1"]}{address["address2"]}{address["address3"]}'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text.strip()

    if message.isdecimal() and len(message) == 7:
        try:
            reply_text = search_address(message)
        except requests.RequestException:
            reply_text = "住所検索APIの呼び出しに失敗しました。時間をおいて試してください。"
    else:
        reply_text = "郵便番号をハイフンなし7桁で送ってください。\n例: 0287111"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
