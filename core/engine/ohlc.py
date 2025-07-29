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