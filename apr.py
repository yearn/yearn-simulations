import brownie, importlib
from dotenv import load_dotenv, find_dotenv
from utils import dotdict
import json, os, sys, re, requests
from datetime import datetime
import pandas as pd

def calc_apr(data, simulation):
    # [{strat, beforefee, afterfee, debtratio}]

    item = dotdict({})
    item.strategy_address = data.strategy_address
    item.strategy_name = data.strategy_name
    item.pre_fee_apr = data.post.est_apr_before_fees
    item.post_fee_apr = data.post.est_apr_after_fees
    item.actual_ratio = data.pre.debt / (data.pre.total_assets + 1)
    item.desired_ratio = data.pre.desired_ratio
    item.relative_pre_fee_apr = item.actual_ratio * item.pre_fee_apr
    item.relative_post_fee_apr = item.desired_ratio * item.post_fee_apr
    simulation.apr.strategies.append(item)

    simulation.apr.pre_fee_apr_total += item.relative_pre_fee_apr
    simulation.apr.post_fee_apr_total += item.relative_post_fee_apr

    # print(json.dumps(simulation.apr, indent=4, sort_keys=True))

    return data, simulation

def report_apr(data, simulation):
    load_dotenv()
    env = os.environ.get("ENVIRONMENT") # Set environment
    chat_id = 1
    f = open("chatid.txt", "r", errors="ignore")
    chat_id = f.read().strip()

    d = 10 ** data.token_decimals

    df = pd.DataFrame(index=[''])
    i = []
    r = dotdict({})
    print(simulation.apr.strategies)

    # for strat in simulation.apr.strategies:
    #     r.name = "Strategy Name"
    #     r.value = strat.strategy_name
    #     i, r = appender(i, r)
    #     r.name = "Strategy Address"
    #     r.value = strat.strategy_address
    #     i, r = appender(i, r)
    #     r.name = "Pre-fee APR"
    #     r.value = strat.pre_fee_apr
    #     i, r = appender(i, r)
    #     r.name = "Post-fee APR"
    #     r.value = strat.post_fee_apr
    #     i, r = appender(i, r)
    #     r.name = "---------"
    #     r.value = ""
    #     i, r = appender(i, r)

    r.name = "----- Vault Weighted Average APR-------"
    r.value = ""
    i, r = appender(i, r)
    r.name = "Pre-fee"
    r.value = "{:.4%}".format(simulation.apr.pre_fee_apr_total)
    i, r = appender(i, r)
    r.name = "Post-fee"
    r.value = "{:.4%}".format(simulation.apr.post_fee_apr_total)
    i, r = appender(i, r)

    for item in i:
        df[item.name] = f"{item.value}"

    report_string = df.T.to_string()
    
    return report_string

def appender(arr, obj):
    arr.append(obj)
    obj = dotdict({})
    return arr, obj