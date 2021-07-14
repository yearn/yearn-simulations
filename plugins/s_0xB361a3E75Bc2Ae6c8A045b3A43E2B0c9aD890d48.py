import urllib
import brownie, json
from utils import dotdict
from brownie import interface, accounts, web3, chain

# ROOK Strategy
def pre_harvest_custom(data):
    """
        data.pre.custom
            A namespace for storage of pre-harvest data
    """
    strategy = interface.IStrategyRook(data.strategy_address)
    with urllib.request.urlopen(
            f"https://indibo-lpq3.herokuapp.com/reward_of_liquidity_provider/{data.strategy_address}") as url:
        payload = json.loads(url.read().decode())
        amount = int(payload["earnings_to_date"], 16)
        nonce = int(payload["nonce"], 16)
        signature = payload["signature"]
    strategy.claimRewards(amount, nonce, signature, {'from': data.gov})
    return data

def post_harvest_custom(data):
    
    return data

def build_report_custom(data):
    
    return data
