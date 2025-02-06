import os
from dotenv import load_dotenv
from decimal import Decimal

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = "https://openapi.fameex.net"  # Updated to match API docs
API_KEY = os.getenv("FAMEEX_API_KEY")
API_SECRET = os.getenv("FAMEEX_API_SECRET")

# Trading Configuration
SYMBOL = "SZARUSDT"  # Changed to uppercase as per API docs
ORDER_BOOK_DEPTH = 5
SPREAD_PERCENTAGE = Decimal("0.02")  # 2% spread
MIN_ORDER_SIZE = Decimal("100")  # Minimum order size
MAX_ORDER_SIZE = Decimal("1000")  # Maximum order size

# Rate Limiting
ORDER_RATE_LIMIT = 100  # 100 times per 2 seconds
ORDER_BOOK_RATE_LIMIT = 20  # 20 times per 2 seconds

# Add Kaspa configuration
KASPA_NODE_URL = os.getenv("KASPA_NODE_URL", "http://localhost:16110")
KASPA_PRIVATE_KEY = os.getenv("KASPA_PRIVATE_KEY")
KASPA_ADDRESS = os.getenv("KASPA_ADDRESS")

# Add minimum balances
MIN_KAS_RESERVE = Decimal("1.0")
MIN_ORDER_VALUE = Decimal("10.0")  # Minimum order value in USDC 