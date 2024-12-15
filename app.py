import os
import json
import random
import pytz
from threading import Thread
from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

app = Flask(__name__)

# 從環境變數獲取配置
channel_access_token = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
channel_secret = os.environ['LINE_CHANNEL_SECRET']

configuration = Configuration(access_token=channel_access_token)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(channel_secret)

def ensure_directory_exists():
    # 確保 list 目錄存在
    if not os.path.exists('list'):
        os.makedirs('list')
        print("已創建 list 目錄")

def ensure_files_exist():
    # 要創建的檔案列表
    files = [
        'list/easy.txt',
        'list/delivery.txt',
        'list/great.txt',
        'list/drink.txt',
        'list/blacklist.txt'
    ]
    
    # 確保每個檔案都存在
    for file in files:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                pass  # 創建空檔案
            print(f"已創建檔案: {file}")

# 定義不同類別的店家
def load_restaurants():
    ensure_directory_exists()
    ensure_files_exist()
    restaurant_files = {
        "簡單出去吃": "list/easy.txt",
        "外送": "list/delivery.txt",
        "吃點好的": "list/great.txt",
        "喝點飲料": "list/drink.txt"
    }
    
    restaurants = {}
    empty_categories = []
    for category, filename in restaurant_files.items():
        try:
            with open(filename, "r", encoding="utf-8") as f:
                restaurants[category] = [line.strip() for line in f if line.strip()]  # 去掉空行
                if not restaurants[category]:
                    empty_categories.append(category)
                    print(f"警告：{category} ({filename}) 是空的")
        except FileNotFoundError:
            print(f"檔案 {filename} 未找到。")
            restaurants[category] = []  # 如果文件不存在，則設置為空列表
            empty_categories.append(category)
    if empty_categories:
        print(f"以下類別沒有資料：{', '.join(empty_categories)}")

    return restaurants

# 載入黑名單
def load_blacklist():
    try:
        with open("list/blacklist.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("黑名單檔案未找到，將返回空列表。")
        return []

# 在主程序中載入餐廳數據
restaurants = load_restaurants()
blacklist = load_blacklist()

def send_button_message(reply_token):
    contents = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "該決定晚餐要吃什麼了",
                    "weight": "bold",
                    "size": "xl",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": "目前有以下選擇",
                    "size": "md",
                    "align": "center",
                    "margin": "md"
                },
                {
                    "type": "separator",
                    "margin": "xxl"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "xxl",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#FFA07A",
                            "action": {
                                "type": "message",
                                "label": "簡單出去吃",
                                "text": "選擇簡單出去吃"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#98FB98",
                            "action": {
                                "type": "message",
                                "label": "外送",
                                "text": "選擇外送"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#87CEFA",
                            "action": {
                                "type": "message",
                                "label": "吃點好的",
                                "text": "選擇吃點好的"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "color": "#E7FA87",
                            "action": {
                                "type": "message",
                                "label": "喝點飲料",
                                "text": "選擇喝點飲料"
                            }
                        }
                    ]
                }
            ]
        }
    }

    flex_message = FlexMessage.from_json(json.dumps({
        "type": "flex",
        "altText": "該吃晚餐囉 請選擇晚餐方式",
        "contents": contents
    }))
    
    reply_request = ReplyMessageRequest(
        replyToken=reply_token,
        messages=[flex_message]
    )
    
    line_bot_api.reply_message(reply_request)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    load_blacklist()
    load_restaurants() 
    # 收到 "我要點餐" 訊息，回傳選單按鈕
    if event.message.text == "我要點餐":
        send_button_message(event.reply_token)
    # 檢查是否是選擇列出清單的請求
    if event.message.text.startswith("列出清單"):
        category = event.message.text[5:]  # 去掉 "列出清單 " 七個字
        if category == "全部":
            # 列出所有類別的店家
            message = "目前所有的店家選項：\n"
            categories = list(restaurants.keys())
            empty_categories = []
            for i, category in enumerate(categories):
                if not restaurants[category]:  # 如果該類別是空的
                    empty_categories.append(category)
                    continue
                message += f"\n{category}：\n"
                message += "\n".join(f"- {shop}" for shop in restaurants[category])
                if i < len(categories) - 1:  # 如果不是最後一個類別，添加一個空行
                    message += "\n"
            if empty_categories:
                message += "\n\n以下類別目前沒有店家：\n"
                message += ", ".join(empty_categories)
            reply_message = message
        elif category in restaurants:
            if not restaurants[category]:  # 檢查該類別是否為空
                reply_message = f"目前 '{category}' 選項中沒有店家"
            else:
                # 列出該類別的所有餐廳
                message = f"{category}的店家清單：\n"
                message += "\n".join(f"- {shop}" for shop in restaurants[category])
                reply_message = message
        else:
            reply_message = "無效的選項，請重新選擇。"

        reply_request= ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=reply_message)]
        )
        line_bot_api.reply_message(reply_request)
    
    # 檢查是否是按鈕選擇的請求
    if event.message.text.startswith("選擇"):
        category = event.message.text[2:]  # 去掉 "選擇" 兩個字
        if category in restaurants:
            if not restaurants[category]:  # 檢查該類別是否為空
                reply_message = f"目前 '{category}' 選項中沒有店家"
            else:
                chosen_restaurant = random.choice(restaurants[category])
                reply_message = f"根據 '{category}' 的選擇，抽中的是：{chosen_restaurant}"
        else:
            reply_message = "無效的選項，請重新選擇。"
        
        reply_request= ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=reply_message)]
        )
        line_bot_api.reply_message(reply_request)
    
    # 檢查是否是新增店家的請求
    if event.message.text.startswith("新增店家"):
        parts = event.message.text.split(" ")
        if len(parts) != 3:
            reply_message = "請使用格式：新增店家 <類別> <店名>"
        else:
            category = parts[1]
            new_restaurant = parts[2]
            if category in restaurants:
                if new_restaurant not in restaurants[category]:
                    if not any(banned_word in new_restaurant for banned_word in blacklist):
                        restaurants[category].append(new_restaurant)
                        update_restaurant_file(category)  # 更新文件
                        reply_message = f"店家 '{new_restaurant}' 已新增到類別 '{category}'。"
                    else:
                        reply_message = f"店家 '{new_restaurant}' 含有黑名單中的關鍵字，無法新增。"
                else:
                    reply_message = f"店家 '{new_restaurant}' 已存在於類別 '{category}'。"
            else:
                reply_message = "無效的類別，請重新選擇。"

        reply_request= ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=reply_message)]
        )
        line_bot_api.reply_message(reply_request)
    
    # 檢查是否是刪除店家的請求
    if event.message.text.startswith("刪除店家"):
        parts = event.message.text.split(" ")
        if len(parts) != 3:
            reply_message = "請使用格式：刪除店家 <類別> <店名>"
        else:
            category = parts[1]
            restaurant_to_remove = parts[2]
            if category in restaurants:
                if restaurant_to_remove in restaurants[category]:
                    restaurants[category].remove(restaurant_to_remove)
                    update_restaurant_file(category)  # 更新文件
                    reply_message = f"店家 '{restaurant_to_remove}' 已從類別'{category}'刪除。"
                else:
                    reply_message = f"店家 '{restaurant_to_remove}' 不在類別'{category}'中。"
            else:
                reply_message = "無效的類別，請重新選擇。"

        reply_request= ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=reply_message)]
        )
        line_bot_api.reply_message(reply_request)

    if event.message.text.startswith("新增黑名單"):
        parts = event.message.text.split(" ")
        if len(parts) != 2:
            reply_message = "請使用格式：新增黑名單 <店名>"
        else:
            restaurant_to_blacklist = parts[1]
            if restaurant_to_blacklist not in blacklist:
                blacklist.append(restaurant_to_blacklist)  # 更改這裡
                update_blacklist_file()  # 更新黑名單文件
                reply_message = f"店家 '{restaurant_to_blacklist}' 已新增到黑名單。"
            else:
                reply_message = f"店家 '{restaurant_to_blacklist}' 已存在於黑名單中。"

        reply_request= ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=reply_message)]
        )
        line_bot_api.reply_message(reply_request)
    
    if event.message.text.startswith("移除黑名單"):
        parts = event.message.text.split(" ")
        if len(parts) != 2:
            reply_message = "請使用格式：移除黑名單 <店名>"
        else:
            restaurant_to_remove = parts[1]
            if restaurant_to_remove in blacklist:
                blacklist.remove(restaurant_to_remove)
                update_blacklist_file()  # 更新黑名單文件
                reply_message = f"店家 '{restaurant_to_remove}' 已從黑名單中移除。"
            else:
                reply_message = f"店家 '{restaurant_to_remove}' 不在黑名單中。"

        reply_request= ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=reply_message)]
        )
        line_bot_api.reply_message(reply_request)

    if event.message.text.startswith("列出黑名單"):
        if blacklist:
            reply_message = "黑名單中的店家有：\n" + "\n".join(f"- {restaurant}" for restaurant in blacklist)
        else:
            reply_message = "黑名單是空的。"

        reply_request= ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[TextMessage(text=reply_message)]
        )
        line_bot_api.reply_message(reply_request)

def update_restaurant_file(category):
    """更新特定類別的餐廳文件"""
    filename = {
        "簡單出去吃": "list/easy.txt",
        "外送": "list/delivery.txt",
        "吃點好的": "list/great.txt",
        "喝點飲料": "list/drink.txt"
    }[category]
    with open(filename, "w", encoding="utf-8") as f:
        for restaurant in restaurants[category]:
            f.write(restaurant + "\n")

def update_blacklist_file():
    """更新黑名單文件"""
    with open("list/blacklist.txt", "w", encoding="utf-8") as f:
        for restaurant in blacklist:
            f.write(restaurant + "\n")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

