from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

# Fetch Alpaca API credentials
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

# no keys required for news data
client = NewsClient(api_key=API_KEY, secret_key=API_SECRET )

request_params = NewsRequest(
                        symbols="TSLA",
                        start=datetime.strptime("2024-10-14", '%Y-%m-%d')
                        )

news = client.get_news(request_params)

# convert to dataframe
print(news)
