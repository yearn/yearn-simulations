import brownie
from brownie import interface, accounts, web3, chain, Contract
from brownie.network.event import _decode_logs
import pandas as pd
import requests

def main():
    provider_address = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
    protocol_provider_address = "0x057835Ad21a177dbdd3090bB1CAE03EaCF78Fc6d"
    provider = Contract(provider_address)
    protocol_provider = Contract(protocol_provider_address)
    strategies = [
        "0xAE159E657712CC68C8A28B6749eC044a7fEABe21", # Lend WBTC, Borrow USDC
        "0x906f0a6f23e7160eB0927B0903ab80b5E3f3950D" # Lend LINK, Borrow sUSD
    ]
    for strat_address in strategies:
        strategy = Contract(strat_address)
        data = provider.getUserAccountData(strategy)
        fields = ['totalCollateralETH', 'totalDebtETH', 'availableBorrowsETH',
              'currentLiquidationThreshold', 'ltv', 'healthFactor']
        df = pd.DataFrame(columns=fields, data=[data], index=[''])
        for el in fields:
            if el not in ['ltv', 'currentLiquidationThreshold']:
                df[el] = df[el]/10**18
        
        # Lending
        df['Strategy:'] = strategy.name()+' '+strat_address
        want = Contract(strategy.want())
        df['Lending:'] = "{0} ({1}): {2} ".format(
                want.symbol(),
                want,
                round(df['totalCollateralETH'].iloc[0],2)
            )

        yvault = Contract(strategy.yVault())
        yvault_token = Contract(yvault.token())
        df['Borrowing:'] = "{0} ({1}): {2} ".format(
            yvault_token.symbol(),
            yvault_token,
            round(df['totalDebtETH'].iloc[0], 2)
        )

        # assets in vault
        vault_balance = (yvault.balanceOf(strategy)
        * yvault.pricePerShare() ) / (10**(yvault.decimals()*2))

        df['Asset in Vault:'] = "{0} {1}".format(yvault_token.symbol(), round(vault_balance,2))
        
        # ltv and thresholds
        df['Current LTV:'] = "{:.1f}%".format(df['totalDebtETH'].iloc[0]/df['totalCollateralETH'].iloc[0]*100)

        df['Target LTV:'] = "{0}%".format((strategy.targetLTVMultiplier()/10000 * df['currentLiquidationThreshold'].iloc[0]/10000)*100)

        df['Warning LTV:'] = "{0}%".format((strategy.warningLTVMultiplier()/10000 * df['currentLiquidationThreshold'].iloc[0]/10000)*100)

        df['Liquidation threshold:'] = "{}%".format(df['currentLiquidationThreshold'].iloc[0]/100)

        df['Current Health Factor:'] = df['healthFactor'].apply(lambda x: round(x,2))

        reserve_data = protocol_provider.getReserveData(yvault_token)

        df['Current Borrowing Costs:'] = "{}%".format(round(reserve_data[4]*10**-27,4)*100)

        df['Maximum Acceptable Costs:'] = "{}%".format(strategy.acceptableCostsRay()*10**-27*100)

        # add is everything ok
        def check_ok(x):
            if float(x['Current Borrowing Costs:'].replace('%','')) > float(x['Maximum Acceptable Costs:'].replace('%','')):
                return 'NO'
            if float(x['Current LTV:'].replace('%','')) >= float(x['Warning LTV:'].replace('%','')):
                return 'NO'
            return 'YES'
        df['Is everything OK:'] = df.apply(check_ok, axis=1)

        df.drop(columns=fields,inplace=True)
    
        print(df.T.to_string())
