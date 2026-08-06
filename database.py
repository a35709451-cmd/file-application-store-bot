import json
import os
import shutil
from datetime import datetime
import motor.motor_asyncio
from config import MONGODB_URI, MONGODB_DB_NAME, logger

class DatabaseManager:
    def __init__(self):
        self.use_mongo = False
        self.client = None
        self.db = None
        
        if MONGODB_URI:
            try:
                self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
                self.db = self.client[MONGODB_DB_NAME]
                self.use_mongo = True
                logger.info("✅ MongoDB connected successfully!")
            except Exception as e:
                logger.error(f"MongoDB connection failed: {e}")
        
        # Local JSON fallback
        self.users = self._load_json("users.json", {})
        self.files = self._load_json("files.json", {})
        self.folders = self._load_json("folders.json", {})
        self.quizzes = self._load_json("quizzes.json", {})
        self.approvals = self._load_json("approvals.json", {})
        
    def _load_json(self, filename, default):
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
        return default

    def _save_json(self, filename, data):
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")

    async def sync_to_mongo(self, collection, data):
        if not self.use_mongo:
            return
        try:
            await self.db[collection].update_one(
                {"_id": "main"},
                {"$set": {"data": data}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"MongoDB sync error: {e}")

    async def save_all(self):
        self._save_json("users.json", self.users)
        self._save_json("files.json", self.files)
        self._save_json("folders.json", self.folders)
        self._save_json("quizzes.json", self.quizzes)
        self._save_json("approvals.json", self.approvals)
        
        if self.use_mongo:
            await self.sync_to_mongo("users", self.users)
            await self.sync_to_mongo("files", self.files)
            await self.sync_to_mongo("folders", self.folders)
            await self.sync_to_mongo("quizzes", self.quizzes)
            await self.sync_to_mongo("approvals", self.approvals)

    async def load_from_mongo(self, collection):
        if not self.use_mongo:
            return None
        try:
            result = await self.db[collection].find_one({"_id": "main"})
            return result.get("data") if result else None
        except Exception as e:
            logger.error(f"MongoDB load error: {e}")
            return None

    async def load_all(self):
        if not self.use_mongo:
            return
        users_data = await self.load_from_mongo("users")
        if users_data: self.users = users_data
        
        files_data = await self.load_from_mongo("files")
        if files_data: self.files = files_data
        
        folders_data = await self.load_from_mongo("folders")
        if folders_data: self.folders = folders_data
        
        quizzes_data = await self.load_from_mongo("quizzes")
        if quizzes_data: self.quizzes = quizzes_data
        
        approvals_data = await self.load_from_mongo("approvals")
        if approvals_data: self.approvals = approvals_data
        
        logger.info("✅ Data loaded from MongoDB successfully!")

db = DatabaseManager()
