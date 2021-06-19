from .TelegramBot import sendMessage
import brownie
from brownie import interface, accounts, web3, chain
from brownie.network.event import _decode_logs
from babel.dates import format_timedelta
from datetime import datetime
import pandas as pd

def main():
    daddy = accounts.at(web3.ens.resolve("ychad.eth"), force=True)
    treasury = accounts.at(web3.ens.resolve("treasury.ychad.eth"), force=True)
    strategiesHelperAddress = "0xae813841436fe29b95a14AC701AFb1502C4CB789"
    oracleAddress = "0x83d95e0D5f402511dB06817Aff3f9eA88224B030"
    oracle = interface.IOracle(oracleAddress)
    strategiesHelper = interface.IStrategiesHelper(strategiesHelperAddress)
    strategiesAddresses = strategiesHelper.assetsStrategiesAddresses()
    for strategyAddress in strategiesAddresses:
        strategy = interface.IStrategy(strategyAddress)
        vaultAddress = strategy.vault()
        vault = interface.IVault032(vaultAddress)
        tokenAddress = vault.token()
        token = interface.IERC20(tokenAddress)
        tokenDecimals = token.decimals()
        dust = 10**(token.decimals() / 2)
        if strategy.isActive() and strategy.estimatedTotalAssets() > dust:
            strategyName = strategy.name()
            print(strategyName + " - " + strategyAddress)
            strategyApiVersion = strategy.apiVersion()
            strategist = strategy.strategist()
            
            vaultName = vault.name()
            
            tokenSymbol = token.symbol()
            tokenDecimals = token.decimals()
            vaultVersion = int(vault.apiVersion().replace(".", ""))
            if vaultVersion == 30:
                vault = interface.IVault030(vaultAddress)
            if vaultVersion == 31:
                vault = interface.IVault031(vaultAddress)

            # State before harvest
            strategyStatistics = vault.strategies(strategy)
            debtBeforeHarvest = strategyStatistics.dict()["totalDebt"]
            gainBeforeHarvest = strategyStatistics.dict()["totalGain"]
            lossBeforeHarvest = strategyStatistics.dict()["totalLoss"]
            reportBeforeHarvest = strategyStatistics.dict()["lastReport"]
            debtOutstandingBeforeHarvest = vault.debtOutstanding(strategyAddress)
            pricePerShareOriginal = vault.pricePerShare()
            assetsBeforeHarvest = vault.totalAssets()
            actualRatio = debtBeforeHarvest / (assetsBeforeHarvest + 1)
            treasuryFeesBefore = vault.balanceOf(treasury)
            strategistFeesBefore = vault.balanceOf(strategy)

            try:
                harvestTriggerReady = strategy.harvestTrigger(2_000_000 * 300 * 1e9)
            except:
                harvestTriggerReady = "Broken"

            # Perform harvest and wait
            hoursToWait = 10
            try:
                strategy.harvest({"from": daddy})
            except:
                print("Can't harvest", strategyAddress)
                chain.reset()
                continue
            chain.sleep(60 * 60 * hoursToWait)
            chain.mine(1)

            # State after harvest
            strategyStatistics = vault.strategies(strategy)
            pricePerShareAfterTenHours = vault.pricePerShare()
            debtAfterHarvest = strategyStatistics.dict()["totalDebt"]
            gainAfterHarvest = strategyStatistics.dict()["totalGain"]
            lossAfterHarvest = strategyStatistics.dict()["totalLoss"]
            reportAfterHarvest = strategyStatistics.dict()["lastReport"]
            debtOutstandingAfterHarvest = vault.debtOutstanding(strategyAddress)
            assetsAfterHarvest = vault.totalAssets()
            treasuryFeesAfter = vault.balanceOf(treasury)
            strategistFeesAfter = vault.balanceOf(strategy)

            # State delta
            debtDelta = (debtAfterHarvest / 10**tokenDecimals) - (debtBeforeHarvest / 10**tokenDecimals)
            gainDelta = (gainAfterHarvest / 10**tokenDecimals) - (gainBeforeHarvest / 10**tokenDecimals)
            lossDelta = (lossAfterHarvest / 10**tokenDecimals) - (lossBeforeHarvest / 10**tokenDecimals)
            debtOutstandingDelta = (
                (debtOutstandingAfterHarvest / 10**tokenDecimals) - (debtOutstandingBeforeHarvest / 10**tokenDecimals)
            )
            reportDelta = reportAfterHarvest - reportBeforeHarvest
            assetsDelta = assetsAfterHarvest - assetsBeforeHarvest
            npps = vault.pricePerShare() / 10**tokenDecimals
            treasuryFeesDelta = (treasuryFeesAfter - treasuryFeesBefore) / 10**tokenDecimals * npps
            strategistFeesDelta = (strategistFeesAfter - strategistFeesBefore) / 10**tokenDecimals * npps
            totalFeesDelta = (treasuryFeesDelta + strategistFeesDelta)

            # Calculate and format results
            percent = 0
            if debtBeforeHarvest > 0:
                if lossDelta > gainDelta:
                    percent = -1 * lossDelta / debtBeforeHarvest
                    percent2 = -1 * (lossDelta + totalFeesDelta) / debtBeforeHarvest
                else:
                    percent = gainDelta / debtBeforeHarvest
                    percent2 = (gainDelta - totalFeesDelta) / debtBeforeHarvest
            estAprBeforeFees = percent * 3.154e7 / reportDelta
            estAprAfterFees = percent2 * 3.154e7 / reportDelta
            lastHarvest = format_timedelta(reportDelta, locale="en_US") + " ago"
            desiredRatio = "{:.4%}".format(strategyStatistics.dict()["debtRatio"] / 10000)
            actualRatio = "{:.4%}".format(actualRatio)
            estAprBeforeFees = "{:.4%}".format(estAprBeforeFees)
            estAprAfterFees = "{:.4%}".format(estAprAfterFees)
            ppsPercentChange = (
                ((pricePerShareAfterTenHours - pricePerShareOriginal))
                / pricePerShareOriginal
            ) * 100

            profitInUsd = (
                f"${oracle.getNormalizedValueUsdc(tokenAddress, gainDelta) / 10 ** 6:,.2f}"
            )
            lossInUsd = (
                f"${oracle.getNormalizedValueUsdc(tokenAddress, lossDelta) / 10 ** 6:,.2f}"
            )
            profitInUnderlying = f"{gainDelta} {tokenSymbol}"

            sharePriceOk = (
                ppsPercentChange >= 0
                and ppsPercentChange < 1
                and pricePerShareAfterTenHours >= 1 ** tokenDecimals
            )
            profitAndLossOk = gainDelta >= 0 and lossDelta == 0
            everythingOk = sharePriceOk and profitAndLossOk

            def boolDescription(bool):
                return "TRUE" if bool else "FALSE"
            def passFail(bool):
                return "PASSED" if bool else "FAILED"


            if not everythingOk:
                df = pd.DataFrame(index=[''])
                df["ALERT 🚨"] = datetime.now().isoformat()
                df[" "] = f""
                df["----- STRATEGY DESCRIPTION-------"] = f""
                df[f"{strategyName}"] = ""
                df["Vault Name"] = f"{vaultName}"
                df["Strategy API Version"] = f"{strategyApiVersion}"
                df["Strategy address"] = f"{strategyAddress}"
                df["Token address"] = f"{tokenAddress}"
                df["Vault Address"] = f"{vaultAddress}"
                df["Strategist Address"] = f"{strategist}"
                df[" "] = f""
                df["----- STRATEGY PARAMS-------"] = f""
                df["Total Debt before"] = f"{debtBeforeHarvest / 10**tokenDecimals}"
                df["Total Gain before"] = f"{gainBeforeHarvest / 10**tokenDecimals}"
                df["Total Loss before"] = f"{lossBeforeHarvest / 10**tokenDecimals}"
                df["Target debt ratio"] = f"{desiredRatio}"
                df["Actual debt ratio"] = f"{actualRatio}"
                df["Harvest trigger"] = f"{boolDescription(harvestTriggerReady)}"
                df[" "] = f""
                df["----- HARVEST SIMULATION DATA-------"] = f""
                df["Last harvest"] = f"{lastHarvest}"
                df["Profit on harvest"] = f"{profitInUnderlying}"
                df["Profit in USD"] = f"{profitInUsd}"
                df["Loss on harvest"] = f"{lossDelta}"
                df["Loss in USD"] = f"{lossInUsd}"
                df["Debt delta"] = f"{debtDelta}"
                df["Treasury fees"] = f"{treasuryFeesDelta}"
                df["Strategist fees"] = f"{strategistFeesDelta}"
                df["Total fees"] = f"{totalFeesDelta}"
                df["APR before fees"] = f"{estAprBeforeFees}"
                df["APR after fees"] = f"{estAprAfterFees}"
                df["Previous PPS"] = f"{pricePerShareOriginal / 10**tokenDecimals}"
                df["New PPS"] = f"{pricePerShareAfterTenHours / 10**tokenDecimals}"
                df["PPS percent change"] = f"{ppsPercentChange}"
                df[" "] = f""
                df["----- HEALTH CHECKS-------"] = f""
                df["Share price change"] = f"{passFail(sharePriceOk)}"
                df["Profit/loss check"] = f"{passFail(profitAndLossOk)}"
                sendMessage(df.T.to_string())

            chain.reset()
