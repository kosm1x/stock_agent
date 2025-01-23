from db_manager import DatabaseManager
import json

def check_stocks():
    try:
        db = DatabaseManager().get_database()
        
        # Count total stocks
        total_stocks = db.stocks.count_documents({})
        print(f"\nTotal stocks in database: {total_stocks}")
        
        # Get unique sectors
        sectors = db.stocks.distinct('sector')
        print("\nUnique sectors:")
        for sector in sectors:
            count = db.stocks.count_documents({'sector': sector})
            print(f"- {sector}: {count} stocks")
            
        # Get some sample stocks
        print("\nSample stocks:")
        for stock in db.stocks.find().limit(5):
            print(f"- {stock['symbol']}: {stock.get('sector', 'N/A')} - {stock.get('industry', 'N/A')}")
            
        # Count watchlist stocks
        watchlist_count = db.watchlist.count_documents({})
        print(f"\nTotal stocks in watchlist: {watchlist_count}")
        print("\nWatchlist stocks:")
        for stock in db.watchlist.find():
            print(f"- {stock['symbol']}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    check_stocks()
