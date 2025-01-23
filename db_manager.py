import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
import time
from config import (
    MONGO_URI, DB_NAME, DB_POOL_SIZE, 
    DB_MAX_IDLE_TIME_MS, MAX_RETRIES, RETRY_DELAY
)

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize database connection with connection pooling"""
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Establish database connection with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                self.client = pymongo.MongoClient(
                    MONGO_URI,
                    maxPoolSize=DB_POOL_SIZE,
                    maxIdleTimeMS=DB_MAX_IDLE_TIME_MS
                )
                # Test the connection
                self.client.admin.command('ping')
                self.db = self.client[DB_NAME]
                logging.info("Successfully connected to MongoDB")
                return
            except (ConnectionFailure, OperationFailure) as e:
                if attempt == MAX_RETRIES - 1:
                    logging.error(f"Failed to connect to MongoDB after {MAX_RETRIES} attempts: {str(e)}")
                    raise
                logging.warning(f"Connection attempt {attempt + 1} failed, retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
    
    def get_database(self):
        """Get database instance with connection check"""
        try:
            self.client.admin.command('ping')
        except:
            logging.warning("Lost connection to MongoDB, attempting to reconnect...")
            self.connect()
        return self.db
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logging.info("Closed MongoDB connection")
    
    def __enter__(self):
        return self.get_database()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logging.error(f"An error occurred: {exc_type.__name__}: {exc_val}")
        # Don't close connection here as it's a singleton
