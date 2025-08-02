import time
import random
import pandas as pd
from yahooquery import Ticker
from datetime import timedelta
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

from core.io.cache import load_ohlc_cache, save_ohlc_cache
from config.problematic_tickers import IPO_TICKERS

us_bd = CustomBusinessDay(calendar=USFederalHolidayCalendar())

def missing_day_tolerance(date, cached_dates):
    """
    Returns True if a single missing date is surrounded by existing dates.
    Used to tolerate gaps caused by illiquid or halted stocks.
    """
    before = (pd.Timestamp(date) - 1 * us_bd).date()
    after = (pd.Timestamp(date) + 1 * us_bd).date()
    return before in cached_dates and after in cached_dates

def determine_fetch_range(trades_df: pd.DataFrame):
    """
    Determines the minimal start and end date needed for OHLC data fetch
    across all transactions, using business days and US holiday calendar.
    """
    today = pd.Timestamp.today().normalize().date() - timedelta(days=1)
    trades_df["transaction_date"] = pd.to_datetime(trades_df["transaction_date"]).dt.date

    start_dates = []
    end_dates = []

    for _, row in trades_df.iterrows():
        ticker = row["ticker"]

        if ticker in IPO_TICKERS:
            print(f"🟡 Skipping known IPO or problematic ticker: {ticker}")
            continue

        T = row["transaction_date"]

        # Smart window: [T - 10BD (15 days), T + 22BD (1 month)] 
        win_start = (pd.Timestamp(T) - 10 * us_bd).date()
        win_end = (pd.Timestamp(T) + 20 * us_bd).date()

        # Check if cached window is complete
        cached = load_ohlc_cache(ticker)
        cached_dates = set(cached["date"]) if not cached.empty else set()
        required_days = pd.date_range(start=win_start, end=win_end, freq="B").date

        for d in required_days:
            if d not in cached_dates:
                if missing_day_tolerance(d, cached_dates):
                    print(f"🟡 Skipping isolated missing day for {ticker}: {d}")
                    continue
                if d < T:
                    start_dates.append(win_start)
                elif d > T:
                    end_dates.append(win_end)
                break  # Only trigger fetch window once per row

    if not start_dates and not end_dates:
        print("✅ All OHLC windows are satisfied.")
        return None, None

    fetch_start = min(start_dates + end_dates)
    fetch_end = today

    if fetch_start > fetch_end:
        print(f"⚠️ Skipping OHLC fetch: start date {fetch_start} is after end date {fetch_end}")
        return None, None

    return fetch_start, fetch_end

def update_ohlc(trades_df: pd.DataFrame):
    """
    Reads tagged trades, determines minimal OHLC fetch range across all tickers,
    and updates the local OHLC cache using one batch call.
    """
    # Make sure transaction_date is datetime.date
    trades_df["transaction_date"] = pd.to_datetime(trades_df["transaction_date"]).dt.date

    # Get global fetch window using smart per-transaction windows
    fetch_start, fetch_end = determine_fetch_range(trades_df)

    if fetch_start is None or fetch_end is None:
        print("✅ No OHLC update needed.")
        return

    tickers = trades_df["ticker"].unique().tolist()
    print(f"📅 Fetching OHLC for {len(tickers)} tickers: {fetch_start} → {fetch_end}")

    # Batch fetch OHLC
    ohlc_data = fetch_bulk_ohlc(tickers, fetch_start, fetch_end)

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
    batch_size = 40
    result = {}

    total_batches = (len(tickers) + batch_size - 1) // batch_size

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        print(f"📊 Fetching OHLC batch {i // batch_size + 1} of {total_batches}")

        try:
            tq = Ticker(batch)
            hist = tq.history(
                start=str(start_date),
                end=str(end_date + timedelta(days=1)),
                interval="1d"
            )

            if isinstance(hist, pd.DataFrame) and not hist.empty:
                hist = hist.reset_index()

                for ticker in batch:
                    df = hist[hist["symbol"] == ticker].copy()
                    if df.empty:
                        continue

                    df = df[["date", "open", "high", "low", "close", "volume"]]

                    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")  # safely force uniform dtype
                    df["date"] = df["date"].dt.tz_localize(None)  # remove tz
                    df["date"] = df["date"].dt.date  # convert to plain date

                    result[ticker] = df

        except Exception as e:
            print(f"❌ Error fetching OHLC for batch: {e}")

        time.sleep(random.uniform(0.8, 2.5))

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

    market_open_at_trade = []
    market_close_at_trade = []
    low_at_trade = []
    high_at_trade = []

    sma_20_at_trade = []
    rsi_14_at_trade = []
    sma_20_prev = []
    price_prev = []

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
            market_close_at_trade.append(None); market_open_at_trade.append(None); low_at_trade.append(None); high_at_trade.append(None)
            sma_20_at_trade.append(None); rsi_14_at_trade.append(None); sma_20_prev.append(None); price_prev.append(None)
            high_plus_7d.append(None);  low_plus_7d.append(None);  max_gain_7d.append(None);  max_drawdown_7d.append(None)
            high_plus_14d.append(None); low_plus_14d.append(None); max_gain_14d.append(None); max_drawdown_14d.append(None)
            high_plus_30d.append(None); low_plus_30d.append(None); max_gain_30d.append(None); max_drawdown_30d.append(None)
            high_minus_7d.append(None); low_minus_7d.append(None)
            high_minus_15d.append(None); low_minus_15d.append(None)
            continue

        ohlc["date"] = pd.to_datetime(ohlc["date"]).dt.date
        ohlc_map = ohlc.set_index("date")

        # Safe access if date exists
        if trade_date in ohlc_map.index:
            row_ohlc = ohlc_map.loc[trade_date]

            # Trade day
            market_open_at_trade.append(row_ohlc.get("open"))
            market_close_at_trade.append(row_ohlc.get("close"))
            high_at_trade.append(row_ohlc.get("high"))
            low_at_trade.append(row_ohlc.get("low"))

            # Indicators on trade day
            sma_20_at_trade.append(row_ohlc.get("sma_20"))
            rsi_14_at_trade.append(row_ohlc.get("rsi_14"))

            # Previous business day
            prev_date = (trade_date - us_bd).date()
            if prev_date in ohlc_map.index:
                row_prev = ohlc_map.loc[prev_date]
                sma_20_prev.append(row_prev.get("sma_20"))
                price_prev.append(row_prev.get("close"))
            else:
                sma_20_prev.append(None)
                price_prev.append(None)
        else:
            # If trade_date not found — fill with None for all columns
            market_open_at_trade.append(None)
            market_close_at_trade.append(None)
            high_at_trade.append(None)
            low_at_trade.append(None)
            sma_20_at_trade.append(None)
            rsi_14_at_trade.append(None)
            sma_20_prev.append(None)
            price_prev.append(None)

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

    df["market_open_at_trade"] = market_open_at_trade
    df["market_close_at_trade"] = market_close_at_trade
    df["high_at_trade"] = high_at_trade
    df["low_at_trade"] = low_at_trade

    df["sma_20_at_trade"] = sma_20_at_trade
    df["rsi_14_at_trade"] = rsi_14_at_trade
    df["sma_20_prev"] = sma_20_prev
    df["price_prev"] = price_prev

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