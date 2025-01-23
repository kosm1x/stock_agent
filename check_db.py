import pymongo
from pymongo import MongoClient
import json

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://fmoctezuma:7NqAJ5A37xbR2D0N@cluster0.29urq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def check_stocks():
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client['stock_data']
        
        # Count total stocks
        total_stocks = db['stocks'].count_documents({})
        print(f"\nTotal stocks in database: {total_stocks}")
        
        # Get unique sectors
        sectors = db['stocks'].distinct('sector')
        print("\nUnique sectors:")
        for sector in sectors:
            count = db['stocks'].count_documents({'sector': sector})
            print(f"- {sector}: {count} stocks")
            
        # Get some sample stocks
        print("\nSample stocks:")
        for stock in db['stocks'].find().limit(5):
            print(f"- {stock['symbol']}: {stock['sector']} - {stock['industry']}")
            
        # Get a sample stock document
        sample_stock = db['stocks'].find_one()
        if sample_stock:
            print("\nAvailable fields in stock document:")
            for field in sample_stock:
                print(f"- {field}: {sample_stock[field]}")
        else:
            print("\nNo stock documents found in database")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

def print_stock_data(symbol=None):
    try:
        # Get a sample stock or specific stock
        if symbol:
            stock = db['stocks'].find_one({'symbol': symbol})
        else:
            stock = db['stocks'].find_one()
            
        if stock:
            print(f"\nStock: {stock['symbol']}")
            print("\nIndicators:")
            print(json.dumps(stock['indicators'], indent=2))
            
            print("\nSample of weekly data:")
            # Print first few weeks of data
            for date in list(stock['data'].keys())[:5]:
                print(f"\n{date}:")
                print(json.dumps(stock['data'][date], indent=2))
        else:
            print("No stock found")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    try:
        client = MongoClient(MONGO_URI)
        db = client['stock_data']
        
        check_stocks()
        
        # Print data for a few stocks
        stocks = list(db['stocks'].find({}, {'symbol': 1}).limit(3))
        for stock in stocks:
            print_stock_data(stock['symbol'])
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == '__main__':
    main()
