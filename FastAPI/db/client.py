#from pymongo import MongoClient

# db_client = MongoClient().local #Si no pones nada es localhost

#db_client = MongoClient("mongodb+srv://customdrago11_db_user:test@cluster0.pj5iijy.mongodb.net/?appName=Cluster0").local


import os

from dotenv import load_dotenv
from fastapi import HTTPException, status
from pymongo import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

uri = os.getenv("MONGODB_URI")
db_name = os.getenv("MONGODB_DB_NAME", "test")
mongo_client = MongoClient(uri, server_api=ServerApi("1")) if uri else None


def get_users_collection():
    if mongo_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MONGODB_URI no configurada",
        )

    return mongo_client[db_name]["users"]