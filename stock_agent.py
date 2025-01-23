import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import random
import time
import traceback
import os
from db_manager import DatabaseManager
from api_manager import APIManager
import config

# Clear existing log file
try:
    if os.path.exists('stock_agent.log'):
        with open('stock_agent.log', 'w') as f:
            pass  # Just truncate the file
except Exception as e:
    print(f"Warning: Could not clear log file: {e}")

# Set up logging with rotation
log_handler = RotatingFileHandler(
    'stock_agent.log',
    maxBytes=100000,  # Approximately 1000 lines
    backupCount=1     # Keep one backup file
)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# Remove any existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
root_logger.addHandler(log_handler)

class StockAgent:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.api_manager = APIManager()
        self.db = self.db_manager.get_database()
    
    def convert_to_datetime(self, date_str):
        """Convert date string to datetime object"""
        return datetime.strptime(date_str, '%Y-%m-%d')

    def process_time_series(self, time_series):
        """Convert time series data with string dates to proper format"""
        processed_data = {}
        for date_str, values in time_series.items():
            processed_values = {
                'timestamp': self.convert_to_datetime(date_str).isoformat(),
                'open': float(values['1. open']),
                'high': float(values['2. high']),
                'low': float(values['3. low']),
                'close': float(values['4. close']),
                'volume': int(values['5. volume'])
            }
            processed_data[date_str] = processed_values
        return processed_data

    def get_random_stocks(self, num_stocks=35, is_initial=True):
        """Get random stocks from Alpha Vantage"""
        try:
            # Get current watchlist
            existing_stocks = set(doc['symbol'] for doc in self.db.watchlist.find())
            
            # Use smaller number for subsequent iterations
            if not is_initial:
                num_stocks = min(10, num_stocks)
            
            # Get listing of all US stocks
            listing_data = self.api_manager.get_stock_data(symbol=None, function='LISTING_STATUS')
            
            # Filter out existing stocks and get new ones
            new_stocks = [stock for stock in listing_data if stock['symbol'] not in existing_stocks]
            
            if new_stocks:
                # Randomly shuffle stocks to avoid always checking the same ones
                random.shuffle(new_stocks)
                selected = []
                
                # Try stocks until we have enough that meet our criteria
                for stock in new_stocks:
                    if len(selected) >= num_stocks:
                        break
                        
                    try:
                        # Get company overview for market cap
                        overview = self.api_manager.get_stock_data(
                            symbol=stock['symbol'],
                            function='OVERVIEW'
                        )
                        
                        # Get current price
                        quote = self.api_manager.get_stock_data(
                            symbol=stock['symbol'],
                            function='GLOBAL_QUOTE'
                        )
                        
                        # Get weekly data to verify history
                        weekly_data = self.api_manager.get_stock_data(
                            symbol=stock['symbol'],
                            function='TIME_SERIES_WEEKLY'
                        )
                        
                        # Verify we have some weekly data
                        time_series = weekly_data.get('Weekly Time Series', {})
                        if not time_series:
                            logging.info(f"Skipped {stock['symbol']} - No historical data available")
                            continue
                        
                        market_cap = float(overview.get('MarketCapitalization', 0))
                        price = float(quote.get('Global Quote', {}).get('05. price', 0))
                        
                        # Apply market cap and price constraints
                        if market_cap > 2_000_000_000 and price < 100:  # >$2B cap and <$100 price
                            selected.append(stock)
                            dates = sorted(time_series.keys())
                            oldest_date = dates[0] if dates else 'unknown'
                            logging.info(f"Selected {stock['symbol']} - Market Cap: ${market_cap:,.2f}, Price: ${price:.2f}, Data since: {oldest_date}")
                        else:
                            logging.info(f"Skipped {stock['symbol']} - Market Cap: ${market_cap:,.2f}, Price: ${price:.2f}")
                            
                    except Exception as e:
                        logging.warning(f"Error checking {stock['symbol']}: {str(e)}")
                        continue
                
                # Add selected stocks to watchlist
                for stock in selected:
                    self.db.watchlist.update_one(
                        {'symbol': stock['symbol']},
                        {'$set': {
                            'symbol': stock['symbol'],
                            'name': stock['name'],
                            'exchange': stock['exchange'],
                            'added_date': datetime.now().isoformat()
                        }},
                        upsert=True
                    )
                logging.info(f"Added {len(selected)} new stocks to watchlist")
            else:
                logging.info("No new stocks to add to watchlist")
                
        except Exception as e:
            logging.error(f"Error getting random stocks: {str(e)}")
            raise

    def get_stock_info(self, symbol):
        """Get company overview including sector, industry, and market cap"""
        try:
            overview_data = self.api_manager.get_stock_data(
                symbol=symbol, 
                function='OVERVIEW'
            )
            return overview_data
        except Exception as e:
            logging.error(f"Error getting stock info for {symbol}: {str(e)}")
            raise

    def fetch_stock_data(self, symbol):
        """Fetch weekly stock data from Alpha Vantage"""
        try:
            weekly_data = self.api_manager.get_stock_data(
                symbol=symbol,
                function='TIME_SERIES_WEEKLY'
            )
            return self.process_time_series(weekly_data['Weekly Time Series'])
        except Exception as e:
            logging.error(f"Error fetching stock data for {symbol}: {str(e)}")
            raise

    def calculate_indicators(self, data):
        """Calculate technical indicators using weekly data"""
        try:
            if not data:
                logging.warning("No data provided for indicator calculation")
                return None
                
            # Sort data by date
            dates = sorted(data.keys())
            if len(dates) < 34:  # Need at least 34 weeks for calculations
                logging.warning(f"Insufficient data points for indicator calculation. Need 34, got {len(dates)}")
                return None

            # Get high and low values for AO calculation
            highs = [float(data[date]['high']) for date in dates]
            lows = [float(data[date]['low']) for date in dates]
            
            # Calculate median prices for different periods
            median_prices = [(high + low) / 2 for high, low in zip(highs, lows)]
            
            # Calculate 5-period and 34-period SMAs for AO
            sma5 = sum(median_prices[-5:]) / 5
            sma34 = sum(median_prices[-34:]) / 34
            
            # Calculate Awesome Oscillator (AO)
            ao = sma5 - sma34
            
            # Calculate Acceleration/Deceleration (AC)
            # AC = AO - 5-period SMA of AO
            if len(dates) >= 39:  # Need 5 more periods for AO history
                prev_aos = []
                for i in range(5):
                    idx = -(5+i)
                    prev_sma5 = sum(median_prices[idx:idx+5]) / 5
                    prev_sma34 = sum(median_prices[idx-29:idx+5]) / 34
                    prev_aos.append(prev_sma5 - prev_sma34)
                ac = ao - (sum(prev_aos) / 5)
            else:
                logging.warning(f"Insufficient data points for AC calculation. Need 39, got {len(dates)}")
                ac = None

            return {
                'ao': ao,
                'ac': ac,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error calculating indicators: {str(e)}")
            return None

    def update_stock_data(self):
        """Update stock data in MongoDB"""
        try:
            watchlist = list(self.db.watchlist.find())
            
            for stock in watchlist:
                symbol = stock['symbol']
                logging.info(f"Updating data for {symbol}")
                
                # Get stock info and weekly data
                info = self.get_stock_info(symbol)
                weekly_data = self.fetch_stock_data(symbol)
                
                # Calculate indicators
                indicators = self.calculate_indicators(weekly_data)
                
                # Prepare document
                doc = {
                    'symbol': symbol,
                    'sector': info.get('Sector'),
                    'industry': info.get('Industry'),
                    'market_cap': info.get('MarketCapitalization'),
                    'data': weekly_data,
                    'indicators': indicators,
                    'last_update': datetime.now().isoformat()
                }
                
                # Update or insert
                self.db.stocks.update_one(
                    {'symbol': symbol},
                    {'$set': doc},
                    upsert=True
                )
                
                time.sleep(12)  # Respect API rate limits
                
        except Exception as e:
            logging.error(f"Error in update_stock_data: {str(e)}\n{traceback.format_exc()}")
            raise

    def run(self):
        """Run the stock agent"""
        try:
            # Get initial batch of stocks
            self.get_random_stocks(is_initial=True)
            
            # Main loop
            while True:
                try:
                    # Update stock data
                    self.update_stock_data()
                    
                    # Calculate indicators
                    self.calculate_indicators(None)
                    
                    # Get more stocks if needed
                    watchlist = list(self.db.watchlist.find())
                    if len(watchlist) < 35:
                        self.get_random_stocks(is_initial=False)
                    
                    # Sleep for 15 minutes
                    logging.info("Sleeping for 15 minutes...")
                    time.sleep(15 * 60)
                    
                except Exception as e:
                    logging.error(f"Error in main loop: {str(e)}")
                    raise
                    
        except Exception as e:
            logging.error(f"Error in run: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup resources"""
        self.api_manager.close()
        self.db_manager.close()

def main():
    agent = StockAgent()
    agent.run()

if __name__ == '__main__':
    main()
