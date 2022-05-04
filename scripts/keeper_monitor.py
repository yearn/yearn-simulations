import os
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
import time, re, json
import warnings
warnings.filterwarnings("ignore", ".*cannot be installed or is not supported by Brownie.*")
warnings.filterwarnings("ignore", ".*Locally compiled and on-chain bytecode do not match*")

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
    "TIME_SINCE_TXN_THRESHOLD": 60 * 60,
    "LAST_UPDATE": 0,
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
    job = Contract(CHAIN_VALUES[chain.id]["JOB"])
    eoa = accounts.at(CHAIN_VALUES[chain.id]["EOA"], force=True)
    all_strats = list(job.strategies())
    workable_strats = []
    for s in all_strats:
        if job.workable(s):
            workable_strats.append(s)
    print(workable_strats)
    INFO["UNWORKED"] = workable_strats
    last_balance = INFO["BALANCE"]
    last_txn_time = INFO["LAST_TXN_TIME"]
    INFO["BALANCE"] = eoa.balance()
    pre_existing_errors = pre_existing_errors()

    ### ALERT CONDITIONS
    # TOO LITTLE BALANCE
    if eoa.balance() < INFO["MIN_BALANCE"]:
        if not ERROR_CODES[0]: # Don't re-send if already sent
            ERROR_CODES[0] = True
            critical_alert()
    else:
        if ERROR_CODES[0]:
            send_healthy()
        ERROR_CODES[0] = False

    # NO TXN SENT IN EXPECTED TIMEFRAME
    if chain.time() - INFO["LAST_TXN_TIME"] > INFO["TIME_SINCE_TXN_THRESHOLD"]:
        if not ERROR_CODES[1]:
            ERROR_CODES[1] = True
            critical_alert() # Don't re-send if already sent
    else:
        if ERROR_CODES[1]:
            send_healthy()
        INFO["LAST_TXN_TIME"] = chain.time()
        # C
        ERROR_CODES[1] = False


    # HEALTH RESTORED
    if chain.time() - INFO["LAST_UPDATE"] > 60 * 15:
        INFO["LAST_UPDATE"] = chain.time()
        if INFO["LAST_UPDATE"] > info_alert():


def info_alert():
    pass

def critical_alert():
    pass

def has_enough_eth():
    eoa = accounts.at("0x000004e4d96d663C809Cbc8D773a764A89D0b37f", force=True)
    if eoa.balance < 100e18:
        m = f'Not enough funds'
        # send_alert(m)

# def send_alert():

