import time, os
import urllib
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timezone
from brownie import (chain,web3, Contract, accounts,ZERO_ADDRESS)

def main():
    print("Starting...", flush=True)
    load_dotenv(find_dotenv())
    is_prod = os.environ.get("ENV") == "PROD"
    telegram_bot_key = os.environ.get("WAVEY_ALERTS_BOT_KEY")
    chat_id = "-1001545486943"
    hot_account = accounts.load('scream', os.getenv('PASSWORD_SCREAM'))
    s = Contract("0xd025b85db175EF1b175Af223BD37f330dB277786")
    s.setRewards()
    s = Contract("0xfF8bb7261E4D51678cB403092Ae219bbEC52aa51")
    count = 0
    price = 0
    log_time = 100
    usd_threshold = 1_000 # USD amount we bother sending txn for

    oracle = Contract("0x57AA88A0810dfe3f9b71a9b179Dd8bF5F956C46A")
    tx_params = {'from': hot_account}
    tx_params['gas_price'] = 1_000e9

    INFO = [
        {
            "underlying": Contract("0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E"),
            "market": Contract("0x8D9AED9882b4953a0c9fa920168fa1FDfA0eBE75"),
            "decimals": 18,
            "symbol": "DAI",
            "price": 0,
            "strategy": Contract("0xd025b85db175EF1b175Af223BD37f330dB277786"),
            "assets": Contract("0xd025b85db175EF1b175Af223BD37f330dB277786").estimatedTotalAssets() / 10**18,
        },
        {
            "underlying": Contract("0xdc301622e621166BD8E82f2cA0A26c13Ad0BE355"),
            "market": Contract("0x383D965C8D2ac0A9c1F6930ad10943606BcA4cB7"),
            "decimals": 18,
            "symbol": "FRAX",
            "price": 0,
            "strategy": Contract("0xfF8bb7261E4D51678cB403092Ae219bbEC52aa51"),
            "assets": Contract("0xfF8bb7261E4D51678cB403092Ae219bbEC52aa51").estimatedTotalAssets() / 10**18,
        }
    ]

    while True:
        for i in range(0, len(INFO)):
            if INFO[i]["assets"] == 0: # Check if we are already exited
                continue
            underlying = INFO[i]["underlying"]
            sym = INFO[i]["symbol"]
            decimals = INFO[i]["decimals"]
            strategy = INFO[i]["strategy"]
            price = INFO[i]["price"]
            market = INFO[i]["market"]
            assets = INFO[i]["assets"]

            message = ""
            count = count + 1

            should_refresh_data = count % 10_000 == 0 or count % (10_000+1) == 0

            market_balance = underlying.balanceOf(market) / 10**decimals
            usd_val = price * market_balance # USD value of want tokens in the market
     
            # Refresh data and print a log every so often
            if price == 0 or should_refresh_data:
                INFO[i]["price"] = oracle.getPriceUsdcRecommended(underlying) / 10**6
                price = INFO[i]["price"]
                INFO[i]["assets"] = INFO[i]["strategy"].estimatedTotalAssets() / 10**decimals
                assets = INFO[i]["assets"]
                
                now = datetime.now()
                print(chain.height, now.strftime("%Y-%m-%d %H:%M"), count, flush=True)
                print(f'fetched new {sym} price {"${:,.2f}".format(price)}', flush=True)
                print(f'Contract {sym} balance: {market_balance} --> {"${:,.2f}".format(usd_val)}\nRemaining claim: {assets} --> {"${:,.2f}".format(assets * price)}\n\n', flush=True)

            # Send transaction if we are over threshold
            if usd_val >= usd_threshold and assets * price > usd_threshold:
                try:
                    tx = strategy.harvest(tx_params)
                    INFO[i]["assets"] = INFO[i]["strategy"].estimatedTotalAssets() / 10**INFO[i]["decimals"]
                    txn_hash = tx.txid
                    debt_payment = tx.events["Harvested"]["debtPayment"]
                    profit = tx.events["Harvested"]["profit"]
                    retrieved = debt_payment + profit
                    debtOutstanding = tx.events["Harvested"]["debtOutstanding"]
                    url = "https://etherscan.io/tx/"
                    if chain.id == 250:
                        url = "https://ftmscan.com/tx/"
                    message = f'⛏ Transaction mined!  --  {sym} {strategy.name()}\n\nRetrieved: {"${:,.2f}".format(retrieved/10**decimals)}\n\nRemaining debt in market: {"${:,.2f}".format(debtOutstanding / 10**decimals)}\n\n{url+txn_hash}'
                except Exception as e:
                    print(e)
                    INFO[i]["assets"] = INFO[i]["strategy"].estimatedTotalAssets() / 10**INFO[i]["decimals"]
                    eoa_balance = int(hot_account.balance()/1e18)
                    message = f'error sending a transaction.\n{sym} {strategy.name()}\n\nEOA Balance: {eoa_balance}'
                if is_prod:
                    encoded_message = urllib.parse.quote(message)
                    url = f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={encoded_message}"
                    try:
                        urllib.request.urlopen(url)
                    except:
                        print("FAILED TO POST TELEGRAM ALERT")
                else:
                    print(message, flush=True)

        # time.sleep(1) # Seconds delay before running again

if __name__ == "__main__":
    main()