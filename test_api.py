import requests
import json

def test_api():
    try:
        # Test stocks endpoint
        response = requests.get('http://localhost:5001/api/stocks')
        stocks = response.json()
        print("\nAPI /api/stocks response:")
        print(f"Status code: {response.status_code}")
        print(f"Number of stocks: {len(stocks)}")
        if stocks:
            print("\nFirst stock data:")
            print(json.dumps(stocks[0], indent=2))
        else:
            print("No stocks returned")
            
        # Test watchlist endpoint
        response = requests.get('http://localhost:5001/api/watchlist')
        watchlist = response.json()
        print("\nAPI /api/watchlist response:")
        print(f"Status code: {response.status_code}")
        print(f"Number of stocks: {len(watchlist)}")
        if watchlist:
            print("\nFirst watchlist item:")
            print(json.dumps(watchlist[0], indent=2))
        else:
            print("No watchlist items returned")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    test_api()
