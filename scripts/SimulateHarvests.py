from .TelegramBot import sendMessage
import brownie
from utils import dotdict
import json
from brownie import interface, accounts, web3, chain
from brownie.network.event import _decode_logs
from babel.dates import format_timedelta
from datetime import datetime
import pandas as pd

def main():
    gov = accounts.at(web3.ens.resolve("ychad.eth"), force=True)
    treasury = accounts.at(web3.ens.resolve("treasury.ychad.eth"), force=True)
    strategiesHelperAddress = "0xae813841436fe29b95a14AC701AFb1502C4CB789"
    oracleAddress = "0x83d95e0D5f402511dB06817Aff3f9eA88224B030"
    oracle = interface.IOracle(oracleAddress)
    strategies_helper = interface.IStrategiesHelper(strategiesHelperAddress)
    strategies_addresses = strategies_helper.assetsStrategiesAddresses()
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
        # (data) = pre_harvest_custom(data)
        if data.pre.debt > 0:
            (data) = harvest(data)
            if data.harvest_success:
                (data) = post_harvest(data)
                # (data) = post_harvest_custom(data)
                # (data) = configure_alerts(data)
                # (data) = configure_alerts_custom(data)
                (data) = build_telegram_message(data)
        chain.reset()
        continue

def pre_harvest(data):
    # Set basic strat/vault/token data values
    strategy_address = data.strategy_address
    strategy = interface.IStrategy(strategy_address)
    data.strategy = strategy
    data.vault_address = strategy.vault()
    vault = interface.IVault032(data.vault_address)
    data.vault = vault
    vault_address = strategy.vault()
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
        vault_version = int(vault.apiVersion().replace(".", ""))
        if vault_version == 30:
            vault = interface.IVault030(vault_address)
        if vault_version == 31:
            vault = interface.IVault031(vault_address)

        # State before harvest
        strategy_params = vault.strategies(strategy)
        data.pre.debt = strategy_params.dict()["totalDebt"]
        data.pre.gain = strategy_params.dict()["totalGain"]
        data.pre.loss = strategy_params.dict()["totalLoss"]
        data.pre.last_report = strategy_params.dict()["lastReport"]
        data.pre.desired_ratio = "{:.4%}".format(strategy_params.dict()["debtRatio"] / 10000)
        data.pre.debt_outstanding = vault.debtOutstanding(strategy_address)
        data.pre.price_per_share = vault.pricePerShare()
        data.pre.total_assets = vault.totalAssets()
        data.pre.actual_ratio = data.pre.debt / (data.pre.total_assets + 1)
        data.pre.treasury_fee_balance = vault.balanceOf(data.treasury)
        data.pre.strategist_fee_balance = vault.balanceOf(strategy)
        try:
            data.pre.harvest_trigger = strategy.harvest_trigger(2_000_000 * 300 * 1e9)
        except:
            data.pre.harvest_trigger_ready = "Broken"
    return data

def harvest(data):
    # Perform harvest and wait
    try:
        data.strategy.harvest({"from": data.gov})
        data.harvest_success = True
    except:
        print("Can't harvest", data.strategy_name, data.strategy_address)
        data.harvest_success = False
    
    chain.sleep(60 * 60 * data.config.hours_to_wait)
    chain.mine(data.config.blocks_to_mine)

    return data

def post_harvest(data):
    strategy_address = data.strategy_address

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
    d = data.token_decimals
    data.post.debt_delta = (data.post.debt - data.pre.debt) / 10**d
    data.post.gain_delta = (data.post.gain - data.pre.gain) / 10**d
    data.post.loss_delta = (data.post.loss - data.pre.loss) / 10**d
    data.post.debt_outstanding_delta = (
        (data.post.debt_outstanding - data.pre.debt_outstanding) / 10**d
    )
    data.post.last_report_delta = data.post.last_report - data.pre.last_report
    data.time_since_last_harvest = format_timedelta(data.post.last_report_delta, locale="en_US") + " ago"
    data.post.total_assets_delta = data.post.total_assets - data.pre.total_assets
    data.post.price_per_share_in_decimals = data.vault.pricePerShare() / 10**d
    pps = data.post.price_per_share_in_decimals
    data.post.treasury_fee_delta = (data.post.treasury_fee_balance - data.pre.treasury_fee_balance) / 10**d * pps
    data.post.strategist_fee_delta = (data.post.strategist_fee_balance - data.pre.strategist_fee_balance) / 10**d * pps
    data.post.total_fee_delta = (data.post.treasury_fee_delta + data.post.strategist_fee_delta)

    # Calculate and format results
    percent = 0
    if data.pre.debt > 0:
        if data.post.loss_delta > data.post.gain_delta:
            percent = -1 * data.post.loss_delta / data.pre.debt
            percent2 = -1 * (data.post.loss_delta + data.post.total_fee_delta) / data.pre.debt
        else:
            percent = data.post.gain_delta / data.pre.debt
            percent2 = (data.post.gain_delta - data.post.total_fee_delta) / data.pre.debt
    data.post.est_apr_before_fees = percent * 3.154e7 / data.post.last_report_delta
    data.post.est_apr_after_fees = percent2 * 3.154e7 / data.post.last_report_delta
    data.post.pps_percent_change = (
        (data.post.price_per_share - data.pre.price_per_share)
        / data.pre.price_per_share
    ) * 100

    return data
    
def build_telegram_message(data):
    
    est_apr_before_fees = "{:.4%}".format(data.post.est_apr_before_fees)
    est_apr_after_fees = "{:.4%}".format(data.post.est_apr_after_fees)
    

    # profitInUsd = (
    #     f"${oracle.getNormalizedValueUsdc(tokenAddress, gainDelta) / 10 ** 6:,.2f}"
    # )
    # lossInUsd = (
    #     f"${oracle.getNormalizedValueUsdc(tokenAddress, lossDelta) / 10 ** 6:,.2f}"
    # )

    profitInUnderlying = f"{data.post.gain_delta} {data.token_symbol}"

    share_price_OK = (
        data.post.pps_percent_change >= 0
        and data.post.price_per_share < 1
        and data.post.price_per_share >= 1 ** data.token_symbol
    )
    profit_and_loss_OK = data.post.gain_delta >= 0 and data.post.loss_delta == 0
    everything_OK = share_price_OK and profit_and_loss_OK

    def boolDescription(bool):
        return "TRUE" if bool else "FALSE"
    def passFail(bool):
        return "PASSED" if bool else "FAILED"


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
        df["Total Debt before"] = f"{data.pre.debt / 10**data.token_decimals}"
        df["Total Gain before"] = f"{data.pre.gain / 10**data.token_decimals}"
        df["Total Loss before"] = f"{data.pre.loss / 10**data.token_decimals}"
        df["Target debt ratio"] = f"{data.pre.desired_ratio}"
        df["Actual debt ratio"] = f"{data.pre.actual_ratio}"
        df["Harvest trigger"] = f"{boolDescription(data.pre.harvest_trigger)}"
        df[" "] = f""
        df["----- HARVEST SIMULATION DATA-------"] = f""
        df["Last harvest"] = f"{data.time_since_last_harvest}"
        df["Profit on harvest"] = f"{profitInUnderlying}"
        # df["Profit in USD"] = f"{profitInUsd}"
        df["Loss on harvest"] = f"{data.post.loss_delta}"
        # df["Loss in USD"] = f"{lossInUsd}"
        df["Debt delta"] = f"{data.post.debt_delta}"
        df["Treasury fees"] = f"{data.post.treasury_fee_delta}"
        df["Strategist fees"] = f"{data.post.strategist_fee_delta}"
        df["Total fees"] = f"{data.post.total_fee_delta}"
        df["APR before fees"] = f"{est_apr_before_fees}"
        df["APR after fees"] = f"{est_apr_after_fees}"
        df["Previous PPS"] = f"{data.pre.price_per_share / 10**data.token_decimals}"
        df["New PPS"] = f"{data.post.price_per_share / 10**data.token_decimals}"
        df["PPS percent change"] = f"{data.pps_percent_change}"
        df[" "] = f""
        df["----- HEALTH CHECKS-------"] = f""
        df["Share price change"] = f"{passFail(share_price_OK)}"
        df["Profit/loss check"] = f"{passFail(profit_and_loss_OK)}"

        sendMessage(df.T.to_string())

    return data

def generate_alerts(strategy_address, data, custom):
    test = "test"