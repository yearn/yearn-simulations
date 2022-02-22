# first line: 38
@log(logger)
@memory.cache()
def is_yearn_vault(token):
    # Yearn-like contracts can use these formats
    result = any([
        has_methods(token, ['pricePerShare()(uint)','getPricePerShare()(uint)','getPricePerFullShare()(uint)','getSharesToUnderlying()(uint)'], any),
        has_methods(token, ['exchangeRate()(uint)','underlying()(address)']),
    ])

    # pricePerShare can revert if totalSupply == 0, which would cause `has_methods` to return `False`,
    # but it might still be a vault. This section will correct `result` for problematic vaults.
    if result is False:
        try: 
            contract = Contract(token)
            result = any([
                hasattr(contract,'pricePerShare'),
                hasattr(contract,'getPricePerShare'),
                hasattr(contract,'getPricePerFullShare'),
                hasattr(contract,'getSharesToUnderlying'),
            ])
        except (ContractNotVerified, MessedUpBrownieContract): pass

    return result
