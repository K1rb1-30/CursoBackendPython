#from pymongo import MongoClient

# db_client = MongoClient().local #Si no pones nada es localhost

#db_client = MongoClient("mongodb+srv://customdrago11_db_user:test@cluster0.pj5iijy.mongodb.net/?appName=Cluster0").local


from pymongo import MongoClient
from pymongo.server_api import ServerApi

import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("MONGODB_URI")

# Create a new client and connect to the server
db_client = MongoClient(uri, server_api=ServerApi('1')).test

# Send a ping to confirm a successful connection
try:
    db_client.client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)