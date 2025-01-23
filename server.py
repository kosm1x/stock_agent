from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import logging
from db_manager import DatabaseManager
from datetime import datetime
import traceback

# Set up logging
logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize database connection
db_manager = DatabaseManager()
db = db_manager.get_database()

@app.route('/')
def index():
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        logging.error(f"Error serving index.html: {str(e)}")
        return jsonify({'error': 'Failed to load page'}), 500

@app.route('/api/stocks')
def get_stocks():
    try:
        stocks = list(db['stocks'].find())
        nodes = []
        links = []
        sector_dict = {}
        
        # First pass: organize stocks by sector and industry
        for stock in stocks:
            sector = stock.get('sector', 'Unknown')
            industry = stock.get('industry', 'Unknown')
            
            if sector not in sector_dict:
                sector_dict[sector] = {'industries': {}}
                
            if industry not in sector_dict[sector]['industries']:
                sector_dict[sector]['industries'][industry] = []
                
            sector_dict[sector]['industries'][industry].append(stock)

        # Second pass: create nodes and links
        # Add sector nodes first
        for sector in sector_dict:
            nodes.append({
                'id': f"sector_{sector}",
                'name': sector,
                'group': 'sector',
                'value': 30
            })
            
            # Add industry nodes for this sector
            for industry in sector_dict[sector]['industries']:
                industry_id = f"industry_{sector}_{industry}"
                nodes.append({
                    'id': industry_id,
                    'name': industry,
                    'group': 'industry',
                    'value': 20
                })
                # Link industry to sector
                links.append({
                    'source': f"sector_{sector}",
                    'target': industry_id,
                    'value': 2
                })
                
                # Add stock nodes for this industry
                for stock in sector_dict[sector]['industries'][industry]:
                    try:
                        # Get latest price data
                        latest_date = max(stock['data'].keys())
                        latest_price = stock['data'][latest_date]
                        indicators = stock.get('indicators', {})
                        
                        nodes.append({
                            'id': stock['symbol'],
                            'name': stock['symbol'],
                            'group': 'stock',
                            'value': 10,
                            'price': f"${latest_price['close']:.2f}",
                            'volume': f"{latest_price['volume']:,}",
                            'ao': f"{indicators.get('ao', 0):.2f}",
                            'ac': f"{indicators.get('ac', 0):.2f}"
                        })
                        # Link stock to industry
                        links.append({
                            'source': industry_id,
                            'target': stock['symbol'],
                            'value': 1
                        })
                    except Exception as e:
                        logging.error(f"Error processing stock {stock['symbol']}: {str(e)}")
                        continue

        return jsonify({'nodes': nodes, 'links': links})
    except Exception as e:
        logging.error(f"Error in get_stocks: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Failed to fetch stock data'}), 500

@app.route('/api/last-updated')
def get_last_updated():
    try:
        latest_stock = db['stocks'].find_one(sort=[('last_updated', -1)])
        last_updated = latest_stock.get('last_updated', '') if latest_stock else ''
        return jsonify({'last_updated': last_updated})
    except Exception as e:
        logging.error(f"Error in get_last_updated: {str(e)}")
        return jsonify({'error': 'Failed to fetch last update time'}), 500

if __name__ == '__main__':
    try:
        app.run(debug=True, port=5001)
    except Exception as e:
        logging.error(f"Server error: {str(e)}\n{traceback.format_exc()}")
