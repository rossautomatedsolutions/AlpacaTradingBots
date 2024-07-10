import asyncio
import websockets
import json
import pandas as pd
import numpy as np
import requests
import csv
import time

# Replace 'YOUR_API_KEY' and 'YOUR_API_SECRET' with your actual Alpaca API credentials
api_key = 'ENTER API KEY'
api_secret ='ENTER API SECRET'
base_url = 'https://paper-api.alpaca.markets'

# Define the assets you want to trade with slashes
assets_to_trade = ['AVAX/USD','BTC/USD', 'GRT/USD', 'ETH/USD', 'USDT/USD', 'CRV/USD',
    'BAT/USD', 'BCH/USD', 'DOGE/USD', 'LINK/USD', 'MKR/USD', 'LTC/USD', 'UNI/USD', 'SHIB/USD',
    'AAVE/USD', 'XTZ/USD', 'SUSHI/USD', 'YFI/USD', 'DOT/USD']

# assets_to_trade = ['BTC/USD', 'LTC/USD']

# Parameters for Bollinger Bands calculation
bollinger_periods = 3  # You can adjust this as needed
std_dev_multiplier = 0.25  # You can adjust this as needed

# User-defined parameters
quantity_to_buy = .61  # Specify the quantity to buy
run_time_minutes = 90  # Specify the run time in minutes
process_interval = 1  # Process every 1 data point by default

# Dictionary to store asset data
asset_data = {}

# Dictionary to store data counters for each symbol
data_counters = {}

async def connect_to_websocket():
    async with websockets.connect('wss://stream.data.alpaca.markets/v1beta3/crypto/us') as ws:
        auth_data = {
            "action": "auth",
            "key": api_key,
            "secret": api_secret
        }
        await ws.send(json.dumps(auth_data))

        listen_message = {
            "action": "subscribe",
            "quotes": assets_to_trade,
        }
        await ws.send(json.dumps(listen_message))

        # Initialize a timestamp to track the start time
        start_time = time.time()

        # Initialize the CSV file with headers
        log_headers_to_csv('asset_data.csv')

        while time.time() - start_time < run_time_minutes * 60:  # Run for specified minutes
            try:
                message = await ws.recv()
                # print(message)
                data = json.loads(message)

                if isinstance(data, list):
                    for item in data:
                        if 'T' in item and item['T'] == 'q':  # Check if it's a quote message
                            symbol = item['S']
                            close_price = float(item['bp'])
                            timestamp = item['t']

                            if symbol not in assets_to_trade:
                                continue

                            # Create a dictionary to store asset data if it doesn't exist
                            if symbol not in asset_data:
                                asset_data[symbol] = {
                                    'close_prices': [],
                                    'upper_band': None,
                                    'middle_band': None,
                                    'lower_band': None,
                                    'signal': None,
                                    'shares_owned': 0.0
                                }
                                data_counters[symbol] = 0

                            data_counters[symbol] += 1

                            # Filter data based on process_interval
                            if not should_process_data(symbol, timestamp, process_interval):
                                continue

                            # Add the close price to the list
                            asset_data[symbol]['close_prices'].append(close_price)

                            # Keep only the last 'bollinger_periods' of close prices
                            if len(asset_data[symbol]['close_prices']) > bollinger_periods:
                                asset_data[symbol]['close_prices'].pop(0)

                            # Calculate Bollinger Bands using the close prices
                            upper_band, middle_band, lower_band = calculate_bollinger_bands(symbol, bollinger_periods, std_dev_multiplier)
                            asset_data[symbol]['upper_band'] = upper_band
                            asset_data[symbol]['middle_band'] = middle_band
                            asset_data[symbol]['lower_band'] = lower_band

                            print(f"Symbol: {symbol}, Close Price: {close_price}")
                            print(f"Upper Band: {upper_band}, Middle Band: {middle_band}, Lower Band: {lower_band}")

                            # Add Buy/Sell signals based on Bollinger Bands
                            signal = calculate_buy_sell_signal(symbol, close_price)
                            asset_data[symbol]['signal'] = signal
                            print(f"Signal: {signal}")

                            # Fetch and print the current position
                            position = fetch_current_position(symbol)
                            print(f"Current Position for {symbol}: {position} shares")

                            # Log the message to the CSV file
                            log_message_to_csv('asset_data.csv', timestamp, symbol, close_price, upper_band, middle_band, lower_band, signal)

            except Exception as e:
                print(f"Error: {e}")

# Function to determine if data should be processed based on the interval
def should_process_data(symbol, timestamp, interval):
    global data_counters
    if symbol in data_counters and data_counters[symbol] % interval == 0:
        return True
    return False


# Function to initialize the CSV file with headers
def log_headers_to_csv(filename):
    try:
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['Timestamp', 'Symbol', 'Close Price', 'Upper Band', 'Middle Band', 'Lower Band', 'Signal']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    except Exception as e:
        print(f"Error initializing CSV headers: {e}")

# Function to log messages to the CSV file
def log_message_to_csv(filename, timestamp, symbol, close_price, upper_band, middle_band, lower_band, signal):
    try:
        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['Timestamp', 'Symbol', 'Close Price', 'Upper Band', 'Middle Band', 'Lower Band', 'Signal']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writerow({
                'Timestamp': timestamp,
                'Symbol': symbol,
                'Close Price': close_price,
                'Upper Band': upper_band,
                'Middle Band': middle_band,
                'Lower Band': lower_band,
                'Signal': signal
            })
    except Exception as e:
        print(f"Error logging message to CSV: {e}")

def calculate_bollinger_bands(symbol, periods, std_dev_multiplier):
    if symbol in asset_data:
        close_prices = asset_data[symbol]['close_prices']
        if len(close_prices) >= periods:
            df = pd.DataFrame(close_prices, columns=['Close'])
            df['Rolling Mean'] = df['Close'].rolling(window=periods).mean()
            df['Upper Band'] = df['Rolling Mean'] + (df['Close'].rolling(window=periods).std() * std_dev_multiplier)
            df['Lower Band'] = df['Rolling Mean'] - (df['Close'].rolling(window=periods).std() * std_dev_multiplier)
            return df['Upper Band'].iloc[-1], df['Rolling Mean'].iloc[-1], df['Lower Band'].iloc[-1]
    return None, None, None

def calculate_buy_sell_signal(symbol, close_price):
    if symbol in asset_data:
        close_prices = asset_data[symbol]['close_prices']
        if len(close_prices) >= bollinger_periods:
            upper_band, middle_band, lower_band = calculate_bollinger_bands(symbol, bollinger_periods, std_dev_multiplier)
            current_position = fetch_current_position(symbol)

            if close_price > upper_band:
                signal = "Sell"  # Price crossed above upper band, indicating a Sell signal
            elif close_price < lower_band:
                signal = "Buy"  # Price crossed below lower band, indicating a Buy signal
            else:
                signal = "Hold"

            if signal == "Buy" and current_position == 0.0:
                print("Buy signal, no shares owned, shares purchased")
                # Buy logic here
                buy_assets(symbol, quantity_to_buy)
            elif signal == "Buy" and current_position > 0.0:
                print("Buy signal, shares owned, no additional shares purchased")
                # No additional buy logic here
            elif signal == "Sell" and current_position == 0.0:
                print("Sell signal, no shares owned, nothing sold")
                # No sell logic here
            elif signal == "Sell" and current_position > 0.0:
                print(f"Sold {current_position} {symbol} shares")
                # Sell logic here
                sell_assets(symbol, current_position)

            return signal
    return "Hold"  # No Buy/Sell signal

def fetch_current_position(symbol):
    try:
        # Remove the slash ("/") from the symbol when fetching the position
        cleaned_symbol = symbol.replace("/", "")
        response = requests.get(f'{base_url}/v2/positions/{cleaned_symbol}', headers={'APCA-API-KEY-ID': api_key, 'APCA-API-SECRET-KEY': api_secret})
        if response.status_code == 200:
            data = response.json()
            return float(data['qty'])  # Convert the quantity to a float
        else:
            return 0.0  # Treat errors as a position of 0
    except Exception as e:
        print(f"Error fetching position: {e}")
        return 0.0

def buy_assets(symbol, quantity):
    try:
        # Buy assets using Alpaca API
        cleaned_symbol = symbol.replace("/", "")
        order_data = {
            "symbol": cleaned_symbol,
            "qty": quantity,
            "side": "buy",
            "type": "market",
            "time_in_force": "gtc"
        }
        response = requests.post(f'{base_url}/v2/orders', json=order_data, headers={'APCA-API-KEY-ID': api_key, 'APCA-API-SECRET-KEY': api_secret})
        if response.status_code == 201:
            asset_data[symbol]['shares_owned'] += quantity
            print(f"Bought {quantity} {symbol} shares")
        else:
            print(f"Error buying {quantity} {symbol} shares: {response.text}")
    except Exception as e:
        print(f"Error buying {quantity} {symbol} shares: {e}")

def sell_assets(symbol, quantity):
    try:
        # Sell assets using Alpaca API
        cleaned_symbol = symbol.replace("/", "")
        order_data = {
            "symbol": cleaned_symbol,
            "qty": quantity,
            "side": "sell",
            "type": "market",
            "time_in_force": "gtc"
        }
        response = requests.post(f'{base_url}/v2/orders', json=order_data, headers={'APCA-API-KEY-ID': api_key, 'APCA-API-SECRET-KEY': api_secret})
        if response.status_code == 201:
            asset_data[symbol]['shares_owned'] -= quantity
            print(f"Sold {quantity} {symbol} shares")
        else:
            print(f"Error selling {quantity} {symbol} shares: {response.text}")
    except Exception as e:
        print(f"Error selling {quantity} {symbol} shares: {e}")

if __name__ == "__main__":
    asyncio.run(connect_to_websocket())
