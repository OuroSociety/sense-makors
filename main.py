from api_client import FameexClient
from market_maker import MarketMaker
from config import API_KEY, API_SECRET

def main():
    # Initialize the API client
    client = FameexClient(API_KEY, API_SECRET)
    
    # Create and run the market maker
    market_maker = MarketMaker(client)
    
    try:
        market_maker.run()
    except KeyboardInterrupt:
        print("Shutting down market maker...")
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
