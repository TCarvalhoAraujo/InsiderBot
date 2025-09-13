import pandas as pd
import numpy as np
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

    open_ = row.get("market_open_at_trade")
    close = row.get("market_close_at_trade")

    low = row.get("low_at_trade")
    high = row.get("high_at_trade")

    low_7 = row.get("low_minus_7d")
    low_15 = row.get("low_minus_15d")

    # % thresholds
    dip_threshold = 0.05  # % within the low
    strength_threshold = 0.05  # % above recent low

    # DIP BUY
    if price and low and low_7:
        near_recent_low = (price - low_7) / price * 100 <= dip_threshold
        red_candle = close < open_
        near_day_low = (price - low) / price * 100 <= dip_threshold

        if near_recent_low and red_candle and near_day_low:
            tags.append("📉 DIP BUY")

    # BUYING INTO STRENGTH
    if price and low_15 and close and open_:
        strength_pct = (price - low_15) / low_15 * 100
        green_candle = close > open_
        near_day_high = (high - price) / price * 100 <= dip_threshold

        if strength_pct >= strength_threshold and green_candle and near_day_high:
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
        20: 20 * (1 - strength_threshold),
        10: 10 * (1 - strength_threshold),
        5: 5 * (1 - strength_threshold)
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
        -20: -20 * (1 - dip_threshold),
        -10: -10 * (1 - dip_threshold),
        -5: -5 * (1 - dip_threshold)
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

# def classify_outcome_tag(row) -> str:
#     """
#     Classifies trade based on post-trade price movement.
#     - 🟢 Successful: gain >= threshold * (1 - tolerance)
#     - 🔴 Unsuccessful: drop < 0%
#     - ⚪ Neutral: flat or small gain
#     """
# 
#     threshold = 10.0
#     tolerance = 0.10
#     min_success_gain = threshold * (1 - tolerance)
# 
#     gains = {
#         "7d": row.get("max_gain_7d"),
#         "14d": row.get("max_gain_14d"),
#         "30d": row.get("max_gain_30d")
#     }
# 
#     # Check if there's at least one valid gain value
#     valid_gains = [g for g in gains.values() if g is not None and not pd.isna(g)]
# 
#     if not valid_gains:
#         return ""
# 
#     max_gain = max(valid_gains)
# 
#     if max_gain >= min_success_gain:
#         return "🟢 SUCCESSFUL TRADE"
#     elif max_gain < 0:
#         return "🔴 UNSUCCESSFUL TRADE"
#     else:
#         return "⚪ NEUTRAL TRADE"

def classify_outcome_case_1(row) -> str:
    """
    Classifies a trade based on the 'Case 1' 30-day strategy:
    - 🟢 SUCCESSFUL: if any window (7d, 14d, 30d) shows > +15%
    - ⚪ NEUTRAL: if final 30d gain is between +9% and +15%
    - 🔴 UNSUCCESSFUL: if final 30d gain < +9%
    """
    entry_price = row.get("price")

    def normalize(val):
        """Ensure val is a percentage, not raw diff."""
        if pd.isna(val) or pd.isna(entry_price) or entry_price == 0:
            return np.nan
        # If val looks like a decimal (e.g. 0.10 = 10%), convert
        if abs(val) < 1:
            return val * 100
        return val

    gain_7d = normalize(row.get("max_gain_7d"))
    gain_14d = normalize(row.get("max_gain_14d"))
    gain_30d = normalize(row.get("max_gain_30d"))
    final_gain_30d = normalize(row.get("final_gain_30d"))

    # Spike threshold
    for gain in [gain_7d, gain_14d, gain_30d]:
        if pd.notna(gain) and gain >= 10:
            return "🟢 SUCCESSFUL TRADE C1"

    if pd.isna(final_gain_30d):
        return ""

    if 3 <= final_gain_30d < 10:
        return "⚪ NEUTRAL TRADE C1"
    else:
        return "🔴 UNSUCCESSFUL TRADE C1"


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

def add_smart_insider_tag(
    df: pd.DataFrame,
    outcome_col: str = "case_2_outcome",
    min_trades: int = 5,
    min_winrate: float = 0.7
) -> pd.DataFrame:
    """
    Adds 🧠 SMART INSIDER tag to trades if the insider has a high historical success rate.
    Success is determined from the given outcome column.
    """

    df = df.copy()
    smart_insiders = set()

    # Group trades by insider
    for insider, trades in df.groupby("insider_name"):
        total = len(trades)
        if total < min_trades:
            continue

        # Count successful outcomes
        wins = trades[outcome_col].apply(lambda x: "SUCCESSFUL" in str(x)).sum()
        winrate = wins / total

        if winrate >= min_winrate:
            smart_insiders.add(insider)

    # Apply smart insider tag
    df["tags"] = df.apply(
        lambda row: row["tags"] + ["🧠 SMART INSIDER"]
        if row["insider_name"] in smart_insiders else row["tags"],
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

def classify_metric_tags(row) -> list[str]:
    tags = []
    sma_20 = row.get("sma_20_at_trade")
    rsi_14 = row.get("rsi_14_at_trade")
    price = row.get("price")
    
    sma_20_prev = row.get("sma_20_prev")
    price_prev = row.get("price_prev")

    # SIMPLE MOVING AVERAGE
    if pd.notna(sma_20) and price:
        if price > sma_20:
            tags.append("📈 ABOVE SMA20")
        elif price < sma_20:
            tags.append("📉 BELOW SMA20")
        
        if pd.notna(sma_20_prev) and pd.notna(price_prev):
            if price_prev < sma_20_prev and price > sma_20:
                tags.append("⚡️ SMA SUPPORT RECLAIMED")
            elif price_prev > sma_20_prev and price < sma_20:
                tags.append("🔻 SMA LOST")

    # RSI
    if pd.notna(rsi_14):
        if rsi_14 < 30:
            tags.append("🔻 OVERSOLD (RSI < 30)")
        elif rsi_14 > 70:
            tags.append("🚀 OVERBOUGHT (RSI > 70)")
        else:
            tags.append("🟡 NEUTRAL (RSI)")

    # CONFLUENCE TAGS
    if pd.notna(sma_20) and pd.notna(rsi_14) and price:
        if price > sma_20 and rsi_14 > 60:
            tags.append("💪 STRONG TREND")
        elif price < sma_20 and rsi_14 < 40:
            tags.append("📉 DIP SETUP")

    if pd.isna(sma_20) or pd.isna(rsi_14):
        tags.append("⚠️ INSUFFICIENT DATA FOR MA/RSI")

    return tags

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

    # Timing Context Tags
    timing_tags = classify_timing_tags(row)
    tags += timing_tags

    # Outcome Tag
    # outcome_tag = classify_outcome_tag(row)
    # if outcome_tag:
    #     tags.append(outcome_tag)

    # Near Earnings Tag
    if near_earnings_tag(row, snapshot):
        tags.append("📅 NEAR EARNINGS")

    # Metric Tags
    metric_tags = classify_metric_tags(row)
    tags += metric_tags

    case1_outcome_tag = classify_outcome_case_1(row)
    if case1_outcome_tag:
        tags.append(case1_outcome_tag)

    return tags