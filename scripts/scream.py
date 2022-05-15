import time, os
import urllib
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timezone
from brownie import (chain,web3, Contract, accounts,ZERO_ADDRESS)

def main():
    print("hi", flush=True)
    load_dotenv(find_dotenv())
    is_prod = os.environ.get("ENV")
    telegram_bot_key = os.environ.get("WAVEY_ALERTS_BOT_KEY")
    chat_id = "-1001545486943"
    hot_account = accounts.load('scream', os.getenv('PASSWORD'))
    count = 0
    log_time = 100
    usd_threshold = 1_000 # USD amount we bother sending txn for
    oracle = Contract("0x57AA88A0810dfe3f9b71a9b179Dd8bF5F956C46A")
    scDAI = Contract("0x8D9AED9882b4953a0c9fa920168fa1FDfA0eBE75")
    scDOLA = Contract("0x5A3B9Dcdd462f264eC1bD56D618BF4552C2EaF8A")
    scFRAX = Contract("0x383D965C8D2ac0A9c1F6930ad10943606BcA4cB7")

    markets = [
        scDAI,
        scDOLA,
        scFRAX,
    ]
    
    strategies = [
        Contract("0xd025b85db175EF1b175Af223BD37f330dB277786"),
        Contract("0x36A1E9dF5EfdAB9694de5bFe25A9ACc23F66BCB7"),
        Contract("0xfF8bb7261E4D51678cB403092Ae219bbEC52aa51"),
    ]

    while True == True:
        for i, m in enumerate(markets):
            underlying = Contract(m.underlying())
            sym = underlying.symbol()
            decimals = underlying.decimals()
            strategy = strategies[i]
            est_wbtc_claim = int(m.balanceOf(strategy) * m.exchangeRateStored() / decimals) / 10**8
            message = ""
            count = count + 1
            should_fetch_new_prices = count % 10_000 == 0

            tx_params = {'from': hot_account}
            tx_params['priority_fee'] = 9e9
            tx_params['max_fee'] = 250e9

            adjusted_balance = underlying.balanceOf(m) / 10**decimals
            val_in_strat = strategy.estimatedTotalAssets() / 10**decimals
            if price == 0 or should_fetch_new_prices:
                price = oracle.getPriceUsdcRecommended(underlying) / 10**6
                print(f'fetched new {sym} price {"${:,.2f}".format(price)}', flush=True)

            usd_val = price * adjusted_balance # USD value of want tokens in the market

            # Print a log every so often
            if count % log_time == 0:
                now = datetime.now()
                print(count,now.strftime("%Y-%m-%d %H:%M"), flush=True)
                print(f'Contract {sym} balance: {adjusted_balance} --> {"${:,.2f}".format(usd_val)}\nRemaining claim: {val_in_strat} --> {"${:,.2f}".format(val_in_strat * price)}\n\n', flush=True)

            # Send transaction if we are over threshold
            if usd_val >= usd_threshold and val_in_strat * price > usd_threshold:
                try:
                    tx = m.harvest()
                    message = f'Transaction mined! \n{sym} {strategy.name()}'
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