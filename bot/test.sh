#!/bin/bash

if [ -f .env ]; then
  export $(echo $(cat .env | sed 's/#.*//g'| xargs) | envsubst)
fi

echo $BROWNIE_PATH
echo "Hi"
path=/c/Users/rmill/AppData/Local/Programs/Python/Python38/Scripts
#/c/Users/rmill/AppData/Local/Programs/Python/Python38/Scripts/brownie.exe run SimulateHarvests.py
$path/brownie.exe run SimulateHarvests.py
#C:\Users\rmill\AppData\Local\Programs\Python\Python38\Scripts