import urllib
import os
from dotenv import load_dotenv, find_dotenv

def sendMessage(message):
    load_dotenv(find_dotenv())
    telegram_bot_key = os.environ.get("TELEGRAM_BOT_KEY")
    encoded_message = urllib.parse.quote(message)
    url = f"https://api.telegram.org/{telegram_bot_key}/sendMessage?chat_id=-1001481847267&text={encoded_message}"
    urllib.request.urlopen(url)