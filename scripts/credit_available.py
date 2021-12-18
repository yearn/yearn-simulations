import os
import time
from datetime import datetime

import telebot
from babel.dates import format_timedelta
from brownie import interface
from dotenv import load_dotenv
from scheduler import schedule_script

load_dotenv()
env = os.environ.get("ENV")  # Set environment
chat_id = os.environ.get("TELEGRAM_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID_CREDIT_TRACKER"))
bot_key = os.environ.get("TELEGRAM_BOT_KEY", os.environ.get("TELEGRAM_YFI_DEV_BOT"))


@schedule_script("@yfitestchannel", minute="30", hour="16")
def main():
    bot = telebot.TeleBot(bot_key)
    addresses_provider = interface.IAddressProvider(
        "0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93"
    )
    oracle = interface.IOracle(addresses_provider.addressById("ORACLE"))

    helper_address = "0x5b4F3BE554a88Bd0f8d8769B9260be865ba03B4a"
    strategies_helper = interface.IStrategiesHelper(helper_address)

    adapter = interface.IRegistryAdapterV2Vaults(
        (addresses_provider.addressById("REGISTRY_ADAPTER_V2_VAULTS"))
    )
    prod_vaults = list(adapter.assetsAddresses())

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
        price = oracle.getPriceUsdcRecommended(token) / 10 ** 6
        if price == 0:
            if (
                token
                == interface.IStrategy32(
                    "0xAF6F42bfB29e90dFe51f2341fF1B1f99Fd776A70"
                ).want()
            ):  # cvxcrv-f
                crv = "0xd533a949740bb3306d119cc777fa900ba034cd52"
                price = oracle.getPriceUsdcRecommended(crv) / 10 ** 6
            if (
                token
                == interface.IStrategy32(
                    "0xB431A88a6cFFfa66dBCf96Ebc89aE72Ff7Fcc34f"
                ).want()
            ):  # ibEUR-sEUR
                sEUR = "0xd71ecff9342a5ced620049e616c5035f1db98620"
                price = oracle.getPriceUsdcRecommended(crv) / 10 ** 6
        if price == 0:
            print("UNABLE TO GET PRICE ON", interface.IERC20(token).symbol(), strat)
        tvl_usd = price * (total_assets / 10 ** decimals)
        debt_ratio = 0
        try:
            debt_ratio = vault.debtRatio()
        except:
            continue
        unallocated_ratio = (
            0 if 10_000 - debt_ratio == 0 else ((10_000 - debt_ratio) / 10_000)
        )
        unallocated_assets_usd = unallocated_ratio * tvl_usd

        strat_msg = ""
        for strat in strategies_addresses:
            credit = vault.creditAvailable(strat)
            lastReport = vault.strategies(strat).dict()["lastReport"]
            totalDebt = vault.strategies(strat).dict()["totalDebt"]
            harvest_delta = (
                format_timedelta(round(time.time()) - lastReport, locale="en_US")
                + " ago"
            )
            if totalDebt > 0:
                credit_usd = (credit / 10 ** decimals) * price
                credit_sum += credit_usd
                if credit_usd > 500_000:
                    maxReportDelay = interface.IStrategy042(strat).maxReportDelay()
                    nextHarvestFormat = datetime.fromtimestamp(
                        lastReport + maxReportDelay
                    ).strftime("%A, %B %d, %Y %I:%M:%S")
                    nextHarvest = round(
                        (lastReport + maxReportDelay - round(time.time())) / 60 / 60
                    )
                    if nextHarvest < 0:
                        nextHarvest = "overdue"
                    else:
                        nextHarvest = str(nextHarvest) + " hrs"
                    strat_msg = (
                        strat_msg
                        + "   ["
                        + interface.IStrategy32(strat).name()
                        + "](https://etherscan.io/address/"
                        + strat
                        + ")\n   Credit available $"
                        + "{:,.2f}".format(credit_usd)
                        + "\n   Last harvest: "
                        + harvest_delta
                        + "\n   Est next harvest: "
                        + str(nextHarvest)
                        + "\n"
                    )

        percent_tvl_uninvested = 0 if tvl_usd == 0 else credit_sum / tvl_usd
        vault_stats = []
        vault_stats.append(
            "$"
            + str(
                "{:,.2f}".format(credit_sum)
                + " total idle credit in vault ("
                + str("{:.2%}".format(percent_tvl_uninvested))
                + " of TVL)\n"
            )
        )
        vault_stats.append(
            str(round(unallocated_ratio)) + " BPS unallocated debt ratio"
        )
        if (
            round(unallocated_ratio) > 500
            or percent_tvl_uninvested > 5
            or credit_sum > 1_500_000
        ):
            m = (
                "["
                + vault.name()
                + " "
                + vault.apiVersion()
                + "](https://etherscan.io/address/"
                + vault.address
                + ")\n"
            )
            m += "".join(vault_stats) + "\n\n"
            m += strat_msg
            print(m)
            if env == "PROD":
                bot.send_message(
                    chat_id, m, parse_mode="markdown", disable_web_page_preview=True
                )
