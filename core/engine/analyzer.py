import os
import time
import random
import pandas as pd
from datetime import datetime
from yahooquery import Ticker

from core.engine.classifier import tag_trade, add_cluster_buy_tag, add_multiple_buys_tag, add_smart_insider_tag
from core.io.file_manager import FINVIZ_DATA_DIR, ensure_finviz_dir
from core.io.cache import load_snapshot_cache, save_snapshot_cache
from core.utils.utils import calculate_ownership_pct
from core.engine.ohlc import enrich_trades_with_price_deltas, update_ohlc
from config.problematic_tickers import NO_MARKET_CAP_TICKERS, IPO_TICKERS

TAGGED_FILE = "finviz_tagged.csv"

def analyze_finviz_trade() -> None:
    """Main entrypoint for analyzing Finviz insider trades and tagging them."""    
    df = load_finviz_data()
    tickers = df["ticker"].unique()

    # --- Build snapshots first ---
    snapshot_cache = load_snapshot_cache()
    snapshot_cache = fetch_missing_snapshots(tickers, snapshot_cache)
    snapshots = {t: snapshot_cache.get(t, {}) for t in tickers}

    # --- Prefilter tickers before any heavy work ---
    valid_tickers = prefilter_tickers(tickers, snapshots, min_market_cap=150_000_000)
    df = df[df["ticker"].isin(valid_tickers)].copy()

    # --- Now update OHLC only for valid tickers ---
    update_ohlc(df)

    # --- Tag and annotate only valid ones ---
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
    tickers = [t for t in tickers if t not in NO_MARKET_CAP_TICKERS]

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
    # Clean up the dataframe
    df = group_same_day_insider_trades(df)
    df = clean_dataframe(df)

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
    Fetches metadata for a list of tickers in batches, with sleep to avoid Yahoo rate limits.
    Includes market cap, sector, industry, short name, and earnings date.
    """
    batch_size = 50
    snapshots = {}

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        print(f"📦 Fetching batch {i // batch_size + 1} of {len(tickers) // batch_size + 1}")

        try:
            t = Ticker(batch)
            summary_data = t.summary_detail
            calendar_data = t.calendar_events
            profile_data = t.asset_profile

            for ticker in batch:
                try:
                    summary = summary_data.get(ticker, {})
                    calendar = calendar_data.get(ticker, {})
                    profile = profile_data.get(ticker, {})

                    # Extract earnings date
                    earnings_date = None
                    earnings_info = calendar.get("earnings", {})
                    earnings_date_raw = earnings_info.get("earningsDate", [])

                    if isinstance(earnings_date_raw, list) and earnings_date_raw:
                        first_entry = earnings_date_raw[0]

                        if isinstance(first_entry, dict) and "raw" in first_entry:
                            raw_val = first_entry["raw"]
                            earnings_date = datetime.fromtimestamp(raw_val).date()

                        elif isinstance(first_entry, str):
                            try:
                                clean_str = first_entry.replace(":S", "")
                                earnings_date = pd.to_datetime(clean_str).date()
                            except Exception:
                                print(f"⚠️ Could not parse string earnings date for {ticker}: {first_entry}")

                    snapshots[ticker] = {
                        "market_cap": summary.get("marketCap"),
                        "sector": profile.get("sector"),
                        "industry": profile.get("industry"),
                        "earnings_date": earnings_date
                    }

                except Exception as e:
                    print(f"⚠️ Error parsing ticker {ticker}: {e}")

        except Exception as e:
            print(f"❌ Error fetching batch: {e}")

        time.sleep(random.uniform(0.8, 2.5))  # Sleep between batches

    return snapshots

def group_same_day_insider_trades(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups trades made by the same insider on the same day for the same ticker and action.
    - Cleans numeric-like strings (e.g., "64,500", "$1,234.50", "(1,000)") to numbers
    - Uses weighted-average price by shares
    - Sums shares and value
    - Keeps first relationship and sec_form4 as representatives
    """
    df = df.copy()

    # Normalize date & transaction_type formatting
    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.date
    df["transaction_type"] = df["transaction_type"].astype(str).str.strip().str.title()

    # Helper to coerce strings-with-commas/currency/parentheses to numeric
    def _to_number(s: pd.Series) -> pd.Series:
        s = s.astype(str)
        # negatives like "(1,000)" -> "-1000"
        s = s.str.replace(r"\((.*)\)", r"-\1", regex=True)
        # drop anything that's not digit, dot or minus (commas, $ spaces, etc.)
        s = s.str.replace(r"[^0-9.\-]", "", regex=True)
        return pd.to_numeric(s, errors="coerce")

    # Clean numeric columns
    for col in ["price", "shares", "value"]:
        if col in df.columns:
            df[col] = _to_number(df[col])

    # If value is missing, compute it
    df["value"] = df["value"].where(df["value"].notna(), df["price"] * df["shares"])

    # Drop rows that can't be aggregated safely
    df = df.dropna(subset=["price", "shares"])

    # Group & aggregate
    grouped = (
    df.groupby(
        ["ticker", "insider_name", "transaction_date", "transaction_type"],
        as_index=False,
    )
    .apply(lambda g: pd.Series({
        "price": (g["price"] * g["shares"]).sum() / g["shares"].sum(),
        "shares": g["shares"].sum(),
        "value": g["value"].sum(min_count=1),
        "relationship": g["relationship"].iloc[0],
        "sec_form4": g["sec_form4"].iloc[0],
    }), include_groups=False)
    .reset_index(drop=True)
    )

    # Optional: enforce integer shares if you prefer
    grouped["shares"] = grouped["shares"].round().astype("Int64")

    return grouped

def clean_dataframe(df):
    """
    Remove rows from df where ticker is in IPO_TICKERS or NO_MARKET_CAP_TICKERS.
    """
    # Union of both sets
    exclude_tickers = IPO_TICKERS.union(NO_MARKET_CAP_TICKERS)

    before = len(df)
    df_cleaned = df[~df["ticker"].isin(exclude_tickers)].copy()
    after = len(df_cleaned)

    print(f"🧹 Cleaned DataFrame: removed {before - after} rows, kept {after}")
    return df_cleaned

def prefilter_tickers(tickers, snapshots, min_market_cap=150_000_000):
    """
    Filters tickers before tagging:
    - Excludes IPO_TICKERS and NO_MARKET_CAP_TICKERS
    - Excludes tickers with market cap < min_market_cap
    """
    exclude_tickers = IPO_TICKERS.union(NO_MARKET_CAP_TICKERS)

    valid = []
    dropped = []

    for t in tickers:
        cap = snapshots.get(t, {}).get("market_cap", None)

        if t in exclude_tickers:
            dropped.append((t, "excluded list"))
            continue
        if cap is None:
            dropped.append((t, "no market cap"))
            continue
        if cap < min_market_cap:
            dropped.append((t, f"market cap {cap:,} < {min_market_cap:,}"))
            continue

        valid.append(t)

    print(f"🧹 Prefilter: {len(valid)} valid tickers, {len(dropped)} dropped")
    for t, reason in dropped[:10]:  # show a preview of reasons
        print(f"   - {t}: {reason}")
    if len(dropped) > 10:
        print(f"   ... and {len(dropped) - 10} more dropped")

    return valid
