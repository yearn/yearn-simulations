from .TelegramBot import sendMessageToTelegram, sendResultToTelegram
import brownie, importlib, time
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
    addresses_provider = interface.IAddressProvider("0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93")
    oracle = interface.IOracle(addresses_provider.addressById("ORACLE"))

    helper_address = "0x5b4F3BE554a88Bd0f8d8769B9260be865ba03B4a"
    strategies_helper = interface.IStrategiesHelper(helper_address)

    adapter = interface.IRegistryAdapterV2Vaults((addresses_provider.addressById("REGISTRY_ADAPTER_V2_VAULTS")))
    print(addresses_provider.addressById("REGISTRY_ADAPTER_V2_VAULTS"))
    prod_vaults = list(adapter.assetsAddresses())
    data = dotdict({})
    vaults = dotdict({})
    data.vaults = []

    for vault_address in prod_vaults:
        credit_sum = 0
        strategies_addresses = strategies_helper.assetStrategiesAddresses(vault_address)
        vault = interface.IVault032(vault_address)
        vault_version = int(vault.apiVersion().replace(".", ""))
        if vault_version == 30:
            vault = interface.IVault030(vault_address)
        if vault_version == 31:
            vault = interface.IVault031(vault_address)
        token = vault.token()
        decimals = vault.decimals()
        total_assets = vault.totalAssets()
        price = oracle.getPriceUsdcRecommended(token) / 10**6
        tvl_usd = price * (total_assets / 10**decimals)
        debt_ratio = 0
        try:
            debt_ratio = vault.debtRatio()
        except:
            continue
        unallocated_ratio = 0 if 10_000 - debt_ratio == 0 else ((10_000 - debt_ratio) / 10_000)
        unallocated_assets_usd = unallocated_ratio * tvl_usd
        print("\n---",vault.name()+" "+vault.apiVersion()+" "+vault.address+"---")

        
        strat_msg = ""
        for strat in strategies_addresses:
            credit = vault.creditAvailable(strat)
            lastReport = vault.strategies(strat).dict()["lastReport"]
            harvest_delta = format_timedelta(round(time.time()) - lastReport, locale="en_US") + " ago"
            credit_usd = (credit / 10**decimals) * price
            credit_sum += credit_usd
            #print("Value", oracle.getNormalizedValueUsdc(weth_address, credit*10**decimals) / 10**6)
            print(strat,interface.IStrategy32(strat).name(),"Credit available $","{:,.2f}".format(credit_usd),"Last harvest:",harvest_delta)
            strat_msg = strat_msg+"\n"+interface.IStrategy32(strat).name()+" "+strat+"\nCredit available $"+"{:,.2f}".format(credit_usd)+"\nLast harvest: "+harvest_delta+"\n"

        

        percent_tvl_uninvested = 0 if tvl_usd == 0 else credit_sum/tvl_usd
        vault_stats = []
        vault_stats.append("\nVault total idle credit $"+str("{:,.2f}".format(credit_sum)+"\n"))
        vault_stats.append(str("{:.2%}".format(percent_tvl_uninvested))+ " of total TVL is idle credit\n")
        vault_stats.append("Total unallocated ratio "+ str(round(unallocated_ratio)) + " BPS")
        print(''.join(vault_stats))

        # vault = dotdict({})
        # vault.credit_sum = credit_sum
        # vault.tvl_usd = tvl_usd
        # vault.percent_tvl_uninvested = percent_tvl_uninvested
        # vault.percent_tvl_uninvested_str = "{:.2%}".format(percent_tvl_uninvested)
        # vault.unallocated_ratio = unallocated_ratio

        if percent_tvl_uninvested > 0.01:
            header = "\n--- ",vault.name()+" "+vault.apiVersion()+" ---\n"+vault.address+"\n\n"
            message_str = ""
            print("------")
            for item in header:
                message_str = message_str + item
            for item in strat_msg:
                message_str = message_str + item
            for item in vault_stats:
                message_str = message_str + item
            sendMessageToTelegram(message_str, chat_id)

    # helper_address = "0x5b4F3BE554a88Bd0f8d8769B9260be865ba03B4a"
    # strategies_helper = interface.IStrategiesHelper(helper_address)
    # strategies_addresses = strategies_helper.assetStrategiesAddresses(vault_address)
    # for strategy_address in strategies_addresses:


    # oracle = interface.IOracle(oracle_address)
    # strategies_helper = interface.IStrategiesHelper(helper_address)
    # strategies_addresses = strategies_helper.assetStrategiesAddresses(vault_address)
    # simulation_iterator(strategies_addresses, simulation)