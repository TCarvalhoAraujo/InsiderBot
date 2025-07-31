from yahooquery import Ticker
import pandas as pd
from datetime import timedelta

from core.io.cache import load_ohlc_cache, save_ohlc_cache

def update_ohlc(trades_df: pd.DataFrame):
    """
    Reads tagged trades, computes required OHLC range per ticker,
    and updates the local OHLC cache in batch.
    """
    trades_df["transaction_date"] = pd.to_datetime(trades_df["transaction_date"])
    today = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)

    # Compute smart max date: min(trade + 60d, today)
    date_ranges = trades_df.groupby("ticker")["transaction_date"].agg(["min", "max"]).reset_index()
    date_ranges["min"] = date_ranges["min"] - pd.Timedelta(days=7)
    date_ranges["max"] = date_ranges["max"] + pd.Timedelta(days=60)
    date_ranges["max"] = date_ranges["max"].apply(lambda d: min(d, today))

    tickers = date_ranges["ticker"].tolist()
    start = date_ranges["min"].min().date()
    end = date_ranges["max"].max().date()

    print(f"📅 Fetching OHLC for {len(tickers)} tickers: {start} → {end}")

    # Batch fetch OHLC
    ohlc_data = fetch_bulk_ohlc(tickers, start, end)

    # Save to cache
    for ticker, df in ohlc_data.items():
        if not df.empty:
            cached = load_ohlc_cache(ticker)
            combined = pd.concat([cached, df], ignore_index=True).drop_duplicates(subset="date")
            save_ohlc_cache(ticker, combined)

def fetch_bulk_ohlc(tickers: list[str], start_date, end_date) -> dict[str, pd.DataFrame]:
    """
    Fetches OHLC history in batch for a list of tickers.
    Returns a dict of {ticker: DataFrame}.
    """
    result = {}

    try:
        tq = Ticker(tickers)
        hist = tq.history(start=str(start_date), end=str(end_date + timedelta(days=1)), interval="1d")

        if isinstance(hist, pd.DataFrame) and not hist.empty:
            hist = hist.reset_index()

            for ticker in tickers:
                df = hist[hist["symbol"] == ticker].copy()
                if df.empty:
                    continue

                df = df[["date", "open", "high", "low", "close", "volume"]]
                df["date"] = pd.to_datetime(df["date"]).dt.date
                result[ticker] = df

    except Exception as e:
        print(f"❌ Failed bulk OHLC fetch: {e}")

    return result

def get_window_stats(ohlc: pd.DataFrame, trade_date: pd.Timestamp, insider_price: float, days_forward: int):
    """
    Returns high, low, %gain, and %drawdown for a future window if fully available.
    """
    window = ohlc[(ohlc["date"] > trade_date) & (ohlc["date"] <= trade_date + timedelta(days=days_forward))]
    
    if window.empty or window["date"].max() < (trade_date + timedelta(days=days_forward - 1)) or not insider_price:
        return None, None, None, None

    high = window["high"].max()
    low = window["low"].min()
    gain = ((high - insider_price) / insider_price) * 100
    drawdown = ((low - insider_price) / insider_price) * 100
    return high, low, gain, drawdown


def get_window_high_low(ohlc: pd.DataFrame, trade_date: pd.Timestamp, days_back: int):
    """
    Returns high and low of the N days before the trade.
    """
    window = ohlc[(ohlc["date"] >= trade_date - timedelta(days=days_back)) & (ohlc["date"] < trade_date)]
    
    if window.empty or window["date"].min() > (trade_date - timedelta(days=days_back - 1)):
        return None, None

    return window["high"].max(), window["low"].min()


def enrich_trades_with_price_deltas(df: pd.DataFrame) -> pd.DataFrame:
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    market_close_at_trade = []

    high_plus_7d = []
    low_plus_7d = []
    max_gain_7d = []
    max_drawdown_7d = []

    high_plus_14d = []
    low_plus_14d = []
    max_gain_14d = []
    max_drawdown_14d = []

    high_plus_30d = []
    low_plus_30d = []
    max_gain_30d = []
    max_drawdown_30d = []

    high_minus_7d = []
    low_minus_7d = []
    high_minus_15d = []
    low_minus_15d = []

    for _, row in df.iterrows():
        ticker = row["ticker"]
        trade_date = row["transaction_date"].date()

        ohlc = load_ohlc_cache(ticker)
        if ohlc.empty:
            # Append all None if no data
            market_close_at_trade.append(None)
            high_plus_7d.append(None);  low_plus_7d.append(None);  max_gain_7d.append(None);  max_drawdown_7d.append(None)
            high_plus_14d.append(None); low_plus_14d.append(None); max_gain_14d.append(None); max_drawdown_14d.append(None)
            high_plus_30d.append(None); low_plus_30d.append(None); max_gain_30d.append(None); max_drawdown_30d.append(None)
            high_minus_7d.append(None); low_minus_7d.append(None)
            high_minus_15d.append(None); low_minus_15d.append(None)
            continue

        ohlc["date"] = pd.to_datetime(ohlc["date"]).dt.date
        ohlc_map = ohlc.set_index("date")
        p0 = ohlc_map["close"].get(trade_date, None)
        market_close_at_trade.append(p0)

        insider_price = row["price"]

        # Future windows
        h7, l7, g7, d7 = get_window_stats(ohlc, trade_date, insider_price, 7)
        h14, l14, g14, d14 = get_window_stats(ohlc, trade_date, insider_price, 14)
        h30, l30, g30, d30 = get_window_stats(ohlc, trade_date, insider_price, 30)

        high_plus_7d.append(h7);   low_plus_7d.append(l7);   max_gain_7d.append(g7);   max_drawdown_7d.append(d7)
        high_plus_14d.append(h14); low_plus_14d.append(l14); max_gain_14d.append(g14); max_drawdown_14d.append(d14)
        high_plus_30d.append(h30); low_plus_30d.append(l30); max_gain_30d.append(g30); max_drawdown_30d.append(d30)

        # Backward windows
        h_7, l_7 = get_window_high_low(ohlc, trade_date, 7)
        h_15, l_15 = get_window_high_low(ohlc, trade_date, 15)

        high_minus_7d.append(h_7); low_minus_7d.append(l_7)
        high_minus_15d.append(h_15); low_minus_15d.append(l_15)

    df["market_close_at_trade"] = market_close_at_trade

    df["high_plus_7d"] = high_plus_7d
    df["low_plus_7d"] = low_plus_7d
    df["max_gain_7d"] = max_gain_7d
    df["max_drawdown_7d"] = max_drawdown_7d

    df["high_plus_14d"] = high_plus_14d
    df["low_plus_14d"] = low_plus_14d
    df["max_gain_14d"] = max_gain_14d
    df["max_drawdown_14d"] = max_drawdown_14d

    df["high_plus_30d"] = high_plus_30d
    df["low_plus_30d"] = low_plus_30d
    df["max_gain_30d"] = max_gain_30d
    df["max_drawdown_30d"] = max_drawdown_30d

    df["high_minus_7d"] = high_minus_7d
    df["low_minus_7d"] = low_minus_7d
    df["high_minus_15d"] = high_minus_15d
    df["low_minus_15d"] = low_minus_15d

    return df