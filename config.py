import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = "https://api.fameex.com"
API_KEY = os.getenv("FAMEEX_API_KEY")
API_SECRET = os.getenv("FAMEEX_API_SECRET")

# Trading Configuration
SYMBOL = "KAS-USDT"  # Replace with actual trading pair
ORDER_BOOK_DEPTH = 5
SPREAD_PERCENTAGE = 0.02  # 2% spread
MIN_ORDER_SIZE = 100  # Minimum order size
MAX_ORDER_SIZE = 1000  # Maximum order size

# Rate Limiting
ORDER_RATE_LIMIT = 100  # 100 times per 2 seconds
ORDER_BOOK_RATE_LIMIT = 20  # 20 times per 2 seconds 