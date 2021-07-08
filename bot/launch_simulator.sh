#!/bin/bash

# Set env variables
while getopts v:s: flag
do
    case "${flag}" in
        v|--vault) vault=${OPTARG};;
        s|--strategy) strategy=${OPTARG};;
    esac
done
echo "HERE WE ARE"
echo "vault: $vault";
echo "strategy: $strategy";

if [ -z "$vault" ] && [ -z "$strategy" ]
then
    echo "RUN EVERYTHING!!"

    mode=a
    sed -i "s/^MODE=.*/MODE=${mode}/" ./.env # Replace in .env file
else
    if [[ -n "$vault" ]]
    then
        echo "Running against all strats in a vault: $vault"

        mode=v
        sed -i "s/^MODE=.*/MODE=${mode}/" ./.env # Replace in .env file

        vault="$(echo -e "${vault}" | tr -d '[:space:]')" # Remove whitespace
        sed -i "s/^VAULT=.*/VAULT=${vault}/" ./.env # Replace in .env file
    else
        if [[ -n "$strategy" ]]
        then
            echo "Running single strat simulation: $address"

            mode=s
            sed -i "s/^MODE=.*/MODE=${mode}/" ./.env # Replace in .env file

            strategy="$(echo -e "${strategy}" | tr -d '[:space:]')" # Remove whitespace
            sed -i "s/^STRATEGY=.*/STRATEGY=${strategy}/" ./.env # Replace in .env file


        fi
    fi
fi
