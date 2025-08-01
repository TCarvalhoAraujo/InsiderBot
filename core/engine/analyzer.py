import os
import pandas as pd
from yahooquery import Ticker

from core.engine.classifier import tag_trade, add_cluster_buy_tag, add_multiple_buys_tag, add_smart_insider_tag
from core.io.file_manager import FINVIZ_DATA_DIR, ensure_finviz_dir
from core.io.cache import load_snapshot_cache, save_snapshot_cache
from core.utils.utils import calculate_ownership_pct
from core.engine.ohlc import enrich_trades_with_price_deltas, update_ohlc

TAGGED_FILE = "finviz_tagged.csv"

def analyze_finviz_trade() -> None:
    """Main entrypoint for analyzing Finviz insider trades and tagging them."""    
    df = load_finviz_data()
    tickers = df["ticker"].unique()
    
    update_ohlc(df)

    snapshot_cache = load_snapshot_cache()
    snapshot_cache = fetch_missing_snapshots(tickers, snapshot_cache)

    snapshots = {t: snapshot_cache.get(t, {}) for t in tickers}
    df = tag_and_annotate(df, snapshots)

    tagged_path = os.path.join(FINVIZ_DATA_DIR, TAGGED_FILE)
    df.to_csv(tagged_path, index=False)
    print(f"✅ Tagged trades saved to {tagged_path}")

def load_finviz_data() -> pd.DataFrame:
    """Loads the full Finviz trades CSV file from disk."""
    ensure_finviz_dir()
    file_path = os.path.join(FINVIZ_DATA_DIR, "finviz_all_trades.csv")
    df = pd.read_csv(file_path)
    print(f"\n📊 Analyzing {len(df)} insider trades...\n")
    return df

def fetch_missing_snapshots(tickers: list[str], cache: dict) -> dict:
    """
    Checks which tickers are missing from the snapshot cache,
    fetches their data using YahooQuery, and updates the cache.
    """
    missing = [t for t in tickers if t not in cache]
    print(f"🔍 Found {len(missing)} missing tickers.")

    if not missing:
        return cache

    print("🌐 Fetching missing snapshots from Yahoo Finance...")
    new_data = get_bulk_snapshots(missing)
    cache.update(new_data)
    save_snapshot_cache(cache)
    return cache

def tag_and_annotate(df: pd.DataFrame, snapshots: dict) -> pd.DataFrame:
    """
    Applies trade tags and ownership percentage to each row in the DataFrame
    using the snapshot data for each ticker.
    """
    # Add additional info to dataframe
    df = enrich_trades_with_price_deltas(df)
    df["ownership_pct"] = df.apply(lambda row: calculate_ownership_pct(row, snapshots.get(row["ticker"], {})), axis=1)

    # Apply simple tags
    df["tags"] = df.apply(lambda row: tag_trade(row, snapshots.get(row["ticker"], {})), axis=1)

    # Post-processing multi-trade tags
    df = add_cluster_buy_tag(df)
    df = add_multiple_buys_tag(df)
    df = add_smart_insider_tag(df, min_trades=5, min_winrate=0.7)
    
    return df

def get_bulk_snapshots(tickers: list[str]) -> dict:
    """
    Fetches key metadata for a list of tickers using YahooQuery in bulk.
    Returns a dictionary of snapshot data per ticker.
    """
    snapshots = {}

    try:
        t = Ticker(tickers)
        summary_data = t.summary_detail
        quote_data = t.quote_type

        for ticker in tickers:
            summary = summary_data.get(ticker, {})
            quote = quote_data.get(ticker, {})

            snapshots[ticker] = {
                "market_cap": summary.get("marketCap"),
                "sector": quote.get("sector"),
                "industry": quote.get("industry"),
                "short_name": quote.get("shortName"),
            }

    except Exception as e:
        print(f"❌ Bulk snapshot fetch failed: {e}")

    return snapshots