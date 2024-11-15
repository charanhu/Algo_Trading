import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import time
import logging
import threading
from datetime import datetime

# ----------------------------
# Configure Logging
# ----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# PaperTrader Class
# ----------------------------
class PaperTrader:
    def __init__(self, initial_cash=100000):
        self.cash = initial_cash
        self.positions = {}  # symbol: quantity
        self.order_history = []
        self.trade_history = []
        self.portfolio_history = []
        self.lock = threading.Lock()

    def get_price(self, symbol):
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            logger.warning(f"No data retrieved for {symbol}")
            return None, None
        latest_price = data['Close'].iloc[-1]
        latest_time = data.index[-1]
        return latest_price, latest_time

    def place_order(self, symbol, quantity, side, price):
        with self.lock:
            order = {
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'price': price,
                'timestamp': datetime.now()
            }
            self.order_history.append(order)
            logger.info(f"Placed {side} order for {quantity} shares of {symbol} at {price}")
            # Simulate immediate execution
            self.execute_order(order)

    def execute_order(self, order):
        with self.lock:
            symbol = order['symbol']
            quantity = order['quantity']
            side = order['side']
            price = order['price']

            if side == 'buy':
                cost = quantity * price
                if self.cash >= cost:
                    self.cash -= cost
                    self.positions[symbol] = self.positions.get(symbol, 0) + quantity
                    logger.info(f"Executed BUY: {quantity} shares of {symbol} at {price}")
                else:
                    logger.warning("Insufficient cash to execute BUY order.")
                    return
            elif side == 'sell':
                if self.positions.get(symbol, 0) >= quantity:
                    self.cash += quantity * price
                    self.positions[symbol] -= quantity
                    if self.positions[symbol] == 0:
                        del self.positions[symbol]
                    logger.info(f"Executed SELL: {quantity} shares of {symbol} at {price}")
                else:
                    logger.warning("Insufficient shares to execute SELL order.")
                    return
            else:
                logger.error("Invalid order side.")
                return

            # Record the trade
            trade = {
                'symbol': symbol,
                'quantity': quantity,
                'side': side,
                'price': price,
                'timestamp': datetime.now()
            }
            self.trade_history.append(trade)
            self.record_portfolio()

    def record_portfolio(self):
        with self.lock:
            portfolio = {
                'cash': self.cash,
                'positions': self.positions.copy(),
                'timestamp': datetime.now()
            }
            self.portfolio_history.append(portfolio)

    def get_portfolio_value(self):
        with self.lock:
            total = self.cash
            for symbol, qty in self.positions.items():
                price, _ = self.get_price(symbol)
                if price:
                    total += qty * price
            return total

    def print_portfolio(self):
        with self.lock:
            logger.info(f"Cash: {self.cash}")
            logger.info(f"Positions: {self.positions}")
            logger.info(f"Total Portfolio Value: {self.get_portfolio_value()}")

# ----------------------------
# EnhancedMLTrader Class
# ----------------------------
class EnhancedMLTrader:
    def __init__(self, trader: PaperTrader, symbol: str = "SPY", risk_per_trade: float = 0.01, 
                 short_window: int = 50, long_window: int = 200, 
                 atr_period: int = 14, atr_multiplier: float = 1.5):
        self.trader = trader
        self.symbol = symbol
        self.risk_per_trade = risk_per_trade
        self.short_window = short_window
        self.long_window = long_window
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        logger.info(f"Initialized strategy for {self.symbol} with short_window={self.short_window}, "
                    f"long_window={self.long_window}, atr_period={self.atr_period}, atr_multiplier={self.atr_multiplier}")

    def calculate_sma(self, window: int):
        ticker = yf.Ticker(self.symbol)
        data = ticker.history(period=f"{window + 10}d", interval="1d")  # Fetch extra data to ensure SMA calculation
        if data.empty:
            logger.warning(f"No data for SMA calculation for {self.symbol}")
            return None
        sma = data['Close'].rolling(window=window).mean().iloc[-1]
        logger.debug(f"Calculated SMA({window}): {sma}")
        return sma

    def calculate_atr(self):
        ticker = yf.Ticker(self.symbol)
        data = ticker.history(period=f"{self.atr_period + 10}d", interval="1d")
        if data.empty:
            logger.warning(f"No data for ATR calculation for {self.symbol}")
            return None
        high = data['High']
        low = data['Low']
        close = data['Close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(self.atr_period).mean().iloc[-1]
        logger.debug(f"Calculated ATR: {atr}")
        return atr

    def position_sizing(self, stop_loss_distance):
        with self.trader.lock:
            cash = self.trader.cash
        risk_amount = cash * self.risk_per_trade
        position_size = risk_amount / stop_loss_distance
        price, _ = self.trader.get_price(self.symbol)
        if price:
            quantity = int(position_size / price)
            logger.debug(f"Position sizing calculated: {quantity} shares")
            return quantity
        return 0

    def on_trading_iteration(self):
        try:
            short_sma = self.calculate_sma(self.short_window)
            long_sma = self.calculate_sma(self.long_window)
            atr = self.calculate_atr()
            if short_sma is None or long_sma is None or atr is None:
                logger.warning("Insufficient data to calculate indicators.")
                return
            last_price, last_time = self.trader.get_price(self.symbol)
            if last_price is None:
                logger.warning(f"Could not retrieve last price for {self.symbol}")
                return
            stop_loss_distance = atr * self.atr_multiplier
            quantity = self.position_sizing(stop_loss_distance)
            current_positions = self.trader.positions

            logger.debug(f"Short SMA: {short_sma}, Long SMA: {long_sma}, Last Price: {last_price}, "
                         f"ATR: {atr}, Stop Loss Distance: {stop_loss_distance}, Quantity: {quantity}")

            # Golden Cross (Buy Signal)
            if short_sma > long_sma and self.symbol not in current_positions:
                take_profit_price = last_price + (atr * 3)
                stop_loss_price = last_price - stop_loss_distance
                self.trader.place_order(
                    symbol=self.symbol,
                    quantity=quantity,
                    side="buy",
                    price=last_price
                )
                logger.info(f"Placed BUY order for {quantity} shares at {last_price}")
            # Death Cross (Sell Signal)
            elif short_sma < long_sma and self.symbol in current_positions:
                position_qty = current_positions[self.symbol]
                take_profit_price = last_price - (atr * 3)
                stop_loss_price = last_price + stop_loss_distance
                self.trader.place_order(
                    symbol=self.symbol,
                    quantity=position_qty,
                    side="sell",
                    price=last_price
                )
                logger.info(f"Placed SELL order for {position_qty} shares at {last_price}")
            else:
                logger.info("No trading signal detected.")
        except Exception as e:
            logger.error(f"Error during trading iteration: {e}")

# ----------------------------
# Trading Loop Function
# ----------------------------
def trading_loop(trader: PaperTrader, strategy: EnhancedMLTrader, symbol: str, interval: int, stop_event: threading.Event):
    while not stop_event.is_set():
        strategy.on_trading_iteration()
        trader.print_portfolio()
        time.sleep(interval)

# ----------------------------
# Initialize Streamlit Session State
# ----------------------------
if 'trader' not in st.session_state:
    st.session_state.trader = PaperTrader(initial_cash=100000)
if 'strategy' not in st.session_state:
    st.session_state.strategy = EnhancedMLTrader(
        trader=st.session_state.trader,
        symbol="SPY",
        risk_per_trade=0.01,
        short_window=50,
        long_window=200,
        atr_period=14,
        atr_multiplier=1.5
    )
if 'thread' not in st.session_state:
    st.session_state.thread = None
if 'stop_event' not in st.session_state:
    st.session_state.stop_event = threading.Event()

# ----------------------------
# Streamlit UI Components
# ----------------------------
st.title("📈 Paper Trading Simulator")

# Start and Stop Buttons
col1, col2 = st.columns(2)
with col1:
    start_button = st.button("▶️ Start Trading")
with col2:
    stop_button = st.button("⏹️ Stop Trading")

# Start Trading
if start_button and st.session_state.thread is None:
    st.session_state.stop_event.clear()
    st.session_state.thread = threading.Thread(target=trading_loop, args=(
        st.session_state.trader,
        st.session_state.strategy,
        st.session_state.strategy.symbol,
        60,  # interval in seconds
        st.session_state.stop_event
    ))
    st.session_state.thread.start()
    st.success("✅ Trading simulation started.")

# Stop Trading
if stop_button and st.session_state.thread is not None:
    st.session_state.stop_event.set()
    st.session_state.thread.join()
    st.session_state.thread = None
    st.success("🛑 Trading simulation stopped.")

st.markdown("---")

# Portfolio Summary
st.header("💼 Portfolio Summary")
with st.session_state.trader.lock:
    st.write(f"**Cash:** ${st.session_state.trader.cash:,.2f}")
    st.write("**Positions:**")
    if st.session_state.trader.positions:
        positions_df = pd.DataFrame.from_dict(st.session_state.trader.positions, orient='index', columns=['Quantity'])
        st.table(positions_df)
    else:
        st.write("No positions currently held.")

# Portfolio Value Over Time
st.header("📊 Portfolio Value Over Time")
with st.session_state.trader.lock:
    portfolio_df = pd.DataFrame(st.session_state.trader.portfolio_history)
if not portfolio_df.empty:
    # Calculate Total Portfolio Value
    portfolio_df['Total Value'] = portfolio_df.apply(
        lambda row: row['cash'] + sum(
            qty * (yf.Ticker(sym).history(period="1d", interval="1m")['Close'].iloc[-1] 
                 if not yf.Ticker(sym).history(period="1d", interval="1m").empty else 0)
            for sym, qty in row['positions'].items()
        ), axis=1
    )
    fig, ax = plt.subplots()
    ax.plot(portfolio_df['timestamp'], portfolio_df['Total Value'], marker='o')
    ax.set_xlabel("Time")
    ax.set_ylabel("Total Portfolio Value ($)")
    ax.set_title("Portfolio Value Over Time")
    ax.grid(True)
    st.pyplot(fig)
else:
    st.write("No portfolio history available.")

# Trade History
st.header("📜 Trade History")
with st.session_state.trader.lock:
    trades_df = pd.DataFrame(st.session_state.trader.trade_history)
if not trades_df.empty:
    trades_df = trades_df[['timestamp', 'symbol', 'side', 'quantity', 'price']]
    trades_df = trades_df.rename(columns={
        'timestamp': 'Time',
        'symbol': 'Symbol',
        'side': 'Side',
        'quantity': 'Quantity',
        'price': 'Price ($)'
    })
    trades_df['Time'] = trades_df['Time'].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.table(trades_df)
else:
    st.write("No trades executed yet.")

# ----------------------------
# Footer
# ----------------------------
st.markdown("---")
st.write("Developed by [Your Name](https://yourwebsite.com)")

