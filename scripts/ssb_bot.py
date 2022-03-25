import os

from dotenv import load_dotenv
import pandas as pd, requests
import datetime
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

load_dotenv()
SSB_BOT_KEY = os.getenv("TELEGRAM_YFI_DEV_BOT")
USE_DYNAMIC_LOOKUP = os.getenv("USE_DYNAMIC_LOOKUP")
ENV = os.getenv("ENV")

CHAIN_VALUES = {
    1: {
        "NETWORK_NAME": "Ethereum Mainnet",
        "NETWORK_SYMBOL": "ETH",
        "ADDRESS_PROVIDER": "0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93",
        "EMOJI": "🇪🇹",
        "PROFIT_TARGET_USD": 65_000
    },
    250: {
        "NETWORK_NAME": "Fantom",
        "NETWORK_SYMBOL": "FTM",
        "ADDRESS_PROVIDER": "0xac5A9E4135A3A26497F3890bFb602b06Ee592B61",
        "EMOJI": "👻",
        "PROFIT_TARGET_USD": 5_000
    }
}
def main():

    bot = telebot.TeleBot(SSB_BOT_KEY)
    report_string = []
    test_group = os.getenv("TEST_GROUP")
    prod_group = os.getenv("YFI_BALANCER_COMMITTEE")
    if ENV == "PROD":
        chat_id = prod_group
    else:
        chat_id = test_group
    strategies = lookup_strategies()
    strategies.append("0x5Df3E97e96FC04ae1F75A9D07A141348E4B07E45") # fBEETS compounder
    addresses_provider = interface.IAddressProvider(CHAIN_VALUES[chain.id]["ADDRESS_PROVIDER"])
    oracle = interface.IOracle(addresses_provider.addressById("ORACLE"))

    count = 0
    needs_tend = []
    needs_harvest = []
    for i, s in enumerate(strategies):
        string = ""
        strat = Contract(s)
        vault = assess_vault_version(strat.vault())
        token = interface.IERC20(vault.token())
        token_price = get_price(oracle, token.address)
        usd_tendable = token_price * token.balanceOf(s) / 10**token.decimals()
        gov = accounts.at(vault.governance(), force=True)
        params = vault.strategies(strat)
        last_report = params.dict()["lastReport"]
        seconds_since_report = int(time.time() - last_report)
        since_last = "%dd, %dhr, %dm" % dhms_from_seconds(seconds_since_report)

        target_ratio = params.dict()["debtRatio"]
        before_debt = params.dict()["totalDebt"]
        before_gain = params.dict()["totalGain"]
        before_loss = params.dict()["totalLoss"]

        try:
            b_vault = Contract(strat.balancerVault())
            amount_in_pool = b_vault.getPoolTokenInfo(strat.balancerPoolId(), strat.want())[0]
            if amount_in_pool * .95 < vault.debtOutstanding(s):
                m = f'\n\n🚨 Needs attention! Harvest fails due to debtoutstanding > pooled tokens {strat.address} {strat.name()}.'
                report_string.append(m)
                continue
        except:
            print("Skipping debtOutstanding check. Strategy is likely not an SSB.")
        assets = vault.totalAssets()
        actual_ratio = before_debt/(assets+1) 

        if target_ratio == 0 and actual_ratio < 0.01:
            print(f"Skipping {strat.address} due to no debt ratio.")
            continue
        
        count = count + 1
        try:
            print("Harvesting strategy: " + s)
            try:
                strat.setParams(
                    10_000,
                    10_000,
                    strat.maxSingleDeposit() * 10,
                    0,
                    {'from': gov}
                )
            except:
                print("Failed setting parameters. Strategy is likely not an SSB.")
            try:
                strat.doHealthCheck()
                strat.setDoHealthCheck(False, {'from': gov})
                tx = strat.harvest({'from': gov})
            except:
                tx = strat.harvest({'from': gov})
        except:
            string = "\n\n" + strat.name() + s + "\n\U0001F6A8 Failed Harvest!\n"
            print(string)
            report_string.append(string)
            continue
        params = vault.strategies(strat)
        profit = params.dict()["totalGain"] - before_gain
        loss = params.dict()["totalLoss"] - before_loss
        net_profit = profit - loss
        before_debt_usd = token_price * before_debt / 10**token.decimals()
        profit_usd = token_price * net_profit / 10**token.decimals()
        debt_delta = params.dict()["totalDebt"] - before_debt
        debt_delta_usd = token_price * debt_delta / 10**token.decimals()
        percent = 0
        if before_debt > 0:
            if loss > profit:
                percent = -1 * loss / before_debt 
            else:
                percent = profit / before_debt
        over_year = percent * 3.154e+7 / (seconds_since_report)

        # Set inidcators
        harvest_indicator = ""
        tend_indicator = ""
        # if hours_since_last > 200 or profit_usd > 50_000:
        if profit_usd > CHAIN_VALUES[chain.id]["PROFIT_TARGET_USD"]:
            harvest_indicator = "\U0001F468" + "\u200D" + "\U0001F33E "
            needs_harvest.append(strat)
        if usd_tendable > 0:
            tend_indicator = "\U0001F33E "
            needs_tend.append(strat)
        
        df = pd.DataFrame(index=[''])
        name = strat.name()
        df[harvest_indicator+tend_indicator + name] = s
        df[vault.name() + " " + vault.apiVersion()] = vault.address
        df["Time Since Harvest: "] =      since_last
        df["Profit on Harvest USD"] =   "${:,.2f}".format(profit_usd)
        df["Ratio (Target | Actual):"] = "{:.2%}".format(target_ratio/10000) + ' | ' + "{:.2%}".format(actual_ratio)
        df["Debt (Delta | Total):"] =             "${:,.2f}".format(debt_delta_usd) + ' | ' + "${:,.2f}".format(before_debt_usd)
        df["Pre-fee APR:"] =              "{:.2%}".format(over_year)
        if usd_tendable > 0:
            df["Tendable Amount in USD:"] = "{:,.2f}".format(usd_tendable)

        report_string.append(df.T.to_string())


    messages = []
    idx = 0
    for i, report in enumerate(report_string):
        if i % 5 == 0:
            idx = len(messages)
            messages.append("")
        messages[idx] = messages[idx] + report + "\n"
    
    chain_indicator = f'{CHAIN_VALUES[chain.id]["EMOJI"]} Chain ID: {chain.id} \n'
    for i,m in enumerate(messages):
        page = "Page " + str(i+1) + "/" + str(len(messages)) + "\n"
        m = f"```{m}\n```"
        if i == 0:
            m = chain_indicator + str(count) + " total active strategies found.\n" + m
        else:
            m = chain_indicator + page + m
        bot.send_message(chat_id, m, parse_mode="markdown", disable_web_page_preview = True)

def lookup_strategies():
    if USE_DYNAMIC_LOOKUP == "False":
        f = open("ssb_list.json", "r", errors="ignore")
        data = json.load(f)
        if chain.id == 1:
            strategies = data['mainnet_strategies']
        elif chain.id == 250:
            strategies = data['ftm_strategies']
    else:
        # Fetch all v2 strategies and query by name
        addresses_provider = Contract("0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93")
        strategies_helper = Contract(addresses_provider.addressById("HELPER_STRATEGIES"))
        v2_strategies = strategies_helper.assetsStrategiesAddresses()
        strategies = []
        for s in v2_strategies:
            strat = Contract(s)
            name = strat.name().lower()
            style1 = re.search("SingleSidedBalancer", name)
            if style1:
                vault = interface.IVault032(strat.vault())
                if vault.strategies(strat).dict()["debtRatio"] > 0:
                    strategies.append(s)
                    print("Found:",strat.address, vault.name(), strat.name())
                else:
                    print("Skipping...",strat.address, vault.name(), strat.name())
    return strategies

def assess_vault_version(vault):
    if int(interface.IVault032(vault).apiVersion().replace(".", "")) > 31:
        return interface.IVault032(vault)
    else:
        return interface.IVault031(vault)

def get_price(oracle, token):
    return oracle.getPriceUsdcRecommended(token) / 10**6

def dhms_from_seconds(seconds):
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)
	return (days, hours, minutes)