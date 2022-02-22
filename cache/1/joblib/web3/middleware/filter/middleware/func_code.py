# first line: 343
    def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
        if method in NEW_FILTER_METHODS:

            filter_id = next(filter_id_counter)

            _filter: Union[RequestLogs, RequestBlocks]
            if method == RPC.eth_newFilter:
                _filter = RequestLogs(w3, **apply_key_map(FILTER_PARAMS_KEY_MAP, params[0]))

            elif method == RPC.eth_newBlockFilter:
                _filter = RequestBlocks(w3)

            else:
                raise NotImplementedError(method)

            filters[filter_id] = _filter
            return {"result": filter_id}

        elif method in FILTER_CHANGES_METHODS:
            filter_id = params[0]
            #  Pass through to filters not created by middleware
            if filter_id not in filters:
                return make_request(method, params)
            _filter = filters[filter_id]
            if method == RPC.eth_getFilterChanges:
                return {"result": next(_filter.filter_changes)}
            elif method == RPC.eth_getFilterLogs:
                # type ignored b/c logic prevents RequestBlocks which doesn't implement get_logs
                return {"result": _filter.get_logs()}  # type: ignore
            else:
                raise NotImplementedError(method)
        else:
            return make_request(method, params)
