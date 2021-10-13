from .TelegramBot import sendMessageToTelegram, sendResultToTelegram
import importlib
from utils import dotdict
import json, os, sys, re, requests
from brownie import interface, accounts, web3, chain
from dotenv import load_dotenv, find_dotenv
from brownie.network.event import _decode_logs
from babel.dates import format_timedelta
from ReportBuilder import appender, report_builder, bool_description, pass_fail
from apr import report_apr, calc_apr
from datetime import datetime
import pandas as pd
from web3 import HTTPProvider

mode = "sim" # strategy mode by default
address_type = "strategy"
load_dotenv()
env = os.environ.get("ENVIRONMENT") # Set environment
chat_id = 1
f = open("chatid.txt", "r", errors="ignore")
chat_id = f.read().strip()
fork_url = ""

def main():
    chain.snapshot()
    load_dotenv()
    # fork_base_url = "https://simulate.yearn.network/fork"
    # fork_id = requests.post(fork_base_url, headers={}, json={"network_id": "1"}).json()['simulation_fork']['id']
    # fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    # web3.provider = HTTPProvider(fork_rpc_url, {"timeout": 600})
    print(web3.provider.endpoint_uri,web3.provider.isConnected())
    simulation = dotdict({})
    simulation.apr = dotdict({})
    simulation.apr.strategies = []
    simulation.apr.pre_fee_apr_total = 0
    simulation.apr.post_fee_apr_total = 0
    f = open("address.txt", "r", errors="ignore")
    address = f.read().strip()
    simulation.address = address
    f = open("mode.txt", "r", errors="ignore")
    simulation.mode = f.read().strip()
    helper_address = "0x5b4F3BE554a88Bd0f8d8769B9260be865ba03B4a"
    oracle_address = "0x83d95e0D5f402511dB06817Aff3f9eA88224B030"

    if address == "all":
        simulation.address_type = "all"
        get_all_addresses(helper_address, oracle_address, simulation)
    elif check_if_vault(address):
        simulation.address_type = "vault"
        get_all_vault_strats(address, helper_address, oracle_address, simulation)
    else:
        simulation.address_type = "strategy"
        single_address(address, simulation)
    print("Forked at block #",chain.height)


def single_address(strategy_address, simulation):
    simulation_iterator([strategy_address], simulation)

def get_all_vault_strats(vault_address, helper_address, oracle_address, simulation):
    print("All strategies in vault: "+vault_address)
    oracle = interface.IOracle(oracle_address)
    strategies_helper = interface.IStrategiesHelper(helper_address)
    strategies_addresses = strategies_helper.assetStrategiesAddresses(vault_address)
    simulation_iterator(strategies_addresses, simulation)

def get_all_addresses(helper_address, oracle_address, simulation):
    oracle = interface.IOracle(oracle_address)
    strategies_helper = interface.IStrategiesHelper(helper_address)
    strategies_addresses = strategies_helper.assetsStrategiesAddresses()
    simulation_iterator(strategies_addresses, simulation)

def simulation_iterator(strategies_addresses, simulation):
    run_report = []
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
        data.should_harvest = data.pre.debt is not None and data.pre.debt > 0
        if data.should_harvest:
            (data) = harvest(data)
            (data) = post_harvest(data)
            (data) = post_harvest_custom(data)
            (data) = build_report(data)
            # (data) = configure_alerts(data)
            # (data) = configure_alerts_custom(data)
            # (data) = build_telegram_message(data)
            data, simulation = calc_apr(data, simulation)
        report = dotdict({})
        run_report.append(report)
        chain.reset()
        # chain.revert()
        continue
    
    msg = "💪 Simulation Complete.\n"
    if env == "prod":
        if simulation.address_type == "vault":
            report_string = report_apr(data, simulation)
            sendResultToTelegram(report_string, chat_id)
        sendMessageToTelegram(msg, chat_id)
    else:
        if simulation.address_type == "vault":
            report_string = report_apr(data, simulation)
            print(report_string)
        print(msg)
    


def pre_harvest(data):
    # Set basic strat/vault/token data values
    strategy_address = data.strategy_address
    data.hasHealthChecks = False
    strategy = interface.IStrategy32(strategy_address)
    strat_version = int(re.sub("[^0-9]", "", strategy.apiVersion()))
    if strat_version <= 31:
        strategy = interface.IStrategy30(strategy_address)
    if strat_version > 31:
        strategy = interface.IStrategy042(strategy_address)
        try:
            strategy.doHealthCheck()
            data.hasHealthChecks = True
        except:
            data.hasHealthChecks = False

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
        data.pre.desired_ratio = strategy_params.dict()["debtRatio"] / 10000
        data.pre.desired_ratio_str = "{:.3%}".format(data.pre.desired_ratio)
        data.pre.debt_outstanding = vault.debtOutstanding(strategy_address)
        data.pre.price_per_share = vault.pricePerShare()
        data.pre.total_assets = vault.totalAssets()
        data.pre.actual_ratio = data.pre.debt / (data.pre.total_assets + 1)
        data.pre.actual_ratio_str = "{:.3%}".format(data.pre.actual_ratio)
        data.pre.treasury_fee_balance = vault.balanceOf(data.treasury)
        data.pre.strategist_fee_balance = vault.balanceOf(strategy)
        try:
            data.pre.harvest_trigger = strategy.harvest_trigger(2_000_000 * 300 * 1e9)
        except:
            data.pre.harvest_trigger_ready = "Broken"
        if data.hasHealthChecks:
            data.strategy.setDoHealthCheck(False,{'from':data.gov})
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
        tx = data.strategy.harvest({"from": data.gov, "gas_limit": 8000000})
        data.harvest_success = True
        chain.sleep(60 * 60 * data.config.hours_to_wait)
        chain.mine(data.config.blocks_to_mine)
    except:
        e = sys.exc_info()[0]
        print("Can't harvest", data.strategy_name, data.strategy_address)
        data.harvest_success = False
    
    return data

def post_harvest(data):
    # if not data.harvest_success:
    #     return data
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
        percent_pre_fee * 3.154e7 / data.post.last_report_delta if data.post.last_report_delta != 0 else 0 # Extrapolate over 1yr
    )
    data.post.est_apr_after_fees = (
        percent_post_fee * 3.154e7 / data.post.last_report_delta if data.post.last_report_delta != 0 else 0 # Extrapolate over 1yr
    )
    data.post.pps_percent_change = (
        (data.post.price_per_share - data.pre.price_per_share)
        / data.pre.price_per_share
    ) * 100

    return data

def post_harvest_custom(data):
    strategy_address = data.strategy_address
    try:
        s = f"s_{strategy_address}"
        spec = importlib.util.spec_from_file_location("module.name", f"./plugins/{s}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data.post.custom = dotdict({})
        data = module.post_harvest_custom(data)
    except:
        print("No custom post-harvest script found for "+strategy_address)

    return data
    

def build_report(data):
    """
        default alerts
        1. share price
        2. loss check

        log_level must be one of the following strings:
                - "alert"
                - "warning"
                - "info"
    """

    data, report_string = report_builder(data)

    # Default alerts
    
    # Custom Data
    #data= build_report_custom(data)
    if mode == "apr":
        print(mode)
        print(data.post.est_apr_before_fees)
        print(data.post.est_apr_after_fees)
        data.post.est_apr_before_fees
        data.post.est_apr_after_fees
    if env == "prod":
        sendResultToTelegram(report_string, chat_id)
    else:
        print(report_string)

    return data


def generate_alerts(strategy_address, data, custom):
    test = "test"

def check_if_vault(addr):
    vault = interface.IVault032(addr)
    strat = interface.IStrategy32(addr)
    try:
        vault.pricePerShare()
        return True
    except:
        try:
            strat.estimatedTotalAssets()
            return False
        except:
            return False



def output_aprs():
    print()