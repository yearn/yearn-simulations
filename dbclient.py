from pymongo import MongoClient
# pprint library is used to make the output look more pretty
from pprint import pprint
import schedule
import time

def job():
    dbname = get_database()
    print(dbname)
    collection_name = dbname["schedule"]
    item_details = collection_name.find()
    for item in item_details:
        # This does not give a very readable output
        pprint(item)

def get_database():
    
    # connect to MongoDB, change the << MONGODB URL >> to reflect your own connection string
    client = MongoClient("mongodb://ryan:ryan@localhost:27017")
    # Issue the serverStatus command and print the results
    return client['simulator']
    serverStatusResult=client['schedule'].command("serverStatus")
    pprint(serverStatusResult)

schedule.every(10).seconds.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)