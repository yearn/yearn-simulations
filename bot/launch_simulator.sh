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

if [ -z "$vault" ] && [ -z "$strategy" ] && [ -z "$address" ]
then
    echo "RUN EVERYTHING!!"

    mode=a
    sed -i "s/^MODE=.*/MODE=${mode}/" ./.env # Replace in .env file

    $BROWNIE_PATH run SimulateHarvests.py
else
    echo "Running simulation: $address"
    echo "Chat ID: $chat_id"
    echo ${chat_id} > 'chatid.txt'
    echo ${address} > 'address.txt'
    $BROWNIE_PATH run SimulateHarvests.py
fi
