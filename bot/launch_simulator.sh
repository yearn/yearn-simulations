#!/bin/bash
if [ -f .env ]; then
  export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
fi

echo $BROWNIE_PATH

# Set env variables
while getopts ":a:i:" flag
do
    case "${flag}" in
        a|--address) address=${OPTARG};;
        i|--chat_id) chat_id=${OPTARG};;
    esac
done

echo "address (launcher): $address";

if [ -n "$address" ] && [ -n "$chat_id" ]
then
    echo "Running simulation: $address"
    echo "Chat ID: $chat_id"
    $BROWNIE_PATH run SimulateHarvests.py ${chat_id} ${address}

else
    echo "Usage: 'launch_simulator.sh -a <address> -i <chat-id>'"
fi
