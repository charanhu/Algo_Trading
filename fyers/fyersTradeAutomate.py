# fyers_algo_trader.py

from fyers_apiv3 import fyersModel
from fyers_apiv3 import fyersModel
import webbrowser
import os
import time

class FyersAlgoTrader:
    def __init__(self, client_id, secret_key, redirect_uri):
        self.client_id = client_id
        self.secret_key = secret_key
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.fyers = None
        self.token_file = 'access_token.txt'

    def generate_auth_code(self):
        # Generate the auth code URL
        session = fyersModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type='code',
            grant_type='authorization_code',
        )
        auth_code_url = session.generate_authcode()
        print("Please open the following URL in your browser and authorize the app:")
        print(auth_code_url)
        # Open the URL in the default browser
        webbrowser.open(auth_code_url)

        # The user needs to authenticate and get the auth_code from the redirected URL
        auth_code = input("Enter the auth code from the URL: ")
        return auth_code

    def generate_access_token(self, auth_code):
        # Generate the access token using the auth code
        session = accessToken.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            grant_type='authorization_code',
        )
        session.set_token(auth_code)
        response = session.generate_token()
        if response["code"] == 200:
            self.access_token = response["access_token"]
            # Save the access token to a file for future use
            with open(self.token_file, 'w') as f:
                f.write(self.access_token)
            print("Access token generated and saved.")
        else:
            print("Error generating access token:", response)

    def load_access_token(self):
        # Load access token from file if it exists
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                self.access_token = f.read()
            print("Access token loaded from file.")
        else:
            print("Access token file not found. Please generate a new one.")

    def initialize_fyers(self):
        if self.access_token is None:
            self.load_access_token()
        if self.access_token:
            self.fyers = fyersModel.FyersModel(
                client_id=self.client_id,
                token=self.access_token,
                log_path="",
                is_async=False
            )
        else:
            print("Access token is not available. Please generate an access token.")

    def place_order(self, symbol, qty, order_type, side, productType,
                    limitPrice=0, stopPrice=0, validity="DAY", disclosedQty=0,
                    offlineOrder=False, stopLoss=0, takeProfit=0, trailing_stop_loss=None, orderTag=""):
        data = {
            "symbol": symbol,
            "qty": qty,
            "type": order_type,
            "side": side,
            "productType": productType,
            "limitPrice": limitPrice,
            "stopPrice": stopPrice,
            "validity": validity,
            "disclosedQty": disclosedQty,
            "offlineOrder": offlineOrder,
            "stopLoss": stopLoss,
            "takeProfit": takeProfit,
            "trailing_stop_loss": trailing_stop_loss,
            "orderTag": orderTag
        }
        response = self.fyers.place_order(data)
        print("Place Order Response:", response)
        return response

    def modify_order(self, order_id, order_type, limitPrice, qty):
        data = {
            "id": order_id,
            "type": order_type,
            "limitPrice": limitPrice,
            "qty": qty
        }
        response = self.fyers.modify_order(data)
        print("Modify Order Response:", response)
        return response

    def cancel_order(self, order_id):
        data = {
            "id": order_id
        }
        response = self.fyers.cancel_order(data)
        print("Cancel Order Response:", response)
        return response

    def exit_position(self, position_id):
        data = {
            "id": position_id
        }
        response = self.fyers.exit_positions(data)
        print("Exit Position Response:", response)
        return response

    def get_positions(self):
        response = self.fyers.positions()
        return response

    def get_market_quote(self, symbol):
        data = {
            "symbols": symbol
        }
        response = self.fyers.quotes(data)
        return response

    def automated_trading_strategy(self, symbol, qty, target_profit_percent, stop_loss_percent, check_interval=60):
        """
        Automated trading strategy:
        - Places a market order to buy the specified symbol.
        - Sets target profit and stop loss based on the provided percentages.
        - Monitors the position and exits when target profit or stop loss is reached.
        """
        # Get the current market price
        quote = self.get_market_quote(symbol)
        if quote['s'] != 'ok':
            print("Error fetching market quote:", quote)
            return
        current_price = quote['d'][0]['v']['lp']
        print(f"Current price of {symbol}: {current_price}")

        # Calculate target and stop-loss prices
        target_price = current_price * (1 + target_profit_percent / 100)
        stop_loss_price = current_price * (1 - stop_loss_percent / 100)
        print(f"Target Price: {target_price:.2f}")
        print(f"Stop Loss Price: {stop_loss_price:.2f}")

        # Place a market order
        order_response = self.place_order(
            symbol=symbol,
            qty=qty,
            order_type=2,  # Market order
            side=1,        # Buy
            productType="INTRADAY",
            validity="DAY",
            stopLoss=stop_loss_price,
            takeProfit=target_price,
            orderTag="AutoTrade"
        )
        if order_response['s'] != 'ok':
            print("Error placing order:", order_response)
            return

        order_id = order_response.get('id')
        print(f"Order ID: {order_id}")

        # Monitor the position
        position_closed = False
        while not position_closed:
            time.sleep(check_interval)
            positions = self.get_positions()
            if positions['s'] != 'ok':
                print("Error fetching positions:", positions)
                continue

            # Find the position for the symbol
            position = next((pos for pos in positions['netPositions'] if pos['symbol'] == symbol), None)
            if position:
                pl = float(position['pl'])
                print(f"Current P&L for {symbol}: {pl:.2f}")
                # Check if target profit or stop loss is reached
                if pl >= (current_price * qty * target_profit_percent / 100):
                    print("Target profit reached. Exiting position.")
                    self.exit_position(position['positionId'])
                    position_closed = True
                elif pl <= -(current_price * qty * stop_loss_percent / 100):
                    print("Stop loss reached. Exiting position.")
                    self.exit_position(position['positionId'])
                    position_closed = True
            else:
                print("Position not found. It might have been closed.")
                position_closed = True

    # Additional methods can be added here

# Example usage
if __name__ == "__main__":
    # Replace with your actual credentials
    client_id = "Your_Client_ID"
    secret_key = "Your_Secret_Key"
    redirect_uri = "Your_Redirect_URI"

    trader = FyersAlgoTrader(client_id, secret_key, redirect_uri)

    # Load or generate access token
    trader.load_access_token()
    if trader.access_token is None or trader.access_token == '':
        # Generate auth code
        auth_code = trader.generate_auth_code()
        # Generate access token
        trader.generate_access_token(auth_code)

    # Initialize Fyers API
    trader.initialize_fyers()

    # Automated trading strategy example
    # Replace with your own parameters
    symbol = "NSE:IDEA-EQ"
    qty = 1000  # Adjust the quantity as needed
    target_profit_percent = 5  # Target profit of 5%
    stop_loss_percent = 2      # Stop loss at 2%
    check_interval = 60        # Check every 60 seconds

    trader.automated_trading_strategy(
        symbol=symbol,
        qty=qty,
        target_profit_percent=target_profit_percent,
        stop_loss_percent=stop_loss_percent,
        check_interval=check_interval
    )
