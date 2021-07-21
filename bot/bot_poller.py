import urllib
import sys, subprocess, os, time
import logging
import json
from web3 import Web3
from telegram import Update
from dotenv import load_dotenv, find_dotenv
from telegram.ext.dispatcher import run_async
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)



# Web3 setup
infura_id = os.environ.get("INFURA_ID")
web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/"+infura_id))
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

@run_async
def do_exec(address, chat_id):
    try:
        address = "-a "+ str(address)
        chat_id = "-i "+ str(chat_id)
        print(chat_id)
        p = subprocess.call(['bash','./bot/launch_simulator.sh', address, chat_id]) # Invoke shell script to update env vars and run brownie
    except:
        e = sys.exc_info()
        print("error calling subprocess")
        print(e)


def sim(update: Update, context: CallbackContext):
    name = ""
    isValid = False
    isVault = False
    str = ""
    print("CHAT ID")
    print(update.message)
    user_first_name = ""
    try:
        user_first_name = update.message.chat.first_name
    except:
        print("Unable to get user's first name")
    chat_id = update.message.chat.id
    print("User:", user_first_name, chat_id)
    try:
        address = context.args[0]
        if address == "all":
            do_exec(address, chat_id) # Invoke shell script to update env vars and run brownie
            update.message.reply_text("G'day {}, ser!\n\nI see you'd like to simulate harvests on all strats\n\n💻 Let's run a simulation! ......".format(user_first_name,str))
        else:
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
                        str = "vault:\n" + name
                    else:
                        str = "strategy:\n" + name
                    do_exec(address, chat_id) # Invoke shell script to update env vars and run brownie
                    update.message.reply_text("G'day {}, ser!\n\nAddress you gave is for {}\n\n💻 Let's run a harvest simulation! ......".format(user_first_name,str))

            except (IndexError, ValueError):
                update.message.reply_text('Please supply a valid strategy or vault address.')
        
        
    except (IndexError, ValueError):
        update.message.reply_text('Please supply a valid strategy or vault address.')

start_handler = CommandHandler('start', start)
sim_handler = CommandHandler('sim', sim)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(sim_handler)

updater.start_polling()
