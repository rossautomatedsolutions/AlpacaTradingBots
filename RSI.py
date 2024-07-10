import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests

# API credentials
api_key = 'YOUR_API_KEY'
api_secret = 'YOUR_API_SECRET'
base_url = 'https://paper-api.alpaca.markets'

def calculate_rsi(data, periods, close_column):
    df = pd.DataFrame(data)
    try:
        price_diff = df[close_column].diff(1)
        gain = price_diff.where(price_diff > 0, 0)
        loss = -price_diff.where(price_diff < 0, 0)

        avg_gain = gain.rolling(window=periods).mean()
        avg_loss = loss.rolling(window=periods).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        df['RSI'] = rsi
    except KeyError as e:
        print(f"Error: {e}")
        print(f"Close column '{close_column}' not found in data.")
        return None

    return df['RSI']

def calculate_buy_sell_signal_rsi(data, periods, thresholds, close_column='Adj Close'):
    data['RSI'] = calculate_rsi(data, periods, close_column)
    signals = pd.DataFrame(index=data.index)
    signals['Signal'] = 'HOLD'
    signals.loc[data['RSI'] > thresholds['overbought_threshold'], 'Signal'] = 'SELL'
    signals.loc[data['RSI'] < thresholds['oversold_threshold'], 'Signal'] = 'BUY'

    return signals, data['RSI'], periods

def connect_to_yfinance(assets, interval, lookback_days=60):
    historical_data = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    for symbol in assets:
        data = yf.download(symbol, interval=interval, start=start_date, end=end_date)
        historical_data[symbol] = data

    return historical_data

def fetch_current_position(symbol):
    try:
        response = requests.get(f'{base_url}/v2/positions/{symbol}', headers={'APCA-API-KEY-ID': api_key, 'APCA-API-SECRET-KEY': api_secret})
        if response.status_code == 200:
            data = response.json()
            return float(data['qty'])
        else:
            return 0.0
    except Exception as e:
        print(f"Error fetching position: {e}")
        return 0.0

def buy_assets(symbol, quantity):
    try:
        order_data = {
            "symbol": symbol,
            "qty": quantity,
            "side": "buy",
            "type": "market",
            "time_in_force": "gtc"
        }
        response = requests.post(f'{base_url}/v2/orders', json=order_data, headers={'APCA-API-KEY-ID': api_key, 'APCA-API-SECRET-KEY': api_secret})
        if response.status_code == 201:
            print(f"Bought {quantity} {symbol} shares")
        else:
            print(f"Error buying {quantity} {symbol} shares: {response.text}")
    except Exception as e:
        print(f"Error buying {quantity} {symbol} shares: {e}")

def sell_assets(symbol, quantity):
    try:
        order_data = {
            "symbol": symbol,
            "qty": quantity,
            "side": "sell",
            "type": "market",
            "time_in_force": "gtc"
        }
        response = requests.post(f'{base_url}/v2/orders', json=order_data, headers={'APCA-API-KEY-ID': api_key, 'APCA-API-SECRET-KEY': api_secret})
        if response.status_code == 201:
            print(f"Sold {quantity} {symbol} shares")
        else:
            print(f"Error selling {quantity} {symbol} shares: {response.text}")
    except Exception as e:
        print(f"Error selling {quantity} {symbol} shares: {e}")

def main():
    assets_to_trade = ['AAPL', 'GOOGL']
    interval = '1h'
    lookback_days = 60
    rsi_periods = 14
    overbought_threshold = 70
    oversold_threshold = 30
    quantity_to_buy = 5

    thresholds = {
        'overbought_threshold': overbought_threshold,
        'oversold_threshold': oversold_threshold
    }

    historical_data = connect_to_yfinance(assets_to_trade, interval, lookback_days)

    for symbol in assets_to_trade:
        data = historical_data[symbol]
        signals, rsi_values, periods = calculate_buy_sell_signal_rsi(data, rsi_periods, thresholds)

        current_position = fetch_current_position(symbol)
        last_signal = signals['Signal'].iloc[-1]

        print(f"Symbol: {symbol}, Current Position: {current_position}, Last Signal: {last_signal}")

        if last_signal == 'BUY' and current_position == 0:
            buy_assets(symbol, quantity_to_buy)
        elif last_signal == 'SELL' and current_position > 0:
            sell_assets(symbol, current_position)

if __name__ == "__main__":
    main()
