# first line: 136
@log(logger)
@memory.cache()
def has_methods(
    address: str, 
    methods: List[str],
    func: Union[any, all] = all
) -> bool:
    '''
    Checks to see if a contract has each view method (with no inputs) in `methods`.
    Pass `at_least_one=True` to only verify a contract has at least one of the methods.
    '''

    assert func in [all, any], '`func` must be either `any` or `all`'

    calls = [Call(address, [method], [[method, None]]) for method in methods]
    try:
        response = Multicall(calls, _w3=web3, require_success=False)().values()
        return func([False if call is None else True for call in response])
    except Exception as e:
        if not call_reverted(e) and not out_of_gas(e): raise
        # Out of gas error implies one or more method is state-changing.
        # If `func == all` we return False because `has_methods` is only supposed to work for public view methods with no inputs
        # If `func == any` maybe one of the methods will work without "out of gas" error
        return False if func == all else any(has_method(address, method) for method in methods)
