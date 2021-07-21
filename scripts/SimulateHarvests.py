from .TelegramBot import sendMessageToTelegram, sendResultToTelegram
import brownie, importlib
from utils import dotdict
import json, os, sys, re, requests
from brownie import interface, accounts, web3, chain
from dotenv import load_dotenv, find_dotenv
from brownie.network.event import _decode_logs
from babel.dates import format_timedelta
from datetime import datetime
import pandas as pd
from web3 import HTTPProvider

mode = "s" # strategy mode by default
load_dotenv()
env = os.environ.get("ENVIRONMENT") # Set environment
chat_id = 1
f = open("chatid.txt", "r", errors="ignore")
chat_id = f.read().strip()
fork_url = ""

def main():
    fork_base_url = "https://simulate.yearn.network/fork"
    fork_id = requests.post(fork_base_url, headers={}, json={"network_id": "1"}).json()['simulation_fork']['id']
    fork_url = f"{fork_base_url}/{fork_id}"
    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    web3.provider = HTTPProvider(fork_rpc_url, {"timeout": 600})
    print(web3.provider.endpoint_uri,web3.provider.isConnected())
    load_dotenv()
    f = open("address.txt", "r", errors="ignore")
    address = f.read().strip()
    helper_address = "0x5b4F3BE554a88Bd0f8d8769B9260be865ba03B4a"
    oracle_address = "0x83d95e0D5f402511dB06817Aff3f9eA88224B030"
    if check_if_vault(address):
        mode = "v"
    else:
        mode = "s"
    print("Forked at block #",chain.height)
    # single_address()
    if mode == "v":
        get_all_vault_strats(address,helper_address,oracle_address)
    if mode == "s":
        single_address(address)
    if mode == "a":
        get_all_addresses(helper_address, oracle_address)

def single_address(strategy_address):
    simulation_iterator([strategy_address])

def get_all_vault_strats(vault_address, helper_address, oracle_address):
    print("All strategies in vault: "+vault_address)
    oracle = interface.IOracle(oracle_address)
    strategies_helper = interface.IStrategiesHelper(helper_address)
    strategies_addresses = strategies_helper.assetStrategiesAddresses(vault_address)
    simulation_iterator(strategies_addresses)

def get_all_addresses(helper_address, oracle_address):
    oracle = interface.IOracle(oracle_address)
    strategies_helper = interface.IStrategiesHelper(helper_address)
    strategies_addresses = strategies_helper.assetsStrategiesAddresses()
    simulation_iterator(strategies_addresses)

def simulation_iterator(strategies_addresses):

    msg = str("Mainnet forked at block #: "+ "{:,}".format(chain.height)+ "\n\n"+str(len(strategies_addresses)))+" total strategies found.\n\nPlease wait while harvest(s) are queued ....."
    
    if env == "prod":
        sendMessageToTelegram(msg, chat_id)
    else:
        print(msg)
    

    gov = accounts.at(web3.ens.resolve("ychad.eth"), force=True)
    treasury = accounts.at(web3.ens.resolve("treasury.ychad.eth"), force=True)
    for strategy_address in strategies_addresses:
        data = dotdict({})
        data.pre = dotdict({}) # Here is where we'll keep all the pre-harvest data
        data.post = dotdict({}) # Here is where we'll keep all the post-harvest data
        data.config = dotdict({}) # Define configuration options
        data.strategy_address = strategy_address
        data.gov = gov
        data.treasury = treasury
        data.config.hours_to_wait = 10
        data.config.blocks_to_mine = 1
        
        (data) = pre_harvest(data)
        (data) = pre_harvest_custom(data)
        if data.pre.debt is not None and data.pre.debt > 0:
            (data) = harvest(data)
            (data) = post_harvest(data)
            (data) = post_harvest_custom(data)
            (data) = build_report(data)
            # (data) = configure_alerts(data)
            # (data) = configure_alerts_custom(data)
            # (data) = build_telegram_message(data)
        chain.reset()
        continue
    
    msg = "💪 Simulation Complete."
    if env == "prod":
        sendMessageToTelegram(msg, chat_id)
    else:
        print(msg)
    requests.delete(fork_url)
    


def pre_harvest(data):
    # Set basic strat/vault/token data values
    strategy_address = data.strategy_address
    strategy = interface.IStrategy32(strategy_address)
    strat_version = int(re.sub("[^0-9]", "", strategy.apiVersion()))
    if strat_version <= 31:
        strategy = interface.IStrategy30(strategy_address)
    if strat_version > 31:
        strategy = interface.IStrategy32(strategy_address)
    data.strategy = strategy
    data.vault_address = strategy.vault()
    vault = interface.IVault032(data.vault_address)
    vault_version = int(vault.apiVersion().replace(".", ""))
    if vault_version == 30:
        vault = interface.IVault030(data.vault_address)
    if vault_version == 31:
        vault = interface.IVault031(data.vault_address)
    vault_gov = vault.governance()
    if vault_gov != data.gov:
        gov = accounts.at(vault_gov, force=True)
        data.gov = gov
    data.vault = vault
    data.token_address = data.vault.token()
    data.token = interface.IERC20(data.token_address)
    data.token_decimals = data.token.decimals()
    data.token_symbol = data.token.symbol()
    dust = 10**(data.token_decimals / 2)
    if strategy.isActive() and strategy.estimatedTotalAssets() > dust:
        data.strategy_name = strategy.name()
        data.vault_name = vault.name()
        print(data.strategy_name + " - " + strategy_address)
        data.strategy_api_version = strategy.apiVersion()
        data.strategist = strategy.strategist()

        # State before harvest
        strategy_params = vault.strategies(strategy)
        data.pre.debt = strategy_params.dict()["totalDebt"]
        data.pre.gain = strategy_params.dict()["totalGain"]
        data.pre.loss = strategy_params.dict()["totalLoss"]
        data.pre.last_report = strategy_params.dict()["lastReport"]
        data.pre.desired_ratio = "{:.3%}".format(strategy_params.dict()["debtRatio"] / 10000)
        data.pre.debt_outstanding = vault.debtOutstanding(strategy_address)
        data.pre.price_per_share = vault.pricePerShare()
        data.pre.total_assets = vault.totalAssets()
        data.pre.actual_ratio = "{:.3%}".format(data.pre.debt / (data.pre.total_assets + 1))
        data.pre.treasury_fee_balance = vault.balanceOf(data.treasury)
        data.pre.strategist_fee_balance = vault.balanceOf(strategy)
        try:
            data.pre.harvest_trigger = strategy.harvest_trigger(2_000_000 * 300 * 1e9)
        except:
            data.pre.harvest_trigger_ready = "Broken"
    return data

def pre_harvest_custom(data):
    strategy_address = data.strategy_address
    s = f"s_{strategy_address}"
    try:
        spec = importlib.util.spec_from_file_location("module.name", f"./plugins/{s}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data.pre.custom = dotdict({})
        data = module.pre_harvest_custom(data)
    except:
        print("No custom pre-harvest script found for "+data.strategy_address)

    return data

def harvest(data):
    # Perform harvest and wait
    try:
        tx = data.strategy.harvest({"from": data.gov})
        data.harvest_success = True
    except:
        print("Can't harvest", data.strategy_name, data.strategy_address)
        data.harvest_success = False
    
    chain.sleep(60 * 60 * data.config.hours_to_wait)
    chain.mine(data.config.blocks_to_mine)
    return data

def post_harvest(data):
    if not data.harvest_success:
        return
    strategy_address = data.strategy_address
    d = 10 ** data.token_decimals

    # State after harvest
    strategy_params = data.vault.strategies(strategy_address)
    data.post.price_per_share = data.vault.pricePerShare()
    data.post.debt = strategy_params.dict()["totalDebt"]
    data.post.gain = strategy_params.dict()["totalGain"]
    data.post.loss = strategy_params.dict()["totalLoss"]
    data.post.desired_ratio = "{:.4%}".format(strategy_params.dict()["debtRatio"] / 10000)
    data.post.last_report = strategy_params.dict()["lastReport"]
    data.post.debt_outstanding = data.vault.debtOutstanding(data.strategy_address)
    data.post.total_assets = data.vault.totalAssets()
    data.post.treasury_fee_balance = data.vault.balanceOf(data.treasury)
    data.post.strategist_fee_balance = data.vault.balanceOf(data.strategy_address)
    
    # State delta
    d = 10 ** data.token_decimals
    data.post.debt_delta = (data.post.debt - data.pre.debt)
    data.post.gain_delta = (data.post.gain - data.pre.gain)
    data.post.loss_delta = (data.post.loss - data.pre.loss)
    data.post.debt_outstanding_delta = (
        (data.post.debt_outstanding - data.pre.debt_outstanding)
    )
    data.post.last_report_delta = data.post.last_report - data.pre.last_report
    data.time_since_last_harvest = format_timedelta(data.post.last_report_delta, locale="en_US") + " ago"
    data.post.total_assets_delta = data.post.total_assets - data.pre.total_assets
    data.post.price_per_share_in_decimals = data.vault.pricePerShare() / d
    pps = data.post.price_per_share_in_decimals
    data.post.treasury_fee_delta = (data.post.treasury_fee_balance - data.pre.treasury_fee_balance) * pps
    data.post.strategist_fee_delta = (data.post.strategist_fee_balance - data.pre.strategist_fee_balance) * pps
    data.post.total_fee_delta = (data.post.treasury_fee_delta + data.post.strategist_fee_delta)
    
    # Calculate and format results
    if data.pre.debt > 0:
        net_gain = data.post.gain_delta - data.post.loss_delta
        percent_pre_fee = net_gain / data.pre.debt
        percent_post_fee = (net_gain - data.post.total_fee_delta) / data.pre.debt

    data.post.est_apr_before_fees = (
        percent_pre_fee * 3.154e7 / data.post.last_report_delta # Extrapolate over 1yr
    )
    data.post.est_apr_after_fees = (
        percent_post_fee * 3.154e7 / data.post.last_report_delta # Extrapolate over 1yr
    )
    data.post.pps_percent_change = (
        (data.post.price_per_share - data.pre.price_per_share)
        / data.pre.price_per_share
    ) * 100

    return data

def post_harvest_custom(data):
    try:
        strategy_address = data.strategy_address
        s = f"s_{strategy_address}"
        spec = importlib.util.spec_from_file_location("module.name", f"./plugins/{s}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data.post.custom = dotdict({})
        data = module.post_harvest_custom(data)
    except:
        print("No custom post-harvest script found for "+data.strategy_address)

    return data

def build_report_custom(data):
    strategy_address = data.strategy_address
    s = f"s_{strategy_address}"
    try:
        spec = importlib.util.spec_from_file_location("module.name", f"./plugins/{s}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data.custom_report = dotdict({})
        data.custom_alerts = dotdict({})
        data = module.build_report_custom(data)
    except:
        print("Failed fetching custom report script")

    return data
    

def build_report(data):
    df = pd.DataFrame(index=[''])
    d = 10 ** data.token_decimals
    
    est_apr_before_fees = "{:.4%}".format(data.post.est_apr_before_fees)
    est_apr_after_fees = "{:.4%}".format(data.post.est_apr_after_fees)
    

    # profitInUsd = (
    #     f"${oracle.getNormalizedValueUsdc(tokenAddress, gainDelta) / 10 ** 6:,.2f}"
    # )
    # lossInUsd = (
    #     f"${oracle.getNormalizedValueUsdc(tokenAddress, lossDelta) / 10 ** 6:,.2f}"
    # )

    """
        default alerts
        1. share price
        2. loss check

        log_level must be one of the following strings:
                - "alert"
                - "warning"
                - "info"
    """

    i = []
    r = dotdict({})
    r.name = "Timestamp"
    r.value = datetime.now().isoformat()
    i, r = appender(i, r)
    r.name = "----- STRATEGY DESCRIPTION-------"
    r.value = ""
    i, r = appender(i, r)
    r.name = "Strategy Name"
    r.value = data.strategy_name
    i, r = appender(i, r)
    r.name = "Vault Name"
    r.value = data.vault_name
    i, r = appender(i, r)
    r.name = "Strategy API Version"
    r.value = data.strategy.apiVersion()
    i, r = appender(i, r)
    r.name = "Strategy address"
    r.value = data.strategy_address
    i, r = appender(i, r)
    r.name = "Token address"
    r.value = data.token_address
    i, r = appender(i, r)
    r.name = "Vault Address"
    r.value = data.vault_address
    i, r = appender(i, r)
    r.name = "Strategist address"
    r.value = data.strategist
    i, r = appender(i, r)
    r.name = "----- STRATEGY PARAMS-------"
    r.value = ""
    i, r = appender(i, r)
    r.name = "Total Debt before"
    r.value = "{:,}".format(data.pre.debt / d)
    i, r = appender(i, r)
    r.name = "Total Gain before"
    r.value = "{:,}".format(data.pre.gain / d)
    i, r = appender(i, r)
    r.name = "Total Loss before"
    r.value = "{:,}".format(data.pre.loss / d)
    i, r = appender(i, r)
    r.name = "Target debt ratio"
    r.value = f"{data.pre.desired_ratio}"
    i, r = appender(i, r)
    r.name = "Actual debt ratio"
    r.value = f"{data.pre.actual_ratio}"
    i, r = appender(i, r)
    r.name = "Harvest trigger"
    r.value = f"{bool_description(data.pre.harvest_trigger)}"
    i, r = appender(i, r)
    r.name = "----- HARVEST SIMULATION DATA-------"
    r.value = ""
    i, r = appender(i, r)
    r.name = "Last harvest"
    r.value = f"{data.time_since_last_harvest}"
    i, r = appender(i, r)
    r.name = "Net Profit on harvest"
    r.value = "{:,}".format((data.post.gain_delta / d) - (data.post.loss_delta / d))
    i, r = appender(i, r)
    r.name = "Debt delta"
    r.value = f"{data.post.debt_delta / d}"
    i, r = appender(i, r)
    r.name = "Treasury fees"
    r.value = "{:,}".format(data.post.treasury_fee_delta / d)
    i, r = appender(i, r)
    r.name = "Strategist fees"
    r.value = "{:,}".format(data.post.strategist_fee_delta / d)
    i, r = appender(i, r)
    r.name = "Total fees"
    r.value = "{:,}".format(data.post.total_fee_delta / d)
    i, r = appender(i, r)
    r.name = "APR before fees"
    r.value = f"{est_apr_before_fees}"
    i, r = appender(i, r)
    r.name = "APR after fees"
    r.value = f"{est_apr_after_fees}"
    i, r = appender(i, r)
    r.name = "Previous PPS"
    r.value =  f"{data.pre.price_per_share / d}"
    i, r = appender(i, r)
    r.name = "New PPS"
    r.value = f"{data.post.price_per_share / d}"
    i, r = appender(i, r)
    r.name = "PPS percent change"
    r.value = f"{data.post.pps_percent_change}"
    i, r = appender(i, r)
    r.name = "Total fees"
    r.value = "{:,}".format(data.post.total_fee_delta / d)
    i, r = appender(i, r)
    r.name = "----- DEFAULT ALERTS -------"
    r.value = ""
    i, r = appender(i, r)
    data.report = i

    """
        FORMAT REPORT
    """
    # Default Data
    for idx in i:
        df[idx.name] = f"{idx.value}"

    # Default alerts
    data = configure_alerts(data)
    data.highest_alert_level = "info"
    try:
        for i in data.alerts:
            df[i.name] = f"{pass_fail(i)}"
            if i.value:
                if i.log_level == "warning" and data.highest_alert_level != "alert":
                    data.highest_alert_level = "warning"
                if i.log_level == "alert":
                    data.highest_alert_level = "alert"
    except:
        print("Error setting up default alerts")

    
    # Custom Data
    data = build_report_custom(data)

    try:
        if len(data.custom_report) > 0:
            df[" "] = " "
            df[" "] = " "
            df[" "] = " "
            df[" "] = " "
            df["----- CUSTOM REPORT -------"] = ""
            for i in data.custom_report:
                df[i.name] = f"{i.value}"
    except:
        print("Error setting up custom data")

    # Custom Alerts
    try:
        if len(data.custom_alerts) > 0:
            df["----- CUSTOM ALERTS -------"] = ""
            for i in data.custom_alerts:
                df[i.name] = f"{pass_fail(i)}"
                if i.log_level == "warning" and data.highest_alert_level != "alert":
                    data.highest_alert_level = "warning"
                if i.log_level == "alert":
                    data.highest_alert_level = "alert"
    except:
        print("Error setting up custom alerts")


    if env == "prod":
        sendResultToTelegram(df.T.to_string(), chat_id)
    else:
        print(df.T.to_string())
    return data

def configure_alerts(data):
    alerts = []
    alert = dotdict({})
    alert.name = "Share price check"
    alert.value = (
        data.post.pps_percent_change >= 0
        and data.post.pps_percent_change < 1 # make sure it doesnt go too high
        and data.post.price_per_share >= 1 ** data.token_decimals
    )
    alert.log_level = "alert"
    alerts, alert = appender(alerts, alert)
    alert.name = "Loss check"
    alert.value = (data.post.loss_delta == 0)
    alert.log_level = "alert"
    alerts, alert = appender(alerts, alert)
    data.alerts = alerts

    return data

def appender(arr, obj):
    arr.append(obj)
    obj = dotdict({})
    return arr, obj

def generate_alerts(strategy_address, data, custom):
    test = "test"

def check_if_vault(addr):
    vault = interface.IVault032(addr)
    strat = interface.IStrategy32(addr)
    isVault = False
    try:
        vault.pricePerShare()
        return True
    except:
        try:
            strat.estimatedTotalAssets()
            return False
        except:
            return False

def bool_description(bool):
        return "TRUE" if bool else "FALSE"

def pass_fail(item):
    if item.value:
        return "✅"
    else:
        if item.log_level == "warning":
            return "⚠"
        if item.log_level == "info":
            return "ℹ"
        else:
            return "🚨"
    #return "PASSED" if bool else "FAILED"
    