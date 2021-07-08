import urllib
import os
import subprocess
import logging
import json
from web3 import Web3


from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv, find_dotenv
load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)



# Web3 setup
infura_id = os.environ.get("INFURA_ID")
web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/"+infura_id))
path = os.getcwd()
print(path)
with open("bot/abis/vault.json") as json_file:
    vault_abi = json.load(json_file)
with open("bot/abis/strategy.json") as json_file:
    strategy_abi = json.load(json_file)

# Bot setup
telegram_chat_id = os.environ.get("TELEGRAM_YFI_HARVEST_SIMULATOR")
telegram_bot_key = os.environ.get("POLLER_KEY")
updater = Updater(token=telegram_bot_key, use_context=True)
dispatcher = updater.dispatcher


def start(update, context):
    context.bot.send_message(chat_id=telegram_chat_id, text="I'm a bot, please talk to me!")

def sim(update, context):
    name = ""
    isValid = False
    isVault = False
    str = ""
    try:
        address = context.args[0]
        try:
            strat = web3.eth.contract(address=address, abi=strategy_abi)
            vault = web3.eth.contract(address=address, abi=vault_abi)
            
            try: # check if a strat
                strat.functions.estimatedTotalAssets().call() # confirm it's a strat
                name = strat.functions.name().call()
                isValid = True
            except (IndexError, ValueError):
                print("")

            try: 
                vault.functions.pricePerShare().call()
                name = vault.functions.name().call()
                isVault = True
                isValid = True
            except (IndexError, ValueError):
                print("")
            
            
            if isValid:
                if isVault:
                    str = "Vault: " + name
                    subprocess.call(['./bot/launch_simulator.sh', "-v " + address]) # Invoke shell script to update env vars and run brownie
                else:
                    str = "Strategy: " + name
                    subprocess.call(['./bot/launch_simulator.sh', "-s " + address]) # Invoke shell script to update env vars and run brownie
                
                update.message.reply_text("Address you gave is: \n\n"+address+"\n\n{}".format(str))    
                context.bot.send_message(chat_id=telegram_chat_id, text="Let's run a simulation! 💻 ......")

        except (IndexError, ValueError):
            update.message.reply_text('Sorry, the value you''ve supplied cannot be read')
        
        
    except (IndexError, ValueError):
        update.message.reply_text('There are not enough numbers')

start_handler = CommandHandler('start', start)
sim_handler = CommandHandler('sim', sim)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(sim_handler)

updater.start_polling()
