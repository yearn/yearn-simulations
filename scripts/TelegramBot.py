import urllib
import os
from dotenv import load_dotenv, find_dotenv

def sendResultToTelegram(message, chat_id, monospacedFont = True):
    load_dotenv(find_dotenv())
    telegram_bot_key = os.environ.get("TELEGRAM_BOT_KEY")
    if monospacedFont:
        message = f"```\n{message}\n```"
    encoded_message = urllib.parse.quote(message)
    url = f"https://api.telegram.org/{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={encoded_message}"
    if monospacedFont:
        url += "&parse_mode=MarkdownV2"
    urllib.request.urlopen(url)

def sendMessageToTelegram(message, chat_id):
    load_dotenv(find_dotenv())
    telegram_bot_key = os.environ.get("TELEGRAM_BOT_KEY")
    encoded_message = urllib.parse.quote(message)
    url = f"https://api.telegram.org/{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={encoded_message}"
    urllib.request.urlopen(url)