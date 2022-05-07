import os, time, re, json, warnings
from dotenv import load_dotenv
from datetime import datetime
import telebot, requests
from brownie import (
    Contract,
    accounts,
    chain,
    rpc,
    web3,
    history,
    Wei,
    ZERO_ADDRESS,
)

warnings.filterwarnings("ignore", ".*cannot be installed or is not supported by Brownie.*")
warnings.filterwarnings("ignore", ".*Locally compiled and on-chain bytecode do not match*")

load_dotenv()
key = os.getenv("WAVEY_ALERTS_BOT_KEY")
chat_id = os.environ.get("TELEGRAM_CHAT_ID_KEEPER")
bot = telebot.TeleBot(key)

CHAIN_VALUES = {
    1: {
        "NETWORK_NAME": "Ethereum Mainnet",
        "NETWORK_SYMBOL": "ETH",
        "JOB": "0x57419Fb50Fa588Fc165AcC26449B2Bf4C7731458",
        "EMOJI": "🇪🇹",
        "PROFIT_TARGET_USD": 65_000
    },
    250: {
        "NETWORK_NAME": "Fantom",
        "NETWORK_SYMBOL": "FTM",
        "TIME_SINCE_TXN_THRESHOLD": 60 * 15,
        "EOA": "0x000004e4d96d663C809Cbc8D773a764A89D0b37f",
        "JOB": "0x57419Fb50Fa588Fc165AcC26449B2Bf4C7731458",
        "EMOJI": "👻",
        "MIN_BALANCE": 500e18
    }
}

INFO = {
    "BALANCE": 0,
    "FIRST_RUN": True,
    "UNWORKED": [],
    "LAST_TXN_TIME": 0,
    "LAST_UPDATE": 0,
    "MIN_BALANCE": 200e18,
}

ERROR_CODES = {
    0: False,   # BALANCE ALERT
    1: False,   # TIME SINCE TXN EXCEEDED
}

def check_pre_existing_errors():
    for i in ERROR_CODES:
        if ERROR_CODES[i]:
            return True
    return False

def main():
    key = os.getenv("WAVEY_ALERTS_BOT_KEY")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID_KEEPER")
    bot = telebot.TeleBot(key)

    job = Contract(CHAIN_VALUES[chain.id]["JOB"])
    eoa = accounts.at(CHAIN_VALUES[chain.id]["EOA"], force=True)
    while True:
        all_strats = list(job.strategies())
        workable_strats = []
        for s in all_strats:
            if job.workable(s):
                workable_strats.append(s)

        INFO["UNWORKED"] = workable_strats
        last_balance = INFO["BALANCE"]
        last_txn_time = INFO["LAST_TXN_TIME"]
        INFO["BALANCE"] = eoa.balance()
        pre_existing_errors = check_pre_existing_errors()

        ### ALERT CONDITIONS
        # TOO LITTLE BALANCE
        if eoa.balance() < INFO["MIN_BALANCE"] and not INFO["FIRST_RUN"]:
            if not ERROR_CODES[0]: # Don't re-send if already sent
                ERROR_CODES[0] = True
                critical_alert(0)
        else:
            if ERROR_CODES[0] and not INFO["FIRST_RUN"]:
                # send_healthy(1)
                pass
            ERROR_CODES[0] = False

        # NO TXN SENT IN EXPECTED TIMEFRAME
        time_threshold = CHAIN_VALUES[chain.id]["TIME_SINCE_TXN_THRESHOLD"]
        if INFO["BALANCE"] != last_balance:
                INFO["LAST_TXN_TIME"] = chain.time()
                ERROR_CODES[1] = False
        elif chain.time() - INFO["LAST_TXN_TIME"] > time_threshold and not INFO["FIRST_RUN"] and len(workable_strats) > 0:
            if not ERROR_CODES[1]:
                ERROR_CODES[1] = True
                critical_alert(1, INFO) # Don't re-send if already sent
            

        # HEALTH RESTORED
        if pre_existing_errors == True and not check_pre_existing_errors() and not INFO["FIRST_RUN"]:
            send_healthy()
        
        if INFO["FIRST_RUN"]:
            INFO["FIRST_RUN"] = False
        elif not check_pre_existing_errors():
            info_alert(INFO)

        print(INFO)
        print(ERROR_CODES)
        
        time.sleep(60*5)

def send_healthy():
    m = f'healthy'
    bot.send_message(chat_id, m, parse_mode="markdown", disable_web_page_preview = True)

def info_alert(info):
    m = 'Info:\n'
    balance = int(info['BALANCE']/1e18)
    symbol = CHAIN_VALUES[chain.id]["NETWORK_SYMBOL"]
    ts = info['LAST_TXN_TIME']
    time_ago = int((chain.time() - ts) / 60)
    last_txn_date = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
    m += f'\nBalance: {balance} {symbol}'
    m += f'\nLast txn: {time_ago} minutes ago: {last_txn_date}'
    unworked = info['UNWORKED']
    if len(unworked) > 0:
        m += f'\nUnworked strategies:\n'
        unworked = info['UNWORKED']
        for u in unworked:
            m += f'{u}\n'
        m = f'info:'
    else:
        m += f'\nNo unworked strategies ✅\n'
    bot.send_message(chat_id, m, parse_mode="markdown", disable_web_page_preview = True)

def critical_alert(code, info):
    max_time_hrs = CHAIN_VALUES[chain.id]["TIME_SINCE_TXN_THRESHOLD"] / 60 / 60
    m = '🚨\n'
    if code == 0:
        min_balance = CHAIN_VALUES[chain.id]["MIN_BALANCE"] / 1e18
        symbol = CHAIN_VALUES[chain.id]["NETWORK_SYMBOL"]
        m += f'Keeper balance below {str(min_balance)} {symbol} threshold\n'
    if code == 1:
        m = f'Exceeded {max_time_hrs} hrs threshold since last harvest.\n'
    unworked = info['UNWORKED']
    if len(unworked) > 0:
        m += f'\nUnworked strategies:\n'
        unworked = info['UNWORKED']
        for u in unworked:
            m += f'{u}\n'
        m = f'info:'
    t = bot.send_message(chat_id, m, parse_mode="markdown", disable_web_page_preview = True)
    bot.pin_chat_message(chat_id,t.message_id,disable_notification=False)


