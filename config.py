import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DB_NAME = 'stock_data'
DB_POOL_SIZE = 100
DB_MAX_IDLE_TIME_MS = 10000
DB_RETRY_WRITES = True

# API Configuration
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
ALPHA_VANTAGE_BASE_URL = 'https://www.alphavantage.co/query'
MAX_REQUESTS_PER_MINUTE = 75
REQUEST_TIMEOUT = 10  # seconds

# Local API Configuration
LOCAL_API_BASE_URL = 'http://localhost:5001'
LOCAL_API_TIMEOUT = 5  # seconds

# Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
