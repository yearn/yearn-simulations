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

load_dotenv()
SSC_BOT_KEY = os.getenv("SSC_BOT_KEY")
USE_DYNAMIC_LOOKUP = os.getenv("USE_DYNAMIC_LOOKUP")
ENV = os.getenv("ENV")

def main():
    bot = telebot.TeleBot(SSC_BOT_KEY)
    report_string = []
    test_group = os.getenv("TEST_GROUP")
    prod_group = os.getenv("FTM_GROUP")
    if ENV == "PROD":
        chat_id = prod_group
    else:
        chat_id = test_group
    vaults = ["0x0DEC85e74A92c52b7F708c4B10207D9560CEFaf0","0x637eC617c86D24E421328e6CAEa1d92114892439","0xA6A0cA45c2ceF0c5C0E0B58A8Ddd59209378B76A"]
    
    # addresses_provider = interface.IAddressProvider("0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93")
    oracle = interface.bandoracle("0x56E2898E0ceFF0D1222827759B56B28Ad812f92F")
    strats = []
    for v in vaults:
        vault = assess_vault_version(v)
        strats = strats + fetch_strats_from_queue(vault)
    count = 0

    last_vault = ""
    for i, s in enumerate(strats):
        string = ""
        strat = interface.IStrategy32(s)
        vault = assess_vault_version(strat.vault())
        token = interface.IERC20(vault.token())
        token_price = get_price(oracle, token.address)
        # usd_tendable = token_price * token.balanceOf(s) / 10**token.decimals()
        params = vault.strategies(strat)
        last_report = params.dict()["lastReport"]
        seconds_since_report = int(time.time() - last_report)
        since_last = "%dd, %dhr, %dm" % dhms_from_seconds(seconds_since_report)
        hours_since_last = seconds_since_report/60/60

        target_ratio = params.dict()["debtRatio"]
        before_debt = params.dict()["totalDebt"]
        before_gain = params.dict()["totalGain"]
        before_loss = params.dict()["totalLoss"]
        
        assets = vault.totalAssets()
        actual_ratio = before_debt/(assets+1) 

        if target_ratio == 0 and actual_ratio < 0.01:
            continue
        
        count = count + 1
        hasHealthCheck = True
        try:
            if strat.doHealthCheck():
                hasHealthCheck = True
        except:
            hasHealthCheck = False
        gov = accounts.at(vault.governance(), force=True)
        try:
            print("Harvesting strategy: " + s)
            if hasHealthCheck:
                strat.setDoHealthCheck(False,{'from':gov})
            tx = strat.harvest({'from': gov})
        except:
            string = "\n\n" + strat.name() + s + "\n\U0001F6A8 Failed Harvest!\n"
            report_string.append(string)
            continue
        
        params = vault.strategies(strat)
        profit = params.dict()["totalGain"] - before_gain
        profit_usd = token_price * (profit / 10**token.decimals())
        
        loss = params.dict()["totalLoss"] - before_loss
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
        if hours_since_last > 200 or profit_usd > 50_000:
            harvest_indicator = "\U0001F468" + "\u200D" + "\U0001F33E "
        # if usd_tendable > 0:
        #     tend_indicator = "\U0001F33E "
        
        df = pd.DataFrame(index=[''])
        if last_vault != vault.address:
            df["---- " + vault.name() + " " +vault.apiVersion()] =  " ---------------"
            last_vault = vault.address
        name = strat.name()
        if name == "StrategyLenderYieldOptimiser":
            name = "Gen Lender"
        df[harvest_indicator+tend_indicator+name] = s
        df[vault.name() + " " + vault.apiVersion()] = vault.address
        df["Time Since Harvest: "] =      since_last
        df["Profit on Harvest USD"] =   "${:,.2f}".format(profit_usd)
        df["Ratio (Target | Actual):"] = "{:.2%}".format(target_ratio/10000) + ' | ' + "{:.2%}".format(actual_ratio)
        df["Debt Delta USD:"] =             "${:,.2f}".format(debt_delta_usd)
        df["Pre-fee APR:"] =              "{:.2%}".format(over_year)

        report_string.append(df.T.to_string())


    messages = []
    idx = 0
    for i, report in enumerate(report_string):
        if i % 5 == 0:
            idx = len(messages)
            messages.append("")
        messages[idx] = messages[idx] + report + "\n"
    
    for i,m in enumerate(messages):
        page = "Page " + str(i+1) + "/" + str(len(messages)) + "\n"
        m = f"```{m}\n```"
        if i == 0:
            m = "Vault TVL " + m
            m = str(count) + " total active strategies found.\n" + m
        else:
            m = page + m
        bot.send_message(chat_id, m, parse_mode="markdown", disable_web_page_preview = True)

def lookup_endorsed_vaults():
    registry_helper = Contract("0x3030c9462BD9AFeCE7536B66cc75071dE687Af4A")
    endorsed_vaults = registry_helper.getVaults()
    return endorsed_vaults

def fetch_strats_from_queue(vault):
    strats = []
    for i in range(0, 20):
        s = vault.withdrawalQueue(i)
        if s == ZERO_ADDRESS:
            break
        strats.append(s)
    return strats

def assess_vault_version(vault):
    if int(interface.IVault032(vault).apiVersion().replace(".", "")) > 31:
        return interface.IVault032(vault)
    else:
        return interface.IVault031(vault)

def get_price(oracle, token):
    token = interface.IERC20(token)
    symbol = token.symbol()
    if token.symbol() == "WFTM":
        symbol = "FTM"
    print(symbol)
    price = 0
    try:
        price = oracle.getReferenceData(symbol,"USD").dict()["rate"] / 1e18
    except:
        price = oracle.getReferenceData("USDC","USD").dict()["rate"] / 1e18
    return price

def dhms_from_seconds(seconds):
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)
	return (days, hours, minutes)
