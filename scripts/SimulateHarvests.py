from .TelegramBot import sendMessage, sendResult
import brownie, importlib
from utils import dotdict
import json, os, sys, re
from dotenv import load_dotenv, find_dotenv
from brownie import interface, accounts, web3, chain
from dotenv import load_dotenv, find_dotenv
from brownie.network.event import _decode_logs
from babel.dates import format_timedelta
from datetime import datetime
import pandas as pd

mode = "s" # vault mode by default

def main():
    load_dotenv()
    f = open("address.txt", "r", errors="ignore")
    address = f.read().strip()
    address = address.strip()
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
    print("Single address")
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

    msg = str("Mainnet forked at block #: "+ str(chain.height)+ "\n\n"+str(len(strategies_addresses)))+" total strategies found.\n\nPlease wait while harvest(s) are queued ....."
    sendMessage(msg)

    gov = accounts.at(web3.ens.resolve("ychad.eth"), force=True)
    treasury = accounts.at(web3.ens.resolve("treasury.ychad.eth"), force=True)
    for strategy_address in strategies_addresses:
        data = dotdict({})
        data.pre = dotdict({}) # Here is where we'll keep all the pre-harvest data
        data.post = dotdict({}) # Here is where we'll keep all the post-harvest data
        data.custom = dotdict({}) # Here is where we'll keep all the custom strategy data
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
            # (data) = post_harvest_custom(data)
            # (data) = configure_alerts(data)
            # (data) = configure_alerts_custom(data)
            (data) = build_telegram_message(data)
        chain.reset()
        continue
    sendMessage("✅ Simulation Complete.")


def pre_harvest(data):
    # Set basic strat/vault/token data values
    strategy_address = data.strategy_address
    strategy = interface.IStrategy32(strategy_address)
    strat_version = int(re.search(r'\d+', strategy.apiVersion()).group())
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
        spec = importlib.util.spec_from_file_location("module.name", f"./custom_scripts/{s}.py")
        print(f"./custom_scripts/{s}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = module.pre_harvest_custom(data)
    except:
        print("No custom script found")
    
    print("-------")
    print(data.custom.pre)
    for i in data.custom.pre:
        print("Name:",i.name)
        print("Value:",i.value)
        print("-------")

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
    
def build_telegram_message(data):
    d = 10 ** data.token_decimals
    
    est_apr_before_fees = "{:.4%}".format(data.post.est_apr_before_fees)
    est_apr_after_fees = "{:.4%}".format(data.post.est_apr_after_fees)
    

    # profitInUsd = (
    #     f"${oracle.getNormalizedValueUsdc(tokenAddress, gainDelta) / 10 ** 6:,.2f}"
    # )
    # lossInUsd = (
    #     f"${oracle.getNormalizedValueUsdc(tokenAddress, lossDelta) / 10 ** 6:,.2f}"
    # )

    share_price_OK = (
        data.post.pps_percent_change >= 0
        and data.post.pps_percent_change < 1 # make sure it doesnt go too high
        and data.post.price_per_share >= 1 ** data.token_decimals
    )
    profit_and_loss_OK = data.post.gain_delta >= 0 and data.post.loss_delta == 0
    everything_OK = share_price_OK and profit_and_loss_OK

    def boolDescription(bool):
        return "TRUE" if bool else "FALSE"
    def passFail(bool):
        return "PASSED" if bool else "FAILED"

    everything_OK = False # Hardcoding this temporarily

    if not everything_OK:
        df = pd.DataFrame(index=[''])
        df["ALERT 🚨"] = datetime.now().isoformat()
        df[" "] = f""
        df["----- STRATEGY DESCRIPTION-------"] = f""
        df[f"{data.strategy_name}"] = ""
        df["Vault Name"] = f"{data.vault_name}"
        df["Strategy API Version"] = f"{data.strategy.apiVersion()}"
        df["Strategy address"] = f"{data.strategy_address}"
        df["Token address"] = f"{data.token_address}"
        df["Vault Address"] = f"{data.vault_address}"
        df["Strategist Address"] = f"{data.strategist}"
        df[" "] = f""

        df["----- STRATEGY PARAMS-------"] = f""
        df["Total Debt before"] = "{:,}".format(data.pre.debt / d)
        df["Total Gain before"] = "{:,}".format(data.pre.gain / d)
        df["Total Loss before"] = "{:,}".format(data.pre.loss / d)
        df["Target debt ratio"] = f"{data.pre.desired_ratio}"
        df["Actual debt ratio"] = f"{data.pre.actual_ratio}"
        df["Harvest trigger"] = f"{boolDescription(data.pre.harvest_trigger)}"
        df[" "] = f""

        df["----- HARVEST SIMULATION DATA-------"] = f""
        df["Last harvest"] = f"{data.time_since_last_harvest}"
        df["Net Profit on harvest"] = "{:,}".format((data.post.gain_delta / d) - (data.post.loss_delta / d))
        # df["Profit in USD"] = f"{profitInUsd}"
        # df["Loss on harvest"] = f"{data.post.loss_delta / d}"
        # df["Loss in USD"] = f"{lossInUsd}"
        df["Debt delta"] = f"{data.post.debt_delta / d}"
        df["Treasury fees"] = "{:,}".format(data.post.treasury_fee_delta / d)
        df["Strategist fees"] = "{:,}".format(data.post.strategist_fee_delta / d)
        df["Total fees"] = "{:,}".format(data.post.total_fee_delta / d)
        df["APR before fees"] = f"{est_apr_before_fees}"
        df["APR after fees"] = f"{est_apr_after_fees}"
        df["Previous PPS"] = f"{data.pre.price_per_share / d}"
        df["New PPS"] = f"{data.post.price_per_share / d}"
        df["PPS percent change"] = f"{data.pps_percent_change}"
        df[" "] = f""
        
        df["----- HEALTH CHECKS-------"] = f""
        df["Share price change"] = f"{passFail(share_price_OK)}"
        df["Profit/loss check"] = f"{passFail(profit_and_loss_OK)}"
        
        df["----- CUSTOM DATA -------"] = f""
        for i in data.custom.pre:
            df[i.name] = f"{i.value}"

        sendResult(df.T.to_string())

    return data

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
        print("Not a vault")
        try:
            strat.estimatedTotalAssets()
            return False
        except:
            print("Hmm, not a strat either")
            return False