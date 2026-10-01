from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage, QuickReply, QuickReplyButton, MessageAction
import requests
import os

app = Flask(__name__)

# ====== ใส่ค่าจาก LINE Developers แก้ให้เป็นของ line ตัวเอง ใน " "======
LINE_CHANNEL_ACCESS_TOKEN = "v0OvtjMfG0h7O0puvK/Vyjtj2vIcvcvZ1Nq55/tRsTIFXpHsErdpczz8vmQ3lMzBcJTFRGroR5D0K5cOggOjD6pJBZYKK8kXt/tmkiaBc7u7ZcDaeAR7Xf9pLc9nEhAX9Rw6aHyLHKk5LIMa5JJcgQdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "f5d09b8ee65dae86fd39f543f3f07224"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ====== Rasa REST endpoint ======
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

def build_quick_reply(buttons=None):
    items = []
    if buttons:
        for b in buttons:
            title = b.get("title", "")[:20]
            payload = b.get("payload", b.get("text", ""))
            if title and payload:
                items.append(QuickReplyButton(action=MessageAction(label=title, text=payload)))

    if not items:
        # ปุ่ม Quick Reply ด่วนตั้งต้นสำหรับ LINE Chatbot
        items = [
            QuickReplyButton(action=MessageAction(label="🍽️ แนะนำอาหาร", text="แนะนำอาหารหน่อย")),
            QuickReplyButton(action=MessageAction(label="🏋️‍♂️ ออกกำลังกาย", text="แนะนำการออกกำลังกายหน่อย")),
            QuickReplyButton(action=MessageAction(label="📈 ประวัติ BMI", text="ดูประวัติ BMI หน่อย")),
            QuickReplyButton(action=MessageAction(label="💡 BMR & TDEE", text="BMR คืออะไร")),
            QuickReplyButton(action=MessageAction(label="📊 คำนวณสุขภาพ", text="ชาย 25 70 175 ลดน้ำหนัก ปานกลาง")),
        ]

    return QuickReply(items=items)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text

    payload = {
        "sender": user_id,
        "message": user_message
    }

    try:
        res = requests.post(RASA_URL, json=payload, timeout=10)
        responses = res.json()
    except Exception as e:
        print(f"Error communicating with Rasa server: {e}")
        responses = []

    messages = []

    # 👉 ถ้า Rasa ส่งข้อความกลับมา
    if responses:
        for r in responses:
            text_content = r.get("text")
            custom_buttons = r.get("buttons")
            custom_data = r.get("custom", {})

            # ตรวจสอบว่าเป็น Flex Message หรือไม่
            if isinstance(custom_data, dict) and custom_data.get("type") == "flex":
                alt_text = custom_data.get("alt_text", "รายงานสุขภาพส่วนบุคคล")
                flex_contents = custom_data.get("flex_contents")
                if flex_contents:
                    msg = FlexSendMessage(alt_text=alt_text, contents=flex_contents)
                    if custom_buttons:
                        msg.quick_reply = build_quick_reply(custom_buttons)
                    messages.append(msg)
                    continue

            if text_content:
                msg = TextSendMessage(text=str(text_content))
                if custom_buttons:
                    msg.quick_reply = build_quick_reply(custom_buttons)
                messages.append(msg)


    # 👉 หากมีข้อความตอบกลับ ให้แนบ Quick Reply ท้ายข้อความสุดท้าย
    if messages:
        if not messages[-1].quick_reply:
            messages[-1].quick_reply = build_quick_reply()

        try:
            # ชุดแรก 5 ข้อความแรกส่งด้วย reply_token (ฟรี)
            reply_batch = messages[:5]
            line_bot_api.reply_message(event.reply_token, reply_batch)

            # หากมีข้อความเหลือมากกว่า 5 ข้อความ ให้ส่งส่วนที่เหลือด้วย push_message เป็นชุดๆ ละไม่เกิน 5 ข้อความ
            remaining = messages[5:]
            while remaining:
                batch = remaining[:5]
                line_bot_api.push_message(user_id, batch)
                remaining = remaining[5:]
        except Exception as e:
            print(f"Error sending message to LINE: {e}")
            # Fallback: ถ้าเกิดข้อผิดพลาดในการส่ง ให้ส่งกลับเป็น TextSendMessage ดั้งเดิม
            try:
                text_messages = []
                for r in responses:
                    txt = r.get("text")
                    if txt:
                        text_messages.append(TextSendMessage(text=str(txt)))
                if text_messages:
                    text_messages[-1].quick_reply = build_quick_reply()
                    line_bot_api.reply_message(event.reply_token, text_messages[:5])
            except Exception as fb_err:
                print(f"Fallback send failed: {fb_err}")


if __name__ == "__main__":
    app.run(port=8000)
