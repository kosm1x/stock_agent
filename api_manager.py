import requests
import logging
import time
import os
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from config import (
    LOCAL_API_BASE_URL, LOCAL_API_TIMEOUT, 
    ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL,
    MAX_REQUESTS_PER_MINUTE, REQUEST_TIMEOUT,
    MAX_RETRIES, RETRY_DELAY
)

# Constants
ALPHA_VANTAGE_BASE_URL = ALPHA_VANTAGE_BASE_URL
ALPHA_VANTAGE_API_KEY = ALPHA_VANTAGE_API_KEY
MAX_REQUESTS_PER_MINUTE = MAX_REQUESTS_PER_MINUTE  # Free tier limit
REQUEST_TIMEOUT = REQUEST_TIMEOUT  # seconds
MAX_RETRIES = MAX_RETRIES
RETRY_DELAY = RETRY_DELAY  # seconds
LOCAL_API_TIMEOUT = LOCAL_API_TIMEOUT  # seconds

class APIManager:
    def __init__(self):
        """Initialize API manager"""
        self.session = self._create_session()
        self.last_request_time = 0
        self.requests_per_minute = 0
        self.max_requests_per_minute = MAX_REQUESTS_PER_MINUTE
        
        # Log API key status
        if not ALPHA_VANTAGE_API_KEY:
            logging.error("No Alpha Vantage API key found!")
        else:
            logging.info("Alpha Vantage API key is configured")
            
        self.verify_api_access()
    
    def _create_session(self):
        """Create a session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def verify_api_access(self):
        """Verify API access and limits"""
        try:
            # Test API access with a simple request
            params = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': 'IBM',  # Use IBM as test symbol
                'interval': '1min',
                'apikey': ALPHA_VANTAGE_API_KEY
            }
            
            response = self.session.get(
                ALPHA_VANTAGE_BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Check for API limit message
            if 'Note' in data:
                logging.warning(f"API Limit Warning: {data['Note']}")
                if 'premium' in data['Note'].lower():
                    raise Exception("API key appears to be hitting standard API limits. Please check your subscription level.")
            
            logging.info("API access verified successfully")
            
        except Exception as e:
            logging.error(f"Failed to verify API access: {str(e)}")
            raise
    
    def _handle_rate_limit(self):
        """Handle API rate limiting"""
        current_time = time.time()
        
        # Reset counter if a minute has passed
        if current_time - self.last_request_time >= 60:
            self.requests_per_minute = 0
            self.last_request_time = current_time
        
        # Check if we're at the limit
        if self.requests_per_minute >= self.max_requests_per_minute:
            sleep_time = 60 - (current_time - self.last_request_time)
            if sleep_time > 0:
                logging.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.requests_per_minute = 0
                self.last_request_time = time.time()
        
        # Increment request counter
        self.requests_per_minute += 1
    
    def get_stock_data(self, symbol, function='TIME_SERIES_WEEKLY'):
        """Get stock data from Alpha Vantage"""
        try:
            self._handle_rate_limit()
            
            params = {
                'function': function,
                'apikey': ALPHA_VANTAGE_API_KEY
            }
            
            if function != 'LISTING_STATUS':
                params['symbol'] = symbol
                
            logging.info(f"Making API request for {function} {'for ' + symbol if symbol else ''}")
            
            response = self.session.get(
                ALPHA_VANTAGE_BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            
            logging.info(f"API response status code: {response.status_code}")
            
            if response.status_code != 200:
                logging.error(f"API error response: {response.text}")
                response.raise_for_status()
            
            if function == 'LISTING_STATUS':
                # Log the raw response for debugging
                logging.info(f"Raw listing response: {response.text[:1000]}")  # Log first 1000 chars
                
                # Parse CSV response
                lines = [line.strip() for line in response.text.strip().split('\n')]
                if len(lines) < 2:  # Need at least header and one data row
                    logging.error(f"Not enough lines in response. Lines: {len(lines)}")
                    return []
                    
                header = [h.strip() for h in lines[0].split(',')]
                logging.info(f"CSV header: {header}")
                
                stocks = []
                for line in lines[1:]:
                    if not line.strip():  # Skip empty lines
                        continue
                    values = [v.strip() for v in line.split(',')]
                    if len(values) == len(header):
                        stock = dict(zip(header, values))
                        if stock.get('status') == 'Active' and stock.get('assetType') == 'Stock':
                            stocks.append({
                                'symbol': stock.get('symbol', ''),
                                'name': stock.get('name', ''),
                                'exchange': stock.get('exchange', '')
                            })
                logging.info(f"Processed {len(stocks)} stocks from listing")
                return stocks
            else:
                return response.json()
            
        except Exception as e:
            logging.error(f"Error fetching stock data: {str(e)}")
            raise
    
    def get_local_stock_data(self):
        """Get stock data from local API"""
        try:
            response = self.session.get(
                f"{LOCAL_API_BASE_URL}/api/stocks",
                timeout=LOCAL_API_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching local stock data: {str(e)}")
            raise
    
    def close(self):
        """Close the session"""
        self.session.close()
