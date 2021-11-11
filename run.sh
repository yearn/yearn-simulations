#!/usr/bin/env bash

ganache-cli --port 8545 --gasLimit 12000000 --accounts 10 --hardfork istanbul --mnemonic brownie --fork https://mainnet.infura.io/v3/"${INFURA_ID}" --chainId 1 &

sleep 30

brownie run $1