import urllib
import os
from dotenv import load_dotenv, find_dotenv

def sendResultToTelegram(message, monospacedFont = True):
    load_dotenv(find_dotenv())
    telegram_bot_key = os.environ.get("TELEGRAM_BOT_KEY")
    #telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    telegram_chat_id = os.environ.get("TELEGRAM_YFI_HARVEST_SIMULATOR")
    if monospacedFont:
        message = f"```\n{message}\n```"
    encoded_message = urllib.parse.quote(message)
    url = f"https://api.telegram.org/{telegram_bot_key}/sendMessage?chat_id={telegram_chat_id}&text={encoded_message}"
    if monospacedFont:
        url += "&parse_mode=MarkdownV2"
    urllib.request.urlopen(url)

def sendMessageToTelegram(message):
    load_dotenv(find_dotenv())
    telegram_bot_key = os.environ.get("TELEGRAM_BOT_KEY")
    telegram_chat_id = os.environ.get("TELEGRAM_YFI_HARVEST_SIMULATOR")
    encoded_message = urllib.parse.quote(message)
    url = f"https://api.telegram.org/{telegram_bot_key}/sendMessage?chat_id={telegram_chat_id}&text={encoded_message}"
    print(url)
    urllib.request.urlopen(url)