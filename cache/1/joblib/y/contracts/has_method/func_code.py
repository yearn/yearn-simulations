# first line: 117
@log(logger)
@memory.cache()
def has_method(address: str, method: str, return_response: bool = False) -> bool:
    '''
    Checks to see if a contract has a `method` view method with no inputs.
    `return_response=True` will return `response` in bytes if `response` else `False`
    '''
    try: response = Call(address, [method], [['key', None]], _w3=web3)()['key']
    except Exception as e:
        if call_reverted(e): return False
        # We return False here because `has_method` is only supposed to work for public view methods with no inputs
        # Out of gas error implies method is state-changing. Therefore the contract does not have a public view method called `method`
        if out_of_gas(e): return False
        raise
    
    if response is None: return False
    if return_response: return response
    return True
