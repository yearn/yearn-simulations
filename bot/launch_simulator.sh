#!/bin/bash
if [ -f .env ]; then
  export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
fi

echo $BROWNIE_PATH

# Set env variables
while getopts ":a:" flag
do
    case "${flag}" in
        a|--address) address=${OPTARG};;
    esac
done

echo "address (launcher): $address";

if [ -z "$vault" ] && [ -z "$strategy" ] && [ -z "$address" ]
then
    echo "RUN EVERYTHING!!"

    mode=a
    sed -i "s/^MODE=.*/MODE=${mode}/" ./.env # Replace in .env file

    $BROWNIE_PATH/brownie.exe run SimulateHarvests.py
else
    echo "Running single strat simulation: $address"
    echo ${address} > 'address.txt'
    $BROWNIE_PATH/brownie.exe run SimulateHarvests.py
fi
