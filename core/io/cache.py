import os
import json

from core.io.file_manager import FINVIZ_DATA_DIR, ensure_finviz_dir

def load_snapshot_cache():
    ensure_finviz_dir()

    cache_path = os.path.join(FINVIZ_DATA_DIR, "snapshot.json")

    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
    return {}

def save_snapshot_cache(cache: dict):
    ensure_finviz_dir()

    cache_path = os.path.join(FINVIZ_DATA_DIR, "snapshot.json")

    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"📦 Snapshot cache saved to {cache_path} ({len(cache)} tickers)")