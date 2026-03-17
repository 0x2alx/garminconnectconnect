from __future__ import annotations
from pymongo import MongoClient
from pymongo.database import Database
from garminconnect.config import settings


def get_mongo_client(url: str | None = None) -> MongoClient:
    return MongoClient(url or settings.mongo_url)


def get_mongo_db(url: str | None = None, db_name: str | None = None) -> Database:
    client = get_mongo_client(url)
    return client[db_name or settings.mongo_db]
