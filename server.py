from flask import Flask, jsonify, send_from_directory
import pymongo
from datetime import datetime

app = Flask(__name__)

# MongoDB connection
MONGO_URI = "mongodb+srv://fmoctezuma:7NqAJ5A37xbR2D0N@cluster0.29urq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URI)
db = client['stock_data']

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stocks')
def get_stocks():
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
                # Get latest price data
                latest_date = max(stock['data'].keys())
                latest_price = stock['data'][latest_date]
                
                nodes.append({
                    'id': stock['symbol'],
                    'name': stock['symbol'],
                    'group': 'stock',
                    'value': 10,
                    'price': f"${latest_price['close']:.2f}",
                    'volume': f"{latest_price['volume']:,}",
                    'ao': f"{stock['indicators']['ao']:.2f}",
                    'ac': f"{stock['indicators']['ac']:.2f}"
                })
                # Link stock to industry
                links.append({
                    'source': industry_id,
                    'target': stock['symbol'],
                    'value': 1
                })

    return jsonify({'nodes': nodes, 'links': links})

@app.route('/api/last-updated')
def get_last_updated():
    latest_stock = db['stocks'].find_one(sort=[('last_updated', -1)])
    last_updated = latest_stock.get('last_updated', '') if latest_stock else ''
    return last_updated

if __name__ == '__main__':
    app.run(debug=True, port=5003)
