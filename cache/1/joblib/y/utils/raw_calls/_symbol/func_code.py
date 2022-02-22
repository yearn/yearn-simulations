# first line: 117
@log(logger)
@memory.cache
def _symbol(
    contract_address: Union[str, Address, brownie.Contract, Contract],
    block: Union[BlockNumber, int, None] = None,
    return_None_on_failure: bool = False
    ):

    # method 1
    # NOTE: this will almost always work, you will rarely proceed to further methods
    symbol = raw_call(contract_address, "symbol()", block=block, output='str', return_None_on_failure=True)
    if symbol is not None: return symbol

    # method 2
    symbol = raw_call(contract_address, "SYMBOL()", block=block, output='str', return_None_on_failure=True)
    if symbol is not None: return symbol

    # method 3
    symbol = raw_call(contract_address, "getSymbol()", block=block, output='str', return_None_on_failure=True)
    if symbol is not None: return symbol

    # we've failed to fetch
    if return_None_on_failure: return None
    raise NonStandardERC20(f'''
        Unable to fetch `symbol` for {contract_address} on {Network.printable()}
        If the contract is verified, please check to see if it has a strangely named
        `symbol` method and create an issue on https://github.com/BobTheBuidler/ypricemagic
        with the contract address and correct method name so we can keep things going smoothly :)''')
