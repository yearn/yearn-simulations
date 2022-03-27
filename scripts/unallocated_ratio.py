from .TelegramBot import sendMessageToTelegram, sendResultToTelegram
import brownie, importlib, time
from utils import dotdict
import json, os, sys, re, requests
from brownie import interface, accounts, web3, chain, Contract
import telebot
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timezone
from yearn.networks import Network
from datetime import datetime
import pandas as pd
from web3 import HTTPProvider

load_dotenv()
env = os.environ.get("ENV") # Set environment
chat_id = os.environ.get("TELEGRAM_CHAT_ID_CREDIT_TRACKER")
bot_key = os.environ.get("TELEGRAM_YFI_DEV_BOT")

CHAIN_VALUES = {
    Network.Mainnet: {
        "NETWORK_NAME": "Ethereum Mainnet",
        "NETWORK_SYMBOL": "ETH",
        "EMOJI": "🇪🇹",
        "START_DATE": datetime(2020, 2, 12, tzinfo=timezone.utc),
        "START_BLOCK": 11563389,
        "REGISTRY_ADDRESS": "0x50c1a2eA0a861A967D9d0FFE2AE4012c2E053804",
        "REGISTRY_DEPLOY_BLOCK": 12045555,
        "REGISTRY_HELPER_ADDRESS": "0x52CbF68959e082565e7fd4bBb23D9Ccfb8C8C057",
        "LENS_ADDRESS": "0x5b4F3BE554a88Bd0f8d8769B9260be865ba03B4a",
        "LENS_DEPLOY_BLOCK": 12707450,
        "VAULT_ADDRESS030": "0x19D3364A399d251E894aC732651be8B0E4e85001",
        "VAULT_ADDRESS031": "0xdA816459F1AB5631232FE5e97a05BBBb94970c95",
        "KEEPER_CALL_CONTRACT": "0x2150b45626199CFa5089368BDcA30cd0bfB152D6",
        "KEEPER_TOKEN": "0x1cEB5cB57C4D4E2b2433641b95Dd330A33185A44",
        "YEARN_TREASURY": "0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde",
        "STRATEGIST_MULTISIG": "0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7",
        "GOVERNANCE_MULTISIG": "0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52",
        "EXPLORER_URL": "https://etherscan.io/",
        "TENDERLY_CHAIN_IDENTIFIER": "mainnet",
        "TELEGRAM_CHAT_ID": os.environ.get('TELEGRAM_CHANNEL_1_PUBLIC'),
        "DISCORD_CHAN": os.environ.get('DISCORD_CHANNEL_1'),
    },
    Network.Fantom: {
        "NETWORK_NAME": "Fantom",
        "NETWORK_SYMBOL": "FTM",
        "EMOJI": "👻",
        "START_DATE": datetime(2021, 4, 30, tzinfo=timezone.utc),
        "START_BLOCK": 18450847,
        "REGISTRY_ADDRESS": "0x727fe1759430df13655ddb0731dE0D0FDE929b04",
        "REGISTRY_DEPLOY_BLOCK": 18455565,
        "REGISTRY_HELPER_ADDRESS": "0x8CC45f739104b3Bdb98BFfFaF2423cC0f817ccc1",
        "REGISTRY_HELPER_DEPLOY_BLOCK": 18456459,
        "LENS_ADDRESS": "0x97D0bE2a72fc4Db90eD9Dbc2Ea7F03B4968f6938",
        "LENS_DEPLOY_BLOCK": 18842673,
        "VAULT_ADDRESS030": "0x637eC617c86D24E421328e6CAEa1d92114892439",
        "VAULT_ADDRESS031": "0x637eC617c86D24E421328e6CAEa1d92114892439",
        "KEEPER_CALL_CONTRACT": "0x57419fb50fa588fc165acc26449b2bf4c7731458",
        "KEEPER_TOKEN": "",
        "YEARN_TREASURY": "0x89716Ad7EDC3be3B35695789C475F3e7A3Deb12a",
        "STRATEGIST_MULTISIG": "0x72a34AbafAB09b15E7191822A679f28E067C4a16",
        "GOVERNANCE_MULTISIG": "0xC0E2830724C946a6748dDFE09753613cd38f6767",
        "EXPLORER_URL": "https://ftmscan.com/",
        "TENDERLY_CHAIN_IDENTIFIER": "fantom",
        "TELEGRAM_CHAT_ID": os.environ.get('TELEGRAM_CHANNEL_250_PUBLIC'),
        "DISCORD_CHAN": os.environ.get('DISCORD_CHANNEL_250'),
    },
    Network.Arbitrum: {
        "NETWORK_NAME": "Arbitrum",
        "NETWORK_SYMBOL": "ARRB",
        "EMOJI": "🤠",
        "START_DATE": datetime(2021, 9, 14, tzinfo=timezone.utc),
        "START_BLOCK": 4841854,
        "REGISTRY_ADDRESS": "0x3199437193625DCcD6F9C9e98BDf93582200Eb1f",
        "REGISTRY_DEPLOY_BLOCK": 12045555,
        "REGISTRY_HELPER_ADDRESS": "0x237C3623bed7D115Fc77fEB08Dd27E16982d972B",
        "LENS_ADDRESS": "0xcAd10033C86B0C1ED6bfcCAa2FF6779938558E9f",
        "VAULT_ADDRESS030": "0x239e14A19DFF93a17339DCC444f74406C17f8E67",
        "VAULT_ADDRESS031": "0x239e14A19DFF93a17339DCC444f74406C17f8E67",
        "KEEPER_CALL_CONTRACT": "",
        "KEEPER_TOKEN": "",
        "YEARN_TREASURY": "0x1DEb47dCC9a35AD454Bf7f0fCDb03c09792C08c1",
        "STRATEGIST_MULTISIG": "0x6346282DB8323A54E840c6C772B4399C9c655C0d",
        "GOVERNANCE_MULTISIG": "0xb6bc033D34733329971B938fEf32faD7e98E56aD",
        "EXPLORER_URL": "https://arbiscan.io/",
        "TENDERLY_CHAIN_IDENTIFIER": "arbitrum",
        "TELEGRAM_CHAT_ID": os.environ.get('TELEGRAM_CHANNEL_42161_PUBLIC'),
        "DISCORD_CHAN": os.environ.get('DISCORD_CHANNEL_42161'),
    }
}

def main():
    bot = telebot.TeleBot(bot_key)
    # addresses_provider = interface.IAddressProvider("0x9be19Ee7Bc4099D62737a7255f5c227fBcd6dB93")
    # oracle = interface.IOracle(addresses_provider.addressById("ORACLE"))

    prod_vaults = Contract(CHAIN_VALUES[chain.id]["REGISTRY_HELPER_ADDRESS"]).getVaults()
    registry = Contract(CHAIN_VALUES[chain.id]["REGISTRY_ADDRESS"])
    items = []
    for vault_address in prod_vaults:
        v = Contract(vault_address)
        if registry.latestVault(v.token()) != v.address or v.debtRatio() == 10_000:
            continue
        item = {}
        item["total_ratio"] = v.debtRatio()
        item["unallocated_ratio"] = 10_000 - v.debtRatio()
        item["api_version"] = v.apiVersion()
        item["name"] = v.name()
        item["token_symbol"] = Contract(v.token()).name()
        item["vault_address"] = v.address
        item["token_address"] = v.token()
        if item["unallocated_ratio"] > 100:
            items.append(item)

    items.sort(key=lambda item: item["unallocated_ratio"], reverse=True)
    for i in items:
        print(i["vault_address"],i["unallocated_ratio"],i["api_version"],i["name"])
    