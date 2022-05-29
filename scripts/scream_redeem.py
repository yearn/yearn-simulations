import time, os
import urllib
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timezone
from itertools import count
from brownie import (chain,web3, Contract, accounts,ZERO_ADDRESS)

load_dotenv(find_dotenv())
user = accounts.load('scream', os.getenv('PASSWORD_SCREAM'))
redeemer = Contract('0xC3C7a349BCAb2a039f466525a106742800fa16f6', owner=user)
scdai = Contract("0x8D9AED9882b4953a0c9fa920168fa1FDfA0eBE75")
dai = Contract(scdai.underlying())
gov = '0xC0E2830724C946a6748dDFE09753613cd38f6767'

def stats(block):
    print(f'[{block:,d}] balance={user.balance() / 1e18:,.2f} ftm  trapped={scdai.balanceOfUnderlying.call(gov)/ 1e18:,.0f} dai  liquidity={dai.balanceOf(scdai) / 1e18:,.0f} dai') 

stats(chain.height)

for block in chain.new_blocks():
    if block.number % 20 == 0:
        stats(block.number)
    if redeemer.shouldRedeem():
        redeemer.redeemMax()

while True:
    if redeemer.shouldRedeem():
        redeemer.redeemMax()
    time.sleep(1)

# def main():
#     print("Starting...", flush=True)
#     load_dotenv(find_dotenv())
#     is_prod = os.environ.get("ENV") == "PROD"
#     telegram_bot_key = os.environ.get("WAVEY_ALERTS_BOT_KEY")
#     chat_id = "-1001545486943"
#     hot_account = accounts.load('scream', os.getenv('PASSWORD_SCREAM'))
#     tx_params = {'from': hot_account}
#     tx_params['gas_price'] = 1_000e9
#     redeemer = Contract("0xC3C7a349BCAb2a039f466525a106742800fa16f6")
#     scdai = Contract("0x8D9AED9882b4953a0c9fa920168fa1FDfA0eBE75")
#     dai = Contract(scdai.underlying())
#     count = 0
#     while True:
#         count += 1
#         if count % 10_000 == 0:
#             ts = chain.time()
#             str = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
#             print(str)
#             print("Balance",dai.balanceOf(scdai)/1e18)
#             print()
#         if redeemer.shouldRedeem():
#             try:
#                 tx = redeemer.redeemMax(tx_params)
#                 txn_hash = tx.txid
#                 retrieved = tx.events["Retrieved"]/1e18
#                 message = f'⛏ Redeem transaction mined!\n\nRetrieved: {"${:,.2f}".format(retrieved)}\n\n{url+txn_hash}'
#             except Exception as e:
#                 print(e)
#                 eoa_balance = int(hot_account.balance()/1e18)
#                 message = f'error sending a REDEEMER transaction.\n\nEOA Balance: {eoa_balance}'
#             # Send transaction if we are over threshold
#             if is_prod:
#                 encoded_message = urllib.parse.quote(message)
#                 url = f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={encoded_message}"
#                 try:
#                     urllib.request.urlopen(url)
#                 except:
#                     print("FAILED TO POST TELEGRAM ALERT")
#             else:
#                 print(message, flush=True)

#         time.sleep(.1) # Seconds delay before running again

# if __name__ == "__main__":
#     main()