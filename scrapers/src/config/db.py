import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/?serverSelectionTimeoutMS=5000")

def connect_db():
    client = MongoClient(MONGO_URI)
    return client['genshin_data']