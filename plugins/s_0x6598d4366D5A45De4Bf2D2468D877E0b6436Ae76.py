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
    data.post.custom.lossProtectionBalance = s.lossProtectionBalance() / decimals
    
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
    reports = []
    report = dotdict({})
    report.name = "Claimed Rewards"
    report.value = data.pre.custom.claimable - data.post.custom.claimable
    reports.append(report)
    report.name = "Loss Protection Diff"
    report.value = data.post.custom.lossProtectionBalance - data.post.custom.lossProtectionBalance
    reports.append(report)
    data.custom_report = reports

    # Custom Alerts Setup
    alerts = []
    alert = dotdict({})
    alert.name = "Rewards Claimed"
    alert.value = (
        data.post.custom.lossProtectionBalance < data.post.custom.lossProtectionBalance
    )
    alert.log_level = "warning"
    alerts.append(alert)
    data.custom_alerts = alerts

    return data
