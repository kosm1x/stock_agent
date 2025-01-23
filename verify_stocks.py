from db_manager import DatabaseManager
from api_manager import APIManager
import logging
from datetime import datetime

def verify_stock(api_manager, symbol):
    try:
        # Get current data
        overview = api_manager.get_stock_data(symbol=symbol, function='OVERVIEW')
        quote = api_manager.get_stock_data(symbol=symbol, function='GLOBAL_QUOTE')
        weekly = api_manager.get_stock_data(symbol=symbol, function='TIME_SERIES_WEEKLY')
        
        # Extract key metrics
        market_cap = float(overview.get('MarketCapitalization', 0))
        price = float(quote.get('Global Quote', {}).get('05. price', 0))
        time_series = weekly.get('Weekly Time Series', {})
        dates = sorted(time_series.keys()) if time_series else []
        
        # Check constraints
        if market_cap < 2_000_000_000:
            return False, f"Market cap too low: ${market_cap:,.2f}"
        if price >= 100:
            return False, f"Price too high: ${price:.2f}"
        if not dates:
            return False, "No historical data"
            
        return True, f"Valid - Market Cap: ${market_cap:,.2f}, Price: ${price:.2f}, Data since: {dates[0] if dates else 'N/A'}"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    logging.basicConfig(level=logging.INFO)
    db = DatabaseManager().get_database()
    api = APIManager()
    
    print("\nVerifying stocks...")
    print("-" * 80)
    
    valid_stocks = []
    for doc in db.watchlist.find():
        symbol = doc['symbol']
        is_valid, reason = verify_stock(api, symbol)
        status = "[PASS]" if is_valid else "[FAIL]"
        print(f"{status} {symbol:<10} {reason}")
        if is_valid:
            valid_stocks.append(doc)
            
    # Update database to only keep valid stocks
    db.watchlist.delete_many({})
    if valid_stocks:
        db.watchlist.insert_many(valid_stocks)
    
    print("-" * 80)
    print(f"Found {len(valid_stocks)} valid stocks")

if __name__ == "__main__":
    main()
