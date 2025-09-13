import time
import random
import pandas as pd
from datetime import datetime
from yahooquery import Ticker

def get_bulk_snapshots(tickers: list[str]) -> dict:
    """
    Fetches metadata for a list of tickers in batches from Yahoo Finance.
    Includes market cap, sector, industry, and earnings date.

    Args:
        tickers (list[str]): List of ticker symbols.

    Returns:
        dict: Snapshot data keyed by ticker.
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