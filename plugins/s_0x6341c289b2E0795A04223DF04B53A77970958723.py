import brownie
from utils import dotdict
from brownie import interface, accounts, web3, chain

def pre_harvest_custom(data):
    strategy = interface.IGenLevComp(data.strategy_address)
    strategy.setMinCompToSell(0,{'from':data.gov})
    return data

def post_harvest_custom(data):
    return data

def report_custom(data):
    return data



