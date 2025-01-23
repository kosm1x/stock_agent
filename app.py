from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from db_manager import DatabaseManager
import os

app = Flask(__name__)
CORS(app)

# Initialize database connection
db = DatabaseManager().get_database()

@app.route('/')
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), path)

@app.route('/api/stocks')
def get_stocks():
    # Get all stocks with their data and indicators
    stocks = list(db.stocks.find({}, {'_id': 0}))
    print(f"Found {len(stocks)} stocks")
    
    # Transform data for visualization
    sectors = {}
    result = []
    
    # Group stocks by sector
    for stock in stocks:
        sector = stock.get('sector', 'Unknown')
        if sector == 'None':
            sector = 'Unknown'
            
        if sector not in sectors:
            sectors[sector] = {
                'name': sector,
                'type': 'sector',
                'children': {}  # Industries within this sector
            }
            
        industry = stock.get('industry', 'Unknown')
        if industry == 'None':
            industry = 'Unknown'
            
        if industry not in sectors[sector]['children']:
            sectors[sector]['children'][industry] = {
                'name': industry,
                'type': 'industry',
                'children': []  # Stocks within this industry
            }
            
        # Add stock to its industry
        market_cap = float(stock.get('market_cap', 0)) if stock.get('market_cap') not in [None, 'None'] else 0
        indicators = stock.get('indicators') or {}
        stock_data = {
            'name': stock.get('symbol'),
            'type': 'stock',
            'market_cap': market_cap,
            'price': float(stock.get('price', 0)),
            'volume': float(stock.get('volume', 0)),
            'ao': float(indicators.get('ao', 0)),
            'ac': float(indicators.get('ac', 0)),
            'sector': sector,
            'industry': industry
        }
        print(f"Processing stock {stock_data['name']}: price={stock_data['price']}, volume={stock_data['volume']}")
        sectors[sector]['children'][industry]['children'].append(stock_data)
    
    # Convert to list format
    for sector_name, sector_data in sectors.items():
        sector_node = {
            'name': sector_name,
            'type': 'sector',
            'children': []
        }
        
        for industry_name, industry_data in sector_data['children'].items():
            industry_node = {
                'name': industry_name,
                'type': 'industry',
                'children': industry_data['children']
            }
            sector_node['children'].append(industry_node)
            
        result.append(sector_node)
    
    print(f"Returning {len(result)} sectors")
    return jsonify(result)

@app.route('/api/watchlist')
def get_watchlist():
    # Get current watchlist
    watchlist = list(db.watchlist.find({}, {'_id': 0}))
    return jsonify(watchlist)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
