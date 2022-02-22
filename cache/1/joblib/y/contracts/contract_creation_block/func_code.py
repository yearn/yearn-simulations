# first line: 34
@log(logger)
@memory.cache()
def contract_creation_block(address) -> int:
    """
    Determine the block when a contract was created using binary search.
    NOTE Requires access to historical state. Doesn't account for CREATE2 or SELFDESTRUCT.
    """
    logger.info("contract creation block %s", address)
    height = chain.height
    lo, hi = 0, height
    while hi - lo > 1:
        mid = lo + (hi - lo) // 2
        try:
            if web3.eth.get_code(address, block_identifier=mid): hi = mid
            else: lo = mid
        except ValueError as e:
            if 'missing trie node' in str(e):
                logger.critical('missing trie node, `contract_creation_block` may output a higher block than actual. Please try again using an archive node.')
            elif 'Server error: account aurora does not exist while viewing' in str(e):
                logger.critical(str(e))
            else: raise
            lo = mid
    return hi if hi != height else None
