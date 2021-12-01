from brownie import chain, Contract
import requests
import os, sys, re
from dotenv import load_dotenv
import telebot

load_dotenv()
env = os.environ.get("ENV") # Set environment
bloxy_key = os.environ.get("BLOXY_KEY")
chat_id = os.environ.get("TELEGRAM_CHAT_ID_WITHDRAWAL_CHECK")
bot_key = os.environ.get("TELEGRAM_YFI_DEV_BOT")

def main():
    load_dotenv()
    bot = telebot.TeleBot(bot_key)
    registry_helper = Contract("0x52CbF68959e082565e7fd4bBb23D9Ccfb8C8C057")
    oracle = Contract("0x83d95e0D5f402511dB06817Aff3f9eA88224B030")

    #Conf:
    vault_assets_filter = 100_000 #USDC
    holder_number = '5'
    key = bloxy_key # Register at https://bloxy.info/login/new to get a key

    list_of_vaults = [Contract(i) for i in list(registry_helper.getVaults())]
    
    message = ""
    for vault in list_of_vaults:
        vault_name = vault.name()
        token = vault.token()
        token_decimals = Contract(vault.token()).decimals()
        vault_total_supply = vault.totalSupply()/(10 ** token_decimals)
        token_price = oracle.getNormalizedValueUsdc(token, (10 ** token_decimals))/(10 ** 6)
        vault_address = vault.address
        
        if vault_total_supply * (vault.pricePerShare()/(10 ** token_decimals)) * token_price < vault_assets_filter:
            message = f'{vault_name} ({vault.apiVersion()}) is outside of set parameters ({vault_assets_filter:,.2f} USDC of total supply)'
            print(message)
            bot.send_message(chat_id, message)
            continue
                
        try:
            holders = fetch_holders(vault_address, holder_number, key)
        except:
            print(f"Skipped holders for vault {vault_name}")
            continue

        whale = merge_holders(vault, holders)
        whale_assets = vault.balanceOf(whale)
        whale_weight = (whale_assets / vault.totalSupply()) * 100
        
        for percentage in [100, 50, 40, 30, 20, 10, 5, 1]:
            amount_to_withdraw = int(vault.totalSupply() * (percentage/100.0))
            if whale_assets - amount_to_withdraw < 0: continue
           
            try:
                vault.withdraw(amount_to_withdraw, {'from': whale})
                message = f'Withdraw capability of {vault_name} ({vault.apiVersion()}) is at least {percentage}%\n' 
                message = message + f'First {holder_number} holders have a {whale_weight:,.2f}% of total supply\n'
                message = message + f'Total Supply: {vault_total_supply:,.2f} {vault.symbol()} with a value of {vault_total_supply * (vault.pricePerShare()/(10 ** token_decimals)) * token_price:,.2f} USDC\n' 
                print(message)
                if env == "PROD":
                    bot.send_message(chat_id, message, parse_mode="markdown", disable_web_page_preview = True)
                break
            except:
                message = f"Withdraw of {percentage}% failed."
                print(message)
                if env == "PROD":
                    bot.send_message(chat_id, message, parse_mode="markdown", disable_web_page_preview = True)

            chain.undo(1)

def fetch_holders(vault_address, holder_number, key):
    bloxi_url = "https://api.bloxy.info/token/token_holders_list"
    get_params = {
        "token": vault_address,
        "limit": holder_number,
        "key": key,
        "format": 'structure'
    }
    r = requests.get(bloxi_url, params=get_params)
    if not r.ok or r.status_code != 200:
        raise Exception(f"Request failed with content {r.content}")
    holders = []
    for holder in r.json():
        holders.append(holder['address'])
    return holders

def merge_holders(vault, holders):
    first_holder = holders[0]
    for holder in holders[1:]:
        vault.transfer(first_holder, vault.balanceOf(holder), {'from': holder})
    return first_holder
