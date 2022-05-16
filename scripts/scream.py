import time, os
import urllib
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timezone
from brownie import (chain,web3, Contract, accounts,ZERO_ADDRESS)

def main():
    print("Starting...", flush=True)
    load_dotenv(find_dotenv())
    is_prod = True #os.environ.get("ENV") == "PROD"
    telegram_bot_key = os.environ.get("WAVEY_ALERTS_BOT_KEY")
    chat_id = "-1001545486943"
    hot_account = accounts.load('scream', os.getenv('PASSWORD_SCREAM'))
    count = 0
    price = 0
    log_time = 100
    usd_threshold = 1_000 # USD amount we bother sending txn for

    oracle = Contract("0x57AA88A0810dfe3f9b71a9b179Dd8bF5F956C46A")

    markets = [
        Contract("0x8D9AED9882b4953a0c9fa920168fa1FDfA0eBE75"), # scDAI
        # Contract("0x5A3B9Dcdd462f264eC1bD56D618BF4552C2EaF8A"), # scDOLA
        Contract("0x383D965C8D2ac0A9c1F6930ad10943606BcA4cB7"), # scFRAX
    ]
    
    strategies = [
        Contract("0xd025b85db175EF1b175Af223BD37f330dB277786"), # DAI
        # Contract("0x36A1E9dF5EfdAB9694de5bFe25A9ACc23F66BCB7"), # DOLA
        Contract("0xfF8bb7261E4D51678cB403092Ae219bbEC52aa51"), # FRAX
    ]

    prices = [
        0,
        0,
        0,
    ]

    while True == True:
        for i, m in enumerate(markets):
            underlying = Contract(m.underlying())
            sym = underlying.symbol()
            decimals = underlying.decimals()
            strategy = strategies[i]
            message = ""
            count = count + 1
            should_fetch_new_prices = count % 9_999 == 0
            should_fetch_new_prices = count % 10_000 == 0

            tx_params = {'from': hot_account}
            tx_params['gas_price'] = 1_000e9

            adjusted_balance = underlying.balanceOf(m) / 10**decimals
            val_in_strat = strategy.estimatedTotalAssets() / 10**decimals
            price = prices[i]
            if price == 0 or should_fetch_new_prices:
                prices[i] = oracle.getPriceUsdcRecommended(underlying) / 10**6
                price = prices[i]
                print(f'fetched new {sym} price {"${:,.2f}".format(price)}', flush=True)

            usd_val = price * adjusted_balance # USD value of want tokens in the market

            # Print a log every so often
            if count % log_time == 0:
                now = datetime.now()
                print(count,now.strftime("%Y-%m-%d %H:%M"), flush=True)
                print(f'Contract {sym} balance: {adjusted_balance} --> {"${:,.2f}".format(usd_val)}\nRemaining claim: {val_in_strat} --> {"${:,.2f}".format(val_in_strat * price)}\n\n', flush=True)

            # Send transaction if we are over threshold
            if usd_val >= usd_threshold and val_in_strat * price > usd_threshold:
                # assert False
                try:
                    tx = strategy.harvest(tx_params)
                    txn_hash = tx.txid
                    debt_payment = tx.events["Harvested"]["debtPayment"]
                    profit = tx.events["Harvested"]["profit"]
                    retrieved = debt_payment + profit
                    debtOutstanding = tx.events["Harvested"]["debtOutstanding"]
                    url = "https://etherscan.io/tx/"
                    if chain.id == 250:
                        url = "https://ftmscan.com/tx/"
                    message = f'⛏ Transaction mined!  --  {sym} {strategy.name()}\n\nRetrieved: {"${:,.2f}".format(retrieved/10**decimals)}\n\nRemaining debt in market: {"${:,.2f}".format(debtOutstanding / 10**decimals)}\n\n{url+txn_hash}'
                except:
                    message = f'error sending a transaction.\n{sym} {strategy.name()}'
                if is_prod:
                    encoded_message = urllib.parse.quote(message)
                    url = f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={encoded_message}"
                    try:
                        urllib.request.urlopen(url)
                    except:
                        print("FAILED TO POST TELEGRAM ALERT")
                else:
                    print(message, flush=True)

        time.sleep(10) # Seconds delay before running again

if __name__ == "__main__":
    main()