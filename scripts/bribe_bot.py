import os

from dotenv import load_dotenv
import pandas as pd
import telebot
from brownie import (
    Contract,
    accounts,
    chain,
    rpc,
    web3,
    history,
    interface,
    Wei,
    ZERO_ADDRESS,
)
import time, re, json

def main():
    bribev2 = interface.IBribeV2("0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026")
    voter = interface.IVoter("0xF147b8125d2ef93FB6965Db97D6746952a133934")
    gauge_controller = interface.IGaugeController("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB")
    addresses_provider = interface.IAddressProvider("0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93")
    oracle = interface.IOracle(addresses_provider.addressById("ORACLE"))
    indent = "    "
    num_gauges = gauge_controller.n_gauges()
    print("Found "+str(num_gauges)+" gauges...")
    for i in range(0, num_gauges):
        g = gauge_controller.gauges(i)
        rewards = bribev2.rewards_per_gauge(g)
        gauge = interface.Gauge(g)
        try:
            lp_name = interface.IERC20(gauge.lp_token()).name()
        except:
            lp_name = "Cannot find name"
        if len(rewards) > 0:
            print("Found tokens on gauge:",g, lp_name)
            for i,  r in enumerate(rewards):
                price = oracle.getPriceUsdcRecommended(r) / 10**6
                token = interface.IERC20(r)
                total_tokens = bribev2.reward_per_token(g, r) / 10**token.decimals()
                claimable = bribev2.claimable(voter, g, r)
                claimable_str = claimable / 10**token.decimals()
                claimable_usd = price * claimable_str
                print(indent,"${:,.2f}".format(total_tokens * price), total_tokens)
                print(indent,token.name(), claimable_str, )
                print(indent,"Claimable by yearn:",claimable)
                print(indent,"USD Value:","${:,.2f}".format(claimable_usd))
            print()


# def claim_it(gauge, token, claimable):
#     bribe = interface.IBribeV2("0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026")
#     voter = interface.IVoter("0xF147b8125d2ef93FB6965Db97D6746952a133934")
#     gov = accounts.at(web3.ens.resolve("ychad.eth"), force=True)
#     claimable = bribe.claimable(voter, gauge, token)
#     before = token.balanceOf(gov)
#     calldata = bribe.claim_reward.encode_input(gauge, token.address)
#     voter.execute(bribe,0,calldata,{'from':gov})
#     calldata = token.transfer.encode_input(gov, claimable)
#     voter.execute(token,0,calldata,{'from':gov})
#     after = token.balanceOf(gov)
#     if after > before:
#         print(token.symbol()," claim succeeded!")
#     else:
#         print(token.symbol()," claim failed.")