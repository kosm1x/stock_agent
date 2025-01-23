import requests
import pymongo
import logging
from datetime import datetime, timedelta
import random
import time
import traceback

# Set up logging
logging.basicConfig(
    filename='stock_agent.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://fmoctezuma:7NqAJ5A37xbR2D0N@cluster0.29urq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
try:
    mongo_client = pymongo.MongoClient(MONGO_URI)
    db = mongo_client['stock_data']
    logging.info("Successfully connected to MongoDB Atlas")
except Exception as e:
    logging.error(f"Error connecting to MongoDB Atlas: {str(e)}")
    raise

# Alpha Vantage API configuration
API_KEY = 'CWIA9S112Q0BHF6N'
MAX_REQUESTS_PER_MINUTE = 75

def convert_to_datetime(date_str):
    """Convert date string to datetime object"""
    return datetime.strptime(date_str, '%Y-%m-%d')

def process_time_series(time_series):
    """Convert time series data with string dates to proper format"""
    processed_data = {}
    for date_str, values in time_series.items():
        # Convert string values to float
        processed_values = {
            'timestamp': convert_to_datetime(date_str).isoformat(),  # Store as ISODate
            'open': float(values['1. open']),
            'high': float(values['2. high']),
            'low': float(values['3. low']),
            'close': float(values['4. close']),
            'volume': int(values['5. volume'])
        }
        processed_data[date_str] = processed_values  # Keep string as key
    return processed_data

def trim_log_file(max_lines=1000):
    """Trim the log file to keep only the last N lines"""
    try:
        with open('stock_agent.log', 'r') as f:
            lines = f.readlines()
        
        if len(lines) > max_lines:
            with open('stock_agent.log', 'w') as f:
                f.writelines(lines[-max_lines:])
            logging.info(f"Trimmed log file to last {max_lines} lines")
    except Exception as e:
        logging.error(f"Error trimming log file: {str(e)}")

def get_random_stocks(num_stocks=35):
    """Get random stocks from Alpha Vantage listing"""
    try:
        url = f'https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={API_KEY}'
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch stock listing: {response.status_code}")
        
        # Split the CSV content into lines and skip header
        lines = response.text.strip().split('\n')[1:]
        logging.info(f"Total available stocks: {len(lines)}")
        
        stocks = []
        for line in lines:
            symbol, name, exchange, _, _, _, _ = line.split(',')
            # Only include stocks from major exchanges
            if exchange in ['NYSE', 'NASDAQ']:
                stocks.append({'symbol': symbol, 'name': name})
        
        logging.info(f"Filtered stocks from major exchanges: {len(stocks)}")
        selected_stocks = random.sample(stocks, min(num_stocks, len(stocks)))
        logging.info(f"Selected {len(selected_stocks)} new random stocks")
        return selected_stocks
    
    except Exception as e:
        logging.error(f"Error getting random stocks: {str(e)}")
        raise

def get_stock_info(symbol):
    """Get company overview including sector, industry, and market cap"""
    try:
        url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}'
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch stock info: {response.status_code}")
            
        data = response.json()
        if not data:
            return None
            
        # Get market cap and convert to numeric value
        market_cap_str = data.get('MarketCapitalization', '0')
        market_cap = float(market_cap_str)
        
        # Check minimum market cap (2B = 2,000,000,000)
        if market_cap < 2000000000:
            logging.info(f"Skipping {symbol}: Market cap below 2B")
            return None
            
        sector = data.get('Sector', '')
        industry = data.get('Industry', '')
        
        # Skip if sector or industry is empty or unknown
        if not sector or not industry or sector.upper() == 'UNKNOWN' or industry.upper() == 'UNKNOWN':
            logging.info(f"Skipping {symbol}: Unknown sector or industry")
            return None
            
        return {
            'name': data.get('Name', symbol),
            'sector': sector,
            'industry': industry,
            'market_cap': market_cap
        }
        
    except Exception as e:
        logging.error(f"Error getting stock info for {symbol}: {str(e)}")
        return None

def fetch_stock_data(symbol):
    """Fetch weekly stock data from Alpha Vantage"""
    try:
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={symbol}&apikey={API_KEY}'
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch stock data: {response.status_code}")
            
        data = response.json()
        if 'Weekly Time Series' not in data:
            logging.error(f"No weekly time series data for {symbol}")
            return {}
            
        time_series = data['Weekly Time Series']
        processed_data = {}
        
        # Process only the last 52 weeks (1 year) of data
        for date, values in list(time_series.items())[:52]:
            processed_data[date] = {
                'timestamp': convert_to_datetime(date).isoformat(),
                'open': float(values['1. open']),
                'high': float(values['2. high']),
                'low': float(values['3. low']),
                'close': float(values['4. close']),
                'volume': int(values['5. volume'])
            }
            
        return processed_data
    except Exception as e:
        logging.error(f"Error fetching stock data: {str(e)}")
        return {}

def calculate_ao_ac(data):
    """Calculate Awesome Oscillator (AO) and Acceleration/Deceleration (AC) using weekly data"""
    try:
        # Sort dates in ascending order
        sorted_dates = sorted(data.keys(), key=lambda x: datetime.fromisoformat(data[x]['timestamp']))
        if len(sorted_dates) < 34:
            logging.warning(f"Not enough data points for AO/AC calculation. Only have {len(sorted_dates)} weeks, need 34.")
            return 0, 0

        # Calculate median prices for each week
        prices = []
        for date in sorted_dates:
            values = data[date]
            high = float(values['high'])
            low = float(values['low'])
            median = (high + low) / 2
            prices.append(median)

        # Calculate AO (5-week SMA - 34-week SMA)
        sma5 = sum(prices[-5:]) / 5
        sma34 = sum(prices[-34:]) / 34
        ao = round(sma5 - sma34, 4)

        # For AC, we need 5 periods of AO values
        if len(prices) < 39:
            logging.warning(f"Not enough data points for AC calculation. Only have {len(sorted_dates)} weeks, need 39.")
            return ao, 0

        # Calculate AO for each of the last 5 periods
        ao_values = []
        for i in range(5):
            idx = -(5 - i)  # Start from -5 to -1
            period_prices = prices[:(idx or None)]  # Use all prices up to this point
            if len(period_prices) >= 34:
                sma5_period = sum(period_prices[-5:]) / 5
                sma34_period = sum(period_prices[-34:]) / 34
                ao_period = sma5_period - sma34_period
                ao_values.append(ao_period)
            else:
                logging.warning(f"Not enough historical prices for period {i}")

        if len(ao_values) == 5:
            # AC is AO minus SMA5 of AO
            ao_sma = sum(ao_values) / 5
            ac = round(ao - ao_sma, 4)
            logging.info(f"Calculated AC using AO values: {ao_values}, SMA5: {ao_sma}, Final AC: {ac}")
        else:
            ac = 0
            logging.warning(f"Could not calculate AC: only got {len(ao_values)} AO values, need 5")

        logging.info(f"Final indicators - AO: {ao}, AC: {ac}")
        return ao, ac

    except Exception as e:
        logging.error(f"Error calculating AO/AC: {str(e)}")
        traceback.print_exc()
        return 0, 0

def update_stock_data():
    """Update stock data in MongoDB without replacing existing records"""
    try:
        # Get MongoDB connection
        client = pymongo.MongoClient(MONGO_URI)
        db = client['stock_data']
        
        processed_count = 0
        max_attempts = 5  # Maximum number of attempts to get enough stocks
        target_stocks = 35  # Number of stocks we want to process
        wait_time = 15  # Increased wait time between API calls
        
        for attempt in range(max_attempts):
            if processed_count >= target_stocks:
                break
                
            # Get new random stocks
            num_needed = target_stocks - processed_count
            stocks = get_random_stocks(num_needed * 3)  # Get 3x the number needed to account for filtering
            logging.info(f"Attempt {attempt + 1}: Attempting to process {len(stocks)} stocks, need {num_needed} more")
            
            # Process each stock
            for stock in stocks:
                if processed_count >= target_stocks:
                    break
                    
                try:
                    # Get stock info including sector and industry
                    info = get_stock_info(stock['symbol'])
                    if info is None:
                        logging.info(f"Skipping {stock['symbol']}: Did not meet criteria")
                        continue
                    
                    logging.info(f"Processing {stock['symbol']} - {info['sector']} - {info['industry']} - Market Cap: ${info['market_cap']:,.2f}")
                    time.sleep(wait_time)  # Rate limiting for Alpha Vantage API
                    
                    # Get weekly time series data
                    data = fetch_stock_data(stock['symbol'])
                    
                    # Prepare document
                    stock_doc = {
                        'symbol': stock['symbol'],
                        'name': info['name'],
                        'sector': info['sector'],
                        'industry': info['industry'],
                        'market_cap': info['market_cap'],
                        'last_updated': datetime.now().isoformat(),
                        'data': data
                    }
                    
                    # Check if stock already exists
                    existing_stock = db['stocks'].find_one({'symbol': stock['symbol']})
                    if existing_stock:
                        # Update existing stock
                        db['stocks'].update_one(
                            {'symbol': stock['symbol']}, 
                            {'$set': stock_doc}
                        )
                        logging.info(f"Updated existing stock: {stock['symbol']}")
                    else:
                        # Insert new stock
                        db['stocks'].insert_one(stock_doc)
                        logging.info(f"Inserted new stock: {stock['symbol']}")
                    
                    processed_count += 1
                    time.sleep(wait_time)  # Rate limiting for Alpha Vantage API
                    
                except Exception as e:
                    logging.error(f"Error processing {stock['symbol']}: {str(e)}")
                    continue
            
            if processed_count < target_stocks:
                logging.info(f"Waiting 60 seconds before next attempt...")
                time.sleep(60)  # Wait longer between attempts
        
        logging.info(f"Successfully processed {processed_count} stocks")
                
    except Exception as e:
        logging.error(f"Error updating stock data: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

def refresh_watchlist():
    """Refresh the watchlist with new random stocks"""
    try:
        db['watchlist'].delete_many({})
        new_stocks = get_random_stocks()
        
        if new_stocks:
            db['watchlist'].insert_many(new_stocks)
            logging.info(f"Refreshed watchlist with {len(new_stocks)} new stocks")
        
        return new_stocks
    except Exception as e:
        logging.error(f"Error refreshing watchlist: {str(e)}")
        raise

def fetch_stocks():
    """Fetch stocks from watchlist collection"""
    try:
        stocks = refresh_watchlist()
        return stocks
    except Exception as e:
        logging.error(f"Error fetching stocks: {str(e)}")
        raise

def run_agent():
    logging.info('Agent started')
    try:
        stocks = fetch_stocks()
        total_stocks = len(stocks)
        
        for index, stock in enumerate(stocks):
            try:
                logging.info(f"Processing {stock['symbol']} ({index + 1}/{total_stocks})")
                
                # Get stock info including sector and industry
                info = get_stock_info(stock['symbol'])
                if info is None:
                    continue
                
                # Fetch stock data
                data = fetch_stock_data(stock['symbol'])
                
                # Calculate indicators
                ao, ac = calculate_ao_ac(data)
                
                # Prepare document with proper datetime objects
                stock_doc = {
                    'symbol': stock['symbol'],
                    'name': info['name'],
                    'sector': info['sector'],
                    'industry': info['industry'],
                    'market_cap': info['market_cap'],
                    'last_updated': datetime.now().isoformat(),
                    'data': data,
                    'indicators': {
                        'ao': ao,
                        'ac': ac,
                        'entry_condition': ao + ac > 0,
                        'calculated_at': datetime.now().isoformat()
                    }
                }
                
                # Insert new data
                db['stocks'].insert_one(stock_doc)
                logging.info(f"Successfully updated {stock['symbol']}")
                
                # Status update
                percent_done = ((index + 1) / total_stocks) * 100
                logging.info(f'Progress: {percent_done:.2f}% done')
                
                # Respect API rate limit
                if index < total_stocks - 1:
                    time.sleep(60 / MAX_REQUESTS_PER_MINUTE)
                
            except Exception as e:
                logging.error(f"Error processing {stock['symbol']}: {str(e)}")
                continue
                
    except Exception as e:
        logging.error(f"Agent error: {str(e)}")
    finally:
        logging.info('Agent finished')

def test_alpha_vantage_connection():
    """Test connection to Alpha Vantage and log response"""
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey={API_KEY}'
    try:
        response = requests.get(url)
        logging.info(f"Test request status: {response.status_code}")
        logging.info(f"Test request content: {response.text[:200]}")  # Log first 200 characters
    except Exception as e:
        logging.error(f"Error testing Alpha Vantage connection: {str(e)}")

def clear_database():
    """Clear all collections in the database"""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client['stock_data']
        db['stocks'].delete_many({})
        logging.info("Successfully cleared all collections")
    except Exception as e:
        logging.error(f"Error clearing database: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == '__main__':
    trim_log_file()  # Trim log file before starting
    run_agent()
