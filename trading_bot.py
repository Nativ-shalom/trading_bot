import alpaca_trade_api as tradeapi
import pandas as pd
import numpy as np
import ta
import time
from datetime import datetime, timedelta
import pytz

# Replace these with your Alpaca API credentials
API_KEY = 'PKMY8FBOKCLF71Y07R4I'
SECRET_KEY = 'IBHctfgtD2HtTlJyT8EzLVhlAihKnwDmsDls6isT'
BASE_URL = 'https://paper-api.alpaca.markets'

# Initialize the Alpaca API
api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

# Define the trading parameters
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
end_date = datetime.now(pytz.UTC) + timedelta(days=730)  # Run for 2 years

# Fixed amount per stock
amount_per_stock = 100000 / 7  # Approximately $14,285.71

def get_historical_data(symbol):
    # Fetch historical data for the symbol
    end = datetime.now(pytz.UTC)
    start = end - timedelta(days=60)
    barset = api.get_bars(
        symbol,
        tradeapi.TimeFrame.Day,
        start.isoformat(),
        end.isoformat(),
        adjustment='raw'
    )
    data = barset.df
    data = data[data['symbol'] == symbol].reset_index()
    return data

def calculate_indicators(data):
    data['SMA20'] = data['close'].rolling(window=20).mean()
    data['RSI'] = ta.momentum.RSIIndicator(data['close'], window=14).rsi()
    return data

def check_buy_sell_signals(symbol):
    data = get_historical_data(symbol)
    data = calculate_indicators(data)

    if len(data) < 20:
        print(f"Not enough data to calculate indicators for {symbol}.")
        return

    latest_price = data['close'].iloc[-1]
    sma20 = data['SMA20'].iloc[-1]
    rsi = data['RSI'].iloc[-1]

    position = None
    try:
        position = api.get_position(symbol)
    except tradeapi.rest.APIError as e:
        if 'position does not exist' in str(e):
            position = None
        else:
            print(f"Error getting position for {symbol}: {e}")
            return

    # Calculate quantity to buy based on fixed amount
    qty = int(amount_per_stock // latest_price)

    # Ensure you have enough cash
    cash = float(api.get_account().cash)
    required_cash = qty * latest_price

    # Buy condition
    if (latest_price > sma20 * 1.03) and (rsi < 70) and (position is None):
        if required_cash <= cash and qty > 0:
            try:
                api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='day'
                )
                print(f"Bought {qty} shares of {symbol} at ${latest_price:.2f}")
            except Exception as e:
                print(f"Error buying {symbol}: {e}")
        else:
            print(f"Not enough cash to buy {symbol} or quantity is zero.")
    # Sell condition
    elif (latest_price < sma20 * 0.97) and (position is not None):
        try:
            api.submit_order(
                symbol=symbol,
                qty=position.qty,
                side='sell',
                type='market',
                time_in_force='day'
            )
            print(f"Sold {position.qty} shares of {symbol} at ${latest_price:.2f}")
        except Exception as e:
            print(f"Error selling {symbol}: {e}")
    else:
        print(f"No action for {symbol}.")

def run_trading_bot():
    while datetime.now(pytz.UTC) < end_date:
        clock = api.get_clock()
        if clock.is_open:
            print(f"Market is open. Checking signals at {datetime.now(pytz.UTC)}")
            for symbol in symbols:
                check_buy_sell_signals(symbol)
            # Sleep until the next trading day
            next_close = clock.next_close
            time_to_close = next_close - datetime.now(pytz.UTC)
            time.sleep(time_to_close.total_seconds() + 60)  # Extra buffer
        else:
            # Sleep until the market opens
            next_open = clock.next_open
            time_to_open = next_open - datetime.now(pytz.UTC)
            time.sleep(time_to_open.total_seconds() + 60)  # Extra buffer

if __name__ == "__main__":
    run_trading_bot()
