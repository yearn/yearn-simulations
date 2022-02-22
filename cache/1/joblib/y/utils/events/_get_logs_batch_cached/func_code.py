# first line: 122
@memory.cache()
def _get_logs_batch_cached(address, topics, start, end):
    return _get_logs_no_cache(address, topics, start, end)
