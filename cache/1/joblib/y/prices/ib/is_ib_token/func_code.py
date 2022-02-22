# first line: 12
@log(logger)
@memory.cache()
def is_ib_token(address):
    return has_methods(address, ['debtShareToVal(uint)(uint)','debtValToShare(uint)(uint)'])
