def safe_get_text(element, subtag=None, default=None):
    try:
        if subtag:
            return element.find(subtag).text if element.find(subtag) else default
        return element.text if element else default
    except:
        return default

def clean_value(value_str):
    if not value_str or not isinstance(value_str, str):
        return 0
    return float(value_str.replace("$", "").replace(",", "").strip())

def calculate_ownership_pct(row, snapshot) -> float | None:
    trade_value = clean_value(row.get("value"))
    market_cap = snapshot.get("market_cap")

    if market_cap in [None, 0]:
        print(f"⚠️ Market cap is missing for {row['ticker']}")

    if trade_value == 0 or not market_cap:
        return None

    try:
        return round(trade_value / market_cap, 6)  # 6 decimal precision (e.g. 0.001324)
    except Exception:
        return None