import brownie
from utils import dotdict
from brownie import interface, accounts, web3, chain

def pre_harvest_custom(data):
    # Harvest underlying mm vault strategy
    mm_gov = accounts.at("0x7cDaCBa026DDdAa0bD77E63474425f630DDf4A0D", force=True)
    mmStrat = "0xa6f43d225d188AeF31F99F20eBa8E537a6DE86B5"
    interface.IMMStrat(mmStrat).harvest({'from':mm_gov, "nonce": mm_gov.nonce, "gas_limit": 8000000})
    return data

def post_harvest_custom(data):
    return data

def report_custom(data):
    return data

def build_report_custom(data):
    return data
