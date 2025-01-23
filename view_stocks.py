from db_manager import DatabaseManager

def main():
    db = DatabaseManager().get_database()
    cursor = db.watchlist.find()
    print("\nStocks in watchlist:")
    print("-" * 80)
    for doc in cursor:
        print(f"{doc['symbol']:<10} {doc['name']:<50} {doc['exchange']:<10}")
    print("-" * 80)

if __name__ == "__main__":
    main()
