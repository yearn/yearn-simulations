from .TelegramBot import sendMessage
import brownie
from brownie import interface, accounts, web3, chain
from brownie.network.event import _decode_logs
from babel.dates import format_timedelta


def main():
    daddy = accounts.at(web3.ens.resolve("ychad.eth"), force=True)
    strategiesHelperAddress = "0xae813841436fe29b95a14AC701AFb1502C4CB789"
    oracleAddress = "0x83d95e0D5f402511dB06817Aff3f9eA88224B030"
    oracle = interface.IOracle(oracleAddress)
    strategiesHelper = interface.IStrategiesHelper(strategiesHelperAddress)
    strategiesAddresses = strategiesHelper.assetsStrategiesAddresses()
    for strategyAddress in strategiesAddresses:
        strategy = interface.IStrategy(strategyAddress)
        strategyName = strategy.name()
        strategyApiVersion = strategy.apiVersion()
        strategist = strategy.strategist()
        vaultAddress = strategy.vault()
        vault = interface.IVault032(vaultAddress)
        vaultName = vault.name()
        tokenAddress = vault.token()
        token = interface.IERC20(tokenAddress)
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

        # State delta
        debtDelta = debtAfterHarvest - debtBeforeHarvest
        gainDelta = gainAfterHarvest - gainBeforeHarvest
        lossDelta = lossAfterHarvest - lossBeforeHarvest
        debtOutstandingDelta = (
            debtOutstandingAfterHarvest - debtOutstandingBeforeHarvest
        )
        reportDelta = reportAfterHarvest - reportBeforeHarvest
        assetsDelta = assetsAfterHarvest - assetsBeforeHarvest

        # Calculate and format results
        percent = 0
        if debtBeforeHarvest > 0:
            if lossDelta > gainDelta:
                percent = -1 * lossDelta / debtBeforeHarvest
            else:
                percent = gainDelta / debtBeforeHarvest
        estimatedApr = percent * 3.154e7 / reportDelta
        lastHarvest = format_timedelta(reportDelta, locale="en_US") + " ago"
        desiredRatio = "{:.2%}".format(strategyStatistics.dict()["debtRatio"] / 10000)
        actualRatio = "{:.2%}".format(actualRatio)
        estimatedApr = "{:.0%}".format(estimatedApr)
        ppsPercentChange = (
            ((pricePerShareAfterTenHours - pricePerShareOriginal))
            / pricePerShareOriginal
        ) * 100

        profitInUsd = (
            f"${oracle.getNormalizedValueUsdc(tokenAddress, gainDelta) / 10 ** 6:,.2f}"
        )
        profitInUnderlying = f"{gainDelta / 10**tokenDecimals:,.2f} {tokenSymbol}"

        sharePriceOk = (
            ppsPercentChange >= 0
            and ppsPercentChange < 1
            and pricePerShareAfterTenHours >= 1 ** tokenDecimals
        )
        profitAndLossOk = (gainDelta > 0 and lossDelta == 0) or (
            lossDelta > 0 and gainDelta == 0
        )
        everythingOk = sharePriceOk and profitAndLossOk

        def boolDescription(bool):
            return "PASSED" if bool else "FAILED"

        if not everythingOk:
            diagnostic_report = (
                "ALERT\n"
                f"{strategyName}\n"
                f"Strategy address: {strategyAddress}\n"
                f"Token address: {tokenAddress}\n"
                f"Vault Address: {vaultAddress}\n"
                f"Strategist Address: {strategist}\n"
                f"Vault Name: {vaultName}\n"
                f"Strategy API Version: {strategyApiVersion}\n"
                f"Profit: {profitInUnderlying}\n"
                f"Normalized profit: {profitInUsd}\n"
                f"Loss: {lossDelta}\n"
                f"Last harvest: {lastHarvest}\n"
                f"Report delta: {reportDelta}\n"
                f"Estimated APR: {estimatedApr}\n"
                f"PPS percent change: {ppsPercentChange}\n"
                f"Previous PPS: {pricePerShareOriginal}\n"
                f"New PPS: {pricePerShareAfterTenHours}\n"
                f"Desired ratio: {desiredRatio}\n"
                f"Actual ratio: {actualRatio}\n"
                f"Debt Outstanding change: {debtOutstandingDelta}\n"
                f"Harvest trigger ready: {boolDescription(harvestTriggerReady)}\n"
                f"Share price change: {boolDescription(sharePriceOk)}\n"
                f"Profit/loss check: {boolDescription(profitAndLossOk)}\n"
            )

            sendMessage(diagnostic_report)

        chain.reset()
