from alpaca_trade_api.common import URL
from alpaca_trade_api.stream import Stream
import os
from dotenv import load_dotenv

load_dotenv()

# Fetch Alpaca API credentials
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")


async def trade_callback(t):
    print("trade", t)


async def quote_callback(q):
    print("quote", q)


# Initiate Class Instance
stream = Stream(data_feed="iex")  # <- replace to 'sip' if you have PRO subscription

# subscribing to event
stream.subscribe_trades(trade_callback, "AAPL")
stream.subscribe_quotes(quote_callback, "IBM")

stream.run()
