import pandas as pd
from datetime import timedelta
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
from core.utils.utils import calculate_ownership_pct

us_bd = CustomBusinessDay(calendar=USFederalHolidayCalendar())

def classify_insider_role(relationship: str) -> str:
    """
    Maps relationship string to an insider role tag with emoji.
    """
    if not relationship:
        return ""

    rel = relationship.lower().replace("&", "and")

    role_map = [
        (["ceo", "chief executive"], "👑 CEO"),
        (["cfo", "chief financial"], "💼 CFO"),
        (["coo", "chief operating"], "⚙️ COO"),
        (["cro", "chief revenue"], "💰 CRO"),
        (["cio", "chief investment"], "📈 CIO"),
        (["cbo", "chief business"], "🧠 CBO"),
        (["chairman"], "🪑 Chairman"),
        (["president"], "🎖️ President"),
        (["evp"], "🧍 EVP"),
        (["portfolio manager"], "📊 Portfolio Manager"),
        (["10% owner", "10 percent"], "🔟 10% Owner"),
        (["director"], "📋 Director"),
    ]

    for keywords, tag in role_map:
        if any(keyword in rel for keyword in keywords):
            return tag

    return "🕵️ Other"

def classify_company_cap(market_cap: float) -> str:
    if market_cap is None:
        return "❓ UNKNOWN SIZE"
    if market_cap < 300_000_000:
        return "🐣 MICRO CAP"
    elif market_cap < 2_000_000_000:
        return "🌱 SMALL CAP"
    elif market_cap < 10_000_000_000:
        return "🌿 MID CAP"
    elif market_cap < 200_000_000_000:
        return "🌳 LARGE CAP"
    else:
        return "🏔️ MEGA CAP"

def classify_sector_tag(sector: str | None) -> str:
    """
    Converts sector string into a tag with emoji.
    """
    if not sector:
        return ""

    sector_map = {
        "Technology": "📡 Tech",
        "Healthcare": "🏥 Healthcare",
        "Financial Services": "🏦 Financial",
        "Consumer Cyclical": "🛍️ Consumer Cyclical",
        "Consumer Defensive": "🥫 Consumer Defensive",
        "Energy": "⚡ Energy",
        "Utilities": "🔌 Utilities",
        "Industrials": "🏗️ Industrial",
        "Real Estate": "🏘️ Real Estate",
        "Basic Materials": "⚙️ Materials",
        "Communication Services": "📞 Communication",
    }

    return sector_map.get(sector, f"🧰 {sector}")

def classify_trade_size(row, snapshot) -> str:
    ownership_pct = calculate_ownership_pct(row, snapshot)

    if ownership_pct is None:
        return "❓ UNKNOWN SIZE"

    if ownership_pct >= 0.005:     # 0.5%
        return "🔥 VERY LARGE TRADE"
    elif ownership_pct >= 0.001:   # 0.1%
        return "💰 LARGE TRADE"
    elif ownership_pct >= 0.0001:  # 0.01%
        return "🟢 SMALL TRADE"
    else:
        return "—"

def classify_timing_tags(row) -> list[str]:
    """
    Applies timing-related tags based on market context and price movement.
    Requires the row to have enriched OHLC-based columns.
    """
    tags = []

    price = row.get("price")
    close = row.get("market_close_at_trade")

    low_7 = row.get("low_minus_7d")
    low_15 = row.get("low_minus_15d")

    # Thresholds and tolerance
    tolerance = 0.15
    base_threshold = 10.0

    dip_required = base_threshold * (1 - tolerance)
    strength_required = base_threshold * (1 - tolerance)

    # DIP BUY
    if close and low_7 and close > 0:
        dip_pct = (close - low_7) / close * 100
        if dip_pct >= dip_required:
            tags.append("📉 DIP BUY")

    # BUYING INTO STRENGTH
    if close and low_15 and low_15 > 0:
        strength_pct = (close - low_15) / low_15 * 100
        if strength_pct >= strength_required:
            tags.append("🚀 BUYING INTO STRENGTH")

    # CAUGHT THE KNIFE
    if price and low_7 and price < low_7:
        tags.append("🧨 CAUGHT THE KNIFE [7d]")
    elif price and low_15 and price < low_15:
        tags.append("🧨 CAUGHT THE KNIFE [14d]")

    # ABOVE / BELOW CLOSE
    if price and close and close > 0:
        diff_pct = (price - close) / close * 100
        if diff_pct >= 1:
            tags.append("📈 ABOVE CLOSE")
        elif diff_pct <= -1:
            tags.append("📉 BELOW CLOSE")

    # SPIKE +X% [tolerant thresholds]
    spike_thresholds = {
        20: 20 * (1 - tolerance),
        10: 10 * (1 - tolerance),
        5: 5 * (1 - tolerance)
    }

    for label, gain in [
        ("7d", row.get("max_gain_7d")),
        ("14d", row.get("max_gain_14d")),
        ("30d", row.get("max_gain_30d"))
    ]:
        if gain is not None:
            if gain >= spike_thresholds[20]:
                tags.append(f"🚀 SPIKE +20% [{label}]")
            elif gain >= spike_thresholds[10]:
                tags.append(f"🚀 SPIKE +10% [{label}]")
            elif gain >= spike_thresholds[5]:
                tags.append(f"🚀 SPIKE +5% [{label}]")

    # DIP -X% [tolerant thresholds]
    dip_thresholds = {
        -20: -20 * (1 - tolerance),
        -10: -10 * (1 - tolerance),
        -5: -5 * (1 - tolerance)
    }

    for label, drop in [
        ("7d", row.get("max_drawdown_7d")),
        ("14d", row.get("max_drawdown_14d")),
        ("30d", row.get("max_drawdown_30d"))
    ]:
        if drop is not None:
            if drop <= dip_thresholds[-20]:
                tags.append(f"📉 DIP -20% [{label}]")
            elif drop <= dip_thresholds[-10]:
                tags.append(f"📉 DIP -10% [{label}]")
            elif drop <= dip_thresholds[-5]:
                tags.append(f"📉 DIP -5% [{label}]")

    return tags

def classify_outcome_tag(row) -> str:
    """
    Classifies trade based on post-trade price movement.
    - 🟢 Successful: gain >= threshold * (1 - tolerance)
    - 🔴 Unsuccessful: drop < 0%
    - ⚪ Neutral: flat or small gain
    """

    threshold = 10.0
    tolerance = 0.10
    min_success_gain = threshold * (1 - tolerance)

    gains = {
        "7d": row.get("max_gain_7d"),
        "14d": row.get("max_gain_14d"),
        "30d": row.get("max_gain_30d")
    }

    # Check if there's at least one valid gain value
    valid_gains = [g for g in gains.values() if g is not None and not pd.isna(g)]

    if not valid_gains:
        return ""

    max_gain = max(valid_gains)

    if max_gain >= min_success_gain:
        return "🟢 SUCCESSFUL TRADE"
    elif max_gain < 0:
        return "🔴 UNSUCCESSFUL TRADE"
    else:
        return "⚪ NEUTRAL TRADE"

def add_cluster_buy_tag(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    for idx, row in df.iterrows():
        ticker = row["ticker"]
        txn_date = row["transaction_date"]
        window_start = txn_date - 5 * us_bd
        window_end = txn_date + 5 * us_bd

        ticker_window = df[
            (df["ticker"] == ticker) &
            (df["transaction_date"] >= window_start) &
            (df["transaction_date"] <= window_end)
        ]

        if ticker_window["insider_name"].nunique() >= 3:
            df.at[idx, "tags"] = row["tags"] + ["🔁 CLUSTER BUY"]

    return df

def add_multiple_buys_tag(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds '🧩 MULTIPLE BUYS' tag only if:
    - Insider made 2+ trades in same stock within ±10 business days
    - At least one of those trades is SMALL or bigger
    """
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    for idx, row in df.iterrows():
        insider = row["insider_name"]
        ticker = row["ticker"]
        txn_date = row["transaction_date"]

        window_start = txn_date - 5 * us_bd
        window_end = txn_date + 5 * us_bd

        # All trades by this insider in this window
        insider_trades = df[
            (df["ticker"] == ticker) &
            (df["insider_name"] == insider) &
            (df["transaction_date"] >= window_start) &
            (df["transaction_date"] <= window_end)
        ]

        if len(insider_trades) >= 2:
            # Check if at least one trade is tagged with a valid size
            has_meaningful_buy = insider_trades["tags"].apply(
                lambda tags: any(tag in tags for tag in ["🟢 SMALL TRADE", "💰 LARGE TRADE", "🔥 VERY LARGE TRADE"])
            ).any()

            if has_meaningful_buy:
                df.at[idx, "tags"] = row["tags"] + ["🧩 MULTIPLE BUYS"]

    return df

def add_smart_insider_tag(df: pd.DataFrame, min_trades: int = 5, min_winrate: float = 0.6) -> pd.DataFrame:
    """
    Adds 🧠 SMART INSIDER tag to trades if the insider has a high historical success rate.
    """
    df = df.copy()

    # Pre-group by insider
    grouped = df.groupby("insider_name")

    # Track smart insiders
    smart_insiders = set()

    for insider, trades in grouped:
        total = len(trades)
        if total < min_trades:
            continue

        wins = trades["tags"].apply(lambda tags: "🟢 SUCCESSFUL TRADE" in tags).sum()
        winrate = wins / total

        if winrate >= min_winrate:
            smart_insiders.add(insider)

    # Apply tag
    df["tags"] = df.apply(
        lambda row: row["tags"] + ["🧠 SMART INSIDER"] if row["insider_name"] in smart_insiders else row["tags"],
        axis=1
    )

    return df

def near_earnings_tag(row, snapshot: dict, window: int = 14) -> bool:
    """
    Returns True if the trade happened within `window` days before the earnings date.
    """
    txn_date = pd.to_datetime(row["transaction_date"]).date()
    earnings_date = snapshot.get("earnings_date")

    if earnings_date is None:
        return False

    if isinstance(earnings_date, str):
        try:
            earnings_date = pd.to_datetime(earnings_date).date()
        except Exception:
            return False

    delta = (earnings_date - txn_date).days
    return 0 < delta <= window

def tag_trade(row, snapshot):
    tags = []

    # Insider Check
    relationship = str(row["relationship"]).strip().lower()
    role_tag = classify_insider_role(relationship)
    if role_tag:
        tags.append(role_tag)

    # Trade Size
    trade_size_tag = classify_trade_size(row, snapshot)
    if trade_size_tag not in ["—", "Unknown"]:
        tags.append(trade_size_tag)

    # Company Cap
    cap_tag = classify_company_cap(snapshot.get("market_cap"))
    if cap_tag:
        tags.append(cap_tag)

    # Sector Tag
    sector_tag = classify_sector_tag(snapshot.get("sector"))
    if sector_tag:
        tags.append(sector_tag)

    # Timing Context
    timing_tags = classify_timing_tags(row)
    tags += timing_tags

    # Outcome Tag
    outcome_tag = classify_outcome_tag(row)
    if outcome_tag:
        tags.append(outcome_tag)

    # Near Earnings Tag
    if near_earnings_tag(row, snapshot):
        tags.append("📅 NEAR EARNINGS")

    return tags