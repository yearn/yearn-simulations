import brownie
from utils import dotdict
from brownie import interface, accounts, web3, chain

def pre_harvest_custom(data):
    try:
        decimals = 10 ** data.token_decimals
        custom = []
        d = dotdict({})

        s = interface.IStrategy(data.strategy_address)
        r = interface.IRewards(s.poolRewards())
        
        d.name = "Claimable Rewards"
        d.value = r.claimable(data.strategy_address) / 1e18
        custom.append(d)
        d = dotdict({})

        d.name = "Loss Protection Balance"
        d.value = s.lossProtectionBalance() / decimals
        custom.append(d)
        print(custom)
        
        # data.custom.pre = dotdict({}) 
        data.custom.pre = custom
    except:
        print("Error in custom script")
    
    return data

def post_harvest_custom(data):
    print("entered post harvest")
    print("entered post harvest")
    print("entered post harvest")
    print("entered post harvest")
    print("entered post harvest")

def configure_alerts_custom(data):
    print("entered post harvest")
    print("entered post harvest")
    print("entered post harvest")
    print("entered post harvest")
    print("entered post harvest")
