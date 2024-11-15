import os
from datetime import datetime, timedelta
import logging
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from alpaca_trade_api import REST, TimeFrame
from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
import ssl
import certifi

# Set SSL_CERT_FILE to certifi's certificate bundle
os.environ['SSL_CERT_FILE'] = certifi.where()

# Load environment variables from .env file
load_dotenv()

# Fetch Alpaca API credentials
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

# Verify that all necessary environment variables are set
required_vars = ["APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "APCA_API_BASE_URL"]
missing_vars = [var for var in required_vars if os.getenv(var) is None]
if missing_vars:
    raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")

# Configure Lumibot Alpaca credentials
ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True  # Set to False for live trading
}

# Configure logging
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    level=logging.DEBUG,  # Set to DEBUG for detailed logs; change to INFO in production
)
logger = logging.getLogger(__name__)

class EnhancedMLTrader(Strategy):
    def initialize(self, symbol: str = "SPY", risk_per_trade: float = 0.01, 
                   short_window: int = 50, long_window: int = 200, 
                   atr_period: int = 14, atr_multiplier: float = 1.5):
        """
        Initialize the trading strategy.
        
        Parameters:
        - symbol (str): The stock symbol to trade.
        - risk_per_trade (float): Fraction of portfolio to risk per trade.
        - short_window (int): Period for short-term SMA.
        - long_window (int): Period for long-term SMA.
        - atr_period (int): Number of periods to calculate ATR.
        - atr_multiplier (float): Multiplier for ATR to set stop-loss distance.
        """
        self.symbol = symbol
        self.risk_per_trade = risk_per_trade
        self.short_window = short_window
        self.long_window = long_window
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.api = REST(key_id=API_KEY, secret_key=API_SECRET, base_url=BASE_URL)
        logger.info(f"Initialized strategy for {self.symbol} with short_window={self.short_window}, "
                    f"long_window={self.long_window}, atr_period={self.atr_period}, atr_multiplier={self.atr_multiplier}")
    
    def calculate_sma(self, window: int):
        """
        Calculate Simple Moving Average (SMA) for the given window.
        
        Parameters:
        - window (int): The number of periods to calculate SMA.
        
        Returns:
        - float: The latest SMA value.
        """
        logger.debug(f"Fetching historical prices for SMA calculation with window: {window}")
        bars = self.api.get_bars(self.symbol, TimeFrame.Day, limit=window + 1).df
        sma = bars['close'].rolling(window=window).mean().iloc[-1]
        logger.debug(f"Calculated SMA({window}): {sma}")
        return sma
    
    def calculate_atr(self):
        """
        Calculate the Average True Range (ATR) for the configured period.
        
        Returns:
        - float: The latest ATR value.
        """
        logger.debug(f"Fetching historical prices for ATR calculation with period: {self.atr_period}")
        bars = self.api.get_bars(self.symbol, TimeFrame.Day, limit=self.atr_period + 1).df
        high = bars['high']
        low = bars['low']
        close = bars['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean().iloc[-1]
        logger.debug(f"Calculated ATR: {atr}")
        return atr
    
    def position_sizing(self, stop_loss_distance):
        """
        Calculate the position size based on risk per trade and stop loss distance.
        
        Parameters:
        - stop_loss_distance (float): Distance for stop loss.
        
        Returns:
        - int: Number of shares to trade.
        """
        cash = self.get_cash()
        risk_amount = cash * self.risk_per_trade
        position_size = risk_amount / stop_loss_distance
        last_price = self.get_last_price(self.symbol)
        quantity = int(position_size / last_price)
        logger.debug(f"Position sizing calculated: {quantity} shares")
        return quantity
    
    def on_trading_iteration(self):
        """
        Main trading logic executed on each trading iteration.
        """
        try:
            short_sma = self.calculate_sma(self.short_window)
            long_sma = self.calculate_sma(self.long_window)
            atr = self.calculate_atr()
            last_price = self.get_last_price(self.symbol)
            stop_loss_distance = atr * self.atr_multiplier
            quantity = self.position_sizing(stop_loss_distance)
            current_positions = self.get_positions()
    
            logger.debug(f"Short SMA: {short_sma}, Long SMA: {long_sma}, Last Price: {last_price}, "
                         f"ATR: {atr}, Stop Loss Distance: {stop_loss_distance}, Quantity: {quantity}")
    
            # Determine if a Golden Cross (buy signal) or Death Cross (sell signal) has occurred
            if short_sma > long_sma and self.symbol not in current_positions:
                # Golden Cross - Bullish Signal
                take_profit_price = last_price + (atr * 3)
                stop_loss_price = last_price - stop_loss_distance
                order = self.create_order(
                    symbol=self.symbol,
                    quantity=quantity,
                    side="buy",
                    type="limit",
                    limit_price=last_price,
                    take_profit={
                        "limit_price": take_profit_price
                    },
                    stop_loss={
                        "stop_price": stop_loss_price
                    },
                )
                self.submit_order(order)
                logger.info(f"Placed BUY order for {quantity} shares at {last_price}")
            elif short_sma < long_sma and self.symbol in current_positions:
                # Death Cross - Bearish Signal
                position = self.get_position(self.symbol)
                quantity = position.qty
                take_profit_price = last_price - (atr * 3)
                stop_loss_price = last_price + stop_loss_distance
                order = self.create_order(
                    symbol=self.symbol,
                    quantity=quantity,
                    side="sell",
                    type="limit",
                    limit_price=last_price,
                    take_profit={
                        "limit_price": take_profit_price
                    },
                    stop_loss={
                        "stop_price": stop_loss_price
                    },
                )
                self.submit_order(order)
                logger.info(f"Placed SELL order for {quantity} shares at {last_price}")
            else:
                logger.info("No trading signal detected.")
    
        except Exception as e:
            logger.error(f"Error during trading iteration: {e}")

if __name__ == "__main__":
    # Define backtesting period
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2023, 12, 31)

    # Initialize Alpaca broker with corrected credentials
    broker = Alpaca(ALPACA_CREDS)

    # Initialize the trading strategy with desired parameters
    strategy = EnhancedMLTrader(
        name="EnhancedMLStrategy",
        broker=broker,
        parameters={
            "symbol": "SPY",
            "risk_per_trade": 0.01,
            "short_window": 50,       # Short-term SMA window
            "long_window": 200,       # Long-term SMA window
            "atr_period": 14,         # ATR calculation period
            "atr_multiplier": 1.5     # ATR multiplier for stop-loss
        },
    )

    # Run backtesting with keyword arguments
    strategy.backtest(
        datasource_class=YahooDataBacktesting,
        backtesting_start=start_date,
        backtesting_end=end_date,
        parameters={
            "symbol": "SPY",
            "risk_per_trade": 0.01,
            "short_window": 50,
            "long_window": 200,
            "atr_period": 14,
            "atr_multiplier": 1.5
        },
    )

    # To run live trading, uncomment the following lines:
    # trader = Trader()
    # trader.add_strategy(strategy)
    # trader.run_all()
