import os

from dotenv import load_dotenv
from datetime import datetime
from ypricemagic.magic import get_price
import telebot, requests
from brownie import (
    Contract,
    accounts,
    chain,
    rpc,
    web3,
    history,
    interface,
    Wei,
    ZERO_ADDRESS,
)
import time, re, json

def main():
    bribev2 = Contract("0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026")
    load_dotenv()
    env = os.environ.get("ENV") # Set environment
    test_group = os.getenv("TELEGRAM_CHAT_ID_TEST_GROUP")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID_BRIBE")
    # chat_id = test_group
    bot_key = os.environ.get("TELEGRAM_YFI_DEV_BOT")
    bot = telebot.TeleBot(bot_key)
    
    voter = Contract("0xF147b8125d2ef93FB6965Db97D6746952a133934")
    gauge_controller = Contract("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB")
    addresses_provider = Contract("0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93")
    oracle = Contract(addresses_provider.addressById("ORACLE"))
    indent = "    "
    WEEK = 86400 * 7
    num_gauges = gauge_controller.n_gauges()
    formated_days = lock_times()
    print("Found "+str(num_gauges)+" gauges...")
    last_vote_timestamp = 0
    days_since_last_vote = 100
    next_vote_available = 0
    should_print = False
    
    for i in range(0, num_gauges):
        msg = ""
        gauge_controller.gauge_relative_weight
        g = gauge_controller.gauges(i)
        last_vote_timestamp = gauge_controller.last_user_vote(voter, g)
        seconds_diff = time.time() - last_vote_timestamp
        days_diff = round(seconds_diff / 60 / 60 / 24,2)
        if days_diff < days_since_last_vote:
            days_since_last_vote = days_diff
            next_vote_available = last_vote_timestamp + (10 * 86400)
        rewards = bribev2.rewards_per_gauge(g)
        gauge = Contract(g)
        try:
            lp_name = Contract(gauge.lp_token()).name()
        except:
            lp_name = "Cannot find name"
        if len(rewards) > 0:
            msg = msg + "[" + lp_name + "](https://etherscan.io/address/"+g+")\n"
            period = round(round(time.time()) / WEEK) * WEEK - WEEK
            for i,  r in enumerate(rewards):
                try:
                    price = get_price(r)
                except:
                    print("Error finding price for", r)
                    continue
                token = Contract(r)
                total_tokens = bribev2.reward_per_token(g, r) / 10**token.decimals()
                total_tokens = total_tokens * gauge_controller.points_weight(g, period).dict()["slope"] / 1e18
                claimable = bribev2.claimable(voter, g, r) / 10**token.decimals()
                claimable_usd_str = ""
                total_tokens_price = ""
                if price == 0:
                    total_tokens_price = "? Cannot find price"
                else:
                    total_tokens_price = "${:,.2f}".format(total_tokens * price)

                if (claimable == 0 or price * claimable < 100) and total_tokens * price < 50_000:
                    print(token.name(), claimable, price*claimable, total_tokens * price)
                    continue
                should_print = True
                claimable_usd = price * claimable
                emoji = ""
                if claimable_usd > 0:
                    emoji = "💰 "
                claimable_usd_str = "${:,.2f}".format(claimable_usd)
                if i > 0:
                    msg = msg + indent + "---\n"
                msg = msg + indent + token.name() + " " + str(round(total_tokens,2)) + " " + token.symbol() + " " + total_tokens_price + "\n"
                msg = msg + indent + f'{emoji}Claimable by yearn: {str(round(claimable,2))} {token.symbol()} {claimable_usd_str}\n'
            if env == "PROD" and should_print:
                bot.send_message(chat_id, msg, parse_mode="markdown", disable_web_page_preview = True)
            if should_print:
                print(msg)
            should_print = False
    message = "Last lock: " + formated_days + " days ago\n\n"
    message = message + "Days since last vote: " + str(days_since_last_vote) + "\n\n"
    message = message + "Next available vote date: " + datetime.utcfromtimestamp(next_vote_available).strftime('%Y-%m-%d %H:%M:%S')
    print(message)
    if env == "PROD":
        bot.send_message(chat_id, message, parse_mode="markdown", disable_web_page_preview = True)
    print(msg)

def lock_times():
    MAXTIME = 4 * 365 * 86400
    current_time = round(time.time(),0)
    four_years = current_time + MAXTIME
    print("current_time",current_time)
    vecrv = Contract("0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2")
    voter = Contract("0xF147b8125d2ef93FB6965Db97D6746952a133934")
    lock_end_date = vecrv.locked__end(voter)
    days_since_last_lock = (four_years - lock_end_date) / 60 / 60 / 24
    formated_days = "{:.0f}".format(round(days_since_last_lock,0))
    print("day since last lock",formated_days)
    return formated_days