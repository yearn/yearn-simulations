import os

from dotenv import load_dotenv
import pandas as pd
import telebot
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
    load_dotenv()
    env = os.environ.get("ENV") # Set environment
    test_group = os.getenv("TELEGRAM_CHAT_ID_TEST_GROUP")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID_BRIBE")
    # chat_id = test_group
    bot_key = os.environ.get("TELEGRAM_YFI_DEV_BOT")
    bot = telebot.TeleBot(bot_key)
    bribev2 = interface.IBribeV2("0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026")
    voter = interface.IVoter("0xF147b8125d2ef93FB6965Db97D6746952a133934")
    gauge_controller = interface.IGaugeController("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB")
    addresses_provider = interface.IAddressProvider("0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93")
    oracle = interface.IOracle(addresses_provider.addressById("ORACLE"))
    indent = "    "
    num_gauges = gauge_controller.n_gauges()
    print("Found "+str(num_gauges)+" gauges...")
    for i in range(0, num_gauges):
        msg = ""
        gauge_controller.gauge_relative_weight
        g = gauge_controller.gauges(i)
        rewards = bribev2.rewards_per_gauge(g)
        gauge = interface.Gauge(g)
        try:
            lp_name = interface.IERC20(gauge.lp_token()).name()
        except:
            lp_name = "Cannot find name"
        if len(rewards) > 0:
            msg = msg + "[" + lp_name + "](https://etherscan.io/address/"+g+")\n"
            for i,  r in enumerate(rewards):
                price = oracle.getPriceUsdcRecommended(r) / 10**6
                token = interface.IERC20(r)
                total_tokens = bribev2.reward_per_token(g, r) / 10**token.decimals()
                claimable = bribev2.claimable(voter, g, r) / 10**token.decimals()
                claimable_str = claimable / 10**token.decimals()
                claimable_usd = price * claimable_str
                if i > 0:
                    msg = msg + indent + "---\n"
                msg = msg + indent + token.name() + " " + str(round(total_tokens,2)) + " " + token.symbol() + " " + "${:,.2f}".format(total_tokens * price) + "\n"
                msg = msg + indent + "**Claimable by yearn: " + str(round(claimable,2)) + " " + token.symbol() + " " + "${:,.2f}".format(claimable_usd) + "**\n"
            # if env == "PROD" and claimable:
            bot.send_message(chat_id, msg, parse_mode="markdown", disable_web_page_preview = True)
            print(msg)