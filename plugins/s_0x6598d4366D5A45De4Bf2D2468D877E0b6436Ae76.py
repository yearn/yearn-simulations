import brownie
from utils import dotdict
from brownie import interface, accounts, web3, chain

def pre_harvest_custom(data):
    """
        data.pre.custom
            A namespace for storage of pre-harvest data
    """

    decimals = 10 ** data.token_decimals
    
    # Get some data
    s = interface.IStrategy(data.strategy_address)
    r = interface.IRewards(s.poolRewards())

    data.pre.custom.claimable = r.claimable(data.strategy_address) / 1e18
    data.pre.custom.lossProtectionBalance = s.lossProtectionBalance() / decimals
    
    return data

def post_harvest_custom(data):
    """
        data.custom.post
            A namespace for storage of post-harvest data
    """
    decimals = 10 ** data.token_decimals
    
    # Get some data
    s = interface.IStrategy(data.strategy_address)
    r = interface.IRewards(s.poolRewards())

    data.post.custom.claimable = r.claimable(data.strategy_address) / 1e18
    data.post.custom.lossProtectionBalance = s.lossProtectionBalance()
    
    return data

def build_report_custom(data):
    """
        data.custom_report
            add name/value array to be displayed in report

        data.custom_alerts
            add name/value/log_level array to be displayed in report
            value must be boolean 
            log_level must be one of the following strings:
                - "alert"
                - "warning"
                - "info"
    """

    # Custom Reports Setup
    s = interface.IStrategy(data.strategy_address)

    hiddenProfit = (s.calcWantHeldInVesper() / 1e8) - (data.post.debt / 1e8)
    lossProtection = s.lossProtectionBalance() / 1e8
    protectionNeeded = (s.calculateProtectionNeeded() / 1e8) - hiddenProfit - lossProtection
    unSafeToHarvest = data.pre.custom.lossProtectionBalance > s.lossProtectionBalance()
    print("PRE",data.pre.custom.lossProtectionBalance)
    print("POST",s.lossProtectionBalance())

    reports = []
    report = dotdict({})
    report.name = "VSP claimed on harvest"
    report.value = data.pre.custom.claimable
    reports.append(report)
    report = dotdict({})
    report.name = "Total Realizable Withdraw Fee"
    report.value = s.calculateProtectionNeeded() / 1e8
    reports.append(report)
    report = dotdict({})
    report.name = "Loss Protection Balance"
    report.value = s.lossProtectionBalance() / 1e8
    reports.append(report)
    report = dotdict({})
    report.name = "Hidden Profit in Vesper"
    report.value = hiddenProfit
    reports.append(report)
    report = dotdict({})
    report.name = "Remaining Protection Needed"
    report.value = protectionNeeded
    reports.append(report)
    

    # Custom Alerts Setup
    alerts = []
    alert = dotdict({})
    alert.name = "Lossy Withdraw on Harvest"
    alert.value = unSafeToHarvest
    alert.log_level = "alert"
    alerts.append(alert)


    data.custom_report = reports
    data.custom_alerts = alerts

    return data
