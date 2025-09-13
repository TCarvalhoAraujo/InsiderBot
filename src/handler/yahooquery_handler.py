from src.io.cache_manager import load_snapshot_cache, save_snapshot_cache
from src.extraction.yahooquery import get_bulk_snapshots

def build_snapshot_cache(tickers: list[str]) -> dict:
    """
    Ensures snapshot cache is up-to-date by fetching missing tickers.

    Args:
        tickers (list[str]): List of tickers that need snapshots.

    Returns:
        dict: Snapshot cache with all requested tickers.
    """
    cache = load_snapshot_cache()
    missing = [t for t in tickers if t not in cache]

    print(f"🔍 Found {len(missing)} missing tickers.")
    if missing:
        print("🌐 Fetching missing snapshots from Yahoo Finance...")
        new_data = get_bulk_snapshots(missing)
        cache.update(new_data)
        save_snapshot_cache(cache)

    return cache