#!/bin/bash
if [ -f .env ]; then
  export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
fi

echo $BROWNIE_PATH

# Set env variables
while getopts ":a:i:c:" flag
do
    case "${flag}" in
        a|--address) address=${OPTARG};;
        i|--chat_id) chat_id=${OPTARG};;
        c|--chain_id) chain_id=${OPTARG};;
    esac
done

echo "address (launcher): $address";
echo "chat (launcher): $chat_id";
echo "chain (launcher): $chain_id";

if [ -n "$address" ] && [ -n "$chat_id" ] && [ -n "$chain_id" ]
then
    echo "Running simulation: $address"
    echo "Chat ID: $chat_id"
    $BROWNIE_PATH run SimulateHarvests.py main ${chat_id} ${address} ${chain_id}

else
    echo "Usage: 'launch_simulator.sh -a <address> -i <chat-id> -c <chain-id>'"
fi
