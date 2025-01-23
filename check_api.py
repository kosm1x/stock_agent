import requests
import json

try:
    response = requests.get('http://localhost:5001/api/stocks')
    data = response.json()
    
    stock_nodes = [n for n in data['nodes'] if n['group'] == 'stock']
    sector_nodes = [n for n in data['nodes'] if n['group'] == 'sector']
    industry_nodes = [n for n in data['nodes'] if n['group'] == 'industry']
    
    print(f"API Response Analysis:")
    print(f"Stock nodes: {len(stock_nodes)}")
    print(f"Sector nodes: {len(sector_nodes)}")
    print(f"Industry nodes: {len(industry_nodes)}")
    print(f"Total nodes: {len(data['nodes'])}")
    print(f"Total links: {len(data['links'])}")
    
    print("\nSectors:")
    for node in sector_nodes:
        print(f"- {node['name']}")
        
except Exception as e:
    print(f"Error: {str(e)}")
