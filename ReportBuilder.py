import brownie, importlib
from dotenv import load_dotenv, find_dotenv
from utils import dotdict
import json, os, sys, re, requests
from datetime import datetime
import pandas as pd

def report_builder(data):
    load_dotenv()
    env = os.environ.get("ENVIRONMENT") # Set environment
    chat_id = 1
    f = open("chatid.txt", "r", errors="ignore")
    chat_id = f.read().strip()

    d = 10 ** data.token_decimals
    
    est_apr_before_fees = "{:.4%}".format(data.post.est_apr_before_fees)
    est_apr_after_fees = "{:.4%}".format(data.post.est_apr_after_fees)

    df = pd.DataFrame(index=[''])
    i = []
    r = dotdict({})
    r.name = "Timestamp"
    r.value = datetime.now().isoformat()
    i, r = appender(i, r)
    r.name = "----- STRATEGY DESCRIPTION-------"
    r.value = ""
    i, r = appender(i, r)
    r.name = "Strategy Name"
    r.value = data.strategy_name
    i, r = appender(i, r)
    r.name = "Vault Name"
    r.value = data.vault_name
    i, r = appender(i, r)
    r.name = "Strategy API Version"
    r.value = data.strategy.apiVersion()
    i, r = appender(i, r)
    r.name = "Vault API Version"
    r.value = data.vault.apiVersion()
    i, r = appender(i, r)
    r.name = "Strategy address"
    r.value = data.strategy_address
    i, r = appender(i, r)
    r.name = "Token address"
    r.value = data.token_address
    i, r = appender(i, r)
    r.name = "Vault Address"
    r.value = data.vault_address
    i, r = appender(i, r)
    r.name = "Strategist address"
    r.value = data.strategist
    i, r = appender(i, r)
    r.name = "----- STRATEGY PARAMS-------"
    r.value = ""
    i, r = appender(i, r)
    r.name = "Total Debt before"
    r.value = "{:,}".format(data.pre.debt / d)
    i, r = appender(i, r)
    r.name = "Total Gain before"
    r.value = "{:,.4f}".format(data.pre.gain / d)
    i, r = appender(i, r)
    r.name = "Total Loss before"
    r.value = "{:,.4f}".format(data.pre.loss / d)
    i, r = appender(i, r)
    r.name = "Target debt ratio"
    r.value = f"{data.pre.desired_ratio_str}"
    i, r = appender(i, r)
    r.name = "Actual debt ratio"
    r.value = f"{data.pre.actual_ratio_str}"
    i, r = appender(i, r)
    r.name = "Harvest trigger"
    r.value = f"{bool_description(data.pre.harvest_trigger)}"
    i, r = appender(i, r)
    r.name = "----- HARVEST SIMULATION DATA-------"
    r.value = ""
    i, r = appender(i, r)
    if data.harvest_success == False:
        i, r = appender(i, r)
        r.name = "Harvest failed!"
        r.value = f"no data available."
    else:
        r.name = "Net Profit on harvest"
        net_profit = (data.post.gain_delta / d) - (data.post.loss_delta / d)
        print("${:,.2f}".format(data.token_price * net_profit))
        net_profit_formatted = "{:,.4f}".format(net_profit)
        net_profit_usd = "${:,.2f}".format(data.token_price * net_profit)
        r.value = net_profit_formatted + " (" + net_profit_usd + ")"
        i, r = appender(i, r)
        r.name = "APR before fees"
        r.value = f"{est_apr_before_fees}"
        i, r = appender(i, r)
        r.name = "APR after fees"
        r.value = f"{est_apr_after_fees}"
        i, r = appender(i, r)
        r.name = "Last harvest"
        r.value = f"{data.time_since_last_harvest}"
        i, r = appender(i, r)
        r.name = "Debt delta"
        value = data.post.debt_delta / d
        value_formatted = "{:,.4f}".format(value)
        value_usd = "${:,.2f}".format(value * data.token_price)
        r.value = value_formatted + " (" + value_usd + ")"
        i, r = appender(i, r)
        r.name = "Treasury fees"
        value = data.post.treasury_fee_delta / d
        value_formatted = "{:,.4f}".format(value)
        value_usd = "${:,.2f}".format(value * data.token_price)
        r.value = value_formatted + " (" + value_usd + ")"
        i, r = appender(i, r)
        r.name = "Strategist fees"
        value = data.post.strategist_fee_delta / d
        value_formatted = "{:,.4f}".format(value)
        value_usd = "${:,.2f}".format(value * data.token_price)
        r.value = value_formatted + " (" + value_usd + ")"
        i, r = appender(i, r)
        r.name = "Total fees"
        value = data.post.total_fee_delta / d
        value_formatted = "{:,.4f}".format(value)
        value_usd = "${:,.2f}".format(value * data.token_price)
        r.value = value_formatted + " (" + value_usd + ")"
        i, r = appender(i, r)
        r.name = "Previous PPS"
        r.value = "{:,.5f}".format(data.pre.price_per_share / d)
        i, r = appender(i, r)
        r.name = "New PPS"
        r.value = "{:,.5f}".format(data.post.price_per_share / d)
        i, r = appender(i, r)
        r.name = "PPS percent change"
        r.value = "{:,.5f}".format(data.post.pps_percent_change)
        i, r = appender(i, r)
    r.name = "----- DEFAULT ALERTS -------"
    r.value = ""
    i, r = appender(i, r)
    data.report = i

    """
        FORMAT REPORT
    """
    # Default Data
    for idx in i:
        df[idx.name] = f"{idx.value}"

    # Alerts
    data = configure_alerts(data)
    data.highest_alert_level = "info"
    try:
        for i in data.alerts:
            df[i.name] = f"{pass_fail(i)}"
            if i.value:
                if i.log_level == "warning" and data.highest_alert_level != "alert":
                    data.highest_alert_level = "warning"
                if i.log_level == "alert":
                    data.highest_alert_level = "alert"
    except:
        print("Error setting up default alerts")

    # Custom Reports
    data = build_report_custom(data)

    try:
        if len(data.custom_report) > 0:
            df[" "] = " "
            df[" "] = " "
            df[" "] = " "
            df[" "] = " "
            df["----- CUSTOM REPORT -------"] = ""
            for i in data.custom_report:
                df[i.name] = f"{i.value}"
    except:
        print("Error setting up custom data")

    # Custom Alerts
    try:
        if len(data.custom_alerts) > 0:
            df["----- CUSTOM ALERTS -------"] = ""
            for i in data.custom_alerts:
                df[i.name] = f"{pass_fail(i)}"
                if i.log_level == "warning" and data.highest_alert_level != "alert":
                    data.highest_alert_level = "warning"
                if i.log_level == "alert":
                    data.highest_alert_level = "alert"
    except:
        print("Error setting up custom alerts")


    report_string = df.T.to_string()
    
    return data, report_string

def appender(arr, obj):
    arr.append(obj)
    obj = dotdict({})
    return arr, obj

def configure_alerts(data):
    alerts = []
    alert = dotdict({})
    alert.name = "Share price check"
    alert.value = (
        data.post.pps_percent_change >= 0
        and data.post.pps_percent_change < 1 # make sure it doesnt go too high
        and data.post.price_per_share >= 1 ** data.token_decimals
    )
    alert.log_level = "alert"
    alerts, alert = appender(alerts, alert)
    alert.name = "Loss check"
    alert.value = (data.post.loss_delta == 0)
    alert.log_level = "alert"
    alerts, alert = appender(alerts, alert)
    data.alerts = alerts

    return data

def bool_description(bool):
        return "TRUE" if bool else "FALSE"

def pass_fail(item):
    if item.value:
        return "✅"
    else:
        if item.log_level == "warning":
            return "⚠"
        if item.log_level == "info":
            return "ℹ"
        else:
            return "🚨"
    #return "PASSED" if bool else "FAILED"

def build_report_custom(data):
    strategy_address = data.strategy_address
    s = f"s_{strategy_address}"
    try:
        spec = importlib.util.spec_from_file_location("module.name", f"./plugins/{s}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data.custom_report = dotdict({})
        data.custom_alerts = dotdict({})
        data = module.build_report_custom(data)
    except:
        print("Failed fetching custom report script")

    return data