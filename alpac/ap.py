import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

from alpaca_trade_api.rest import REST, TimeFrame
api = REST()

# Fetch Apple data from last 100 days
APPLE_DATA=api.get_bars("AAPL", TimeFrame.Hour, "2024-09-14", "2024-10-14").df

# Reformat data (drop multiindex, rename columns, reset index)
APPLE_DATA.columns = APPLE_DATA.columns.to_flat_index()
APPLE_DATA.columns = [x[1] for x in APPLE_DATA.columns]
APPLE_DATA.reset_index(inplace=True)
print(APPLE_DATA.head())

# Plot stock price data
plot = APPLE_DATA.plot(x="timestamp", y="p", legend=False)
plot.set_xlabel("Date")
plot.set_ylabel("Apple Close Price ($)")
plt.show()
