# first line: 25
@log(logger)
@memory.cache()
def is_mooniswap_pool(token):
    if router is None: return False
    return router.isPool(token)
