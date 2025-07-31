from core.utils.utils import calculate_ownership_pct

def classify_insider_role(relationship: str) -> str:
    if not relationship:
        return ""

    rel = relationship.lower().replace("&", "and")

    if "ceo" in rel or "chief executive" in rel:
        return "👑 CEO"
    elif "cfo" in rel or "chief financial" in rel:
        return "💼 CFO"
    elif "coo" in rel or "chief operating" in rel:
        return "⚙️ COO"
    elif "cro" in rel or "chief revenue" in rel:
        return "💰 CRO"
    elif "cio" in rel or "chief investment" in rel:
        return "📈 CIO"
    elif "cbo" in rel or "chief business" in rel:
        return "🧠 CBO"
    elif "chairman" in rel:
        return "🪑 Chairman"
    elif "president" in rel:
        return "🎖️ President"
    elif "evp" in rel:
        return "🧍 EVP"
    elif "portfolio manager" in rel:
        return "📊 Portfolio Manager"
    elif "10% owner" in rel or "10 percent" in rel:
        return "🔟 10% Owner"
    elif "director" in rel:
        return "📋 Director"
    else:
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

    tolerance = 0.15  # 15%
    base_threshold = 10  # 10%

    # DIP BUY
    if close is not None and low_7 is not None and close > 0:
        dip_pct = (close - low_7) / close * 100
        if dip_pct >= base_threshold * (1 - tolerance):
            tags.append("📉 DIP BUY")

    # BUYING INTO STRENGTH
    if close is not None and low_15 is not None and low_15 > 0:
        strength_pct = (close - low_15) / low_15 * 100
        if strength_pct >= base_threshold * (1 - tolerance):
            tags.append("🚀 BUYING INTO STRENGTH")

    # ABOVE CLOSE / BELOW CLOSE
    if price is not None and close is not None and close > 0:
        diff_pct = (price - close) / close * 100
        if diff_pct >= 1:
            tags.append("📈 ABOVE CLOSE")
        elif diff_pct <= -1:
            tags.append("📉 BELOW CLOSE")

    # SPIKE +X%
    for label, gain in [
        ("7d", row.get("max_gain_7d")),
        ("14d", row.get("max_gain_14d")),
        ("30d", row.get("max_gain_30d"))
    ]:
        if gain is not None:
            if gain >= 20:
                tags.append(f"🚀 SPIKE +20% [{label}]")
            elif gain >= 10:
                tags.append(f"🚀 SPIKE +10% [{label}]")
            elif gain >= 5:
                tags.append(f"🚀 SPIKE +5% [{label}]")

    # DIP -X%
    for label, drop in [
        ("7d", row.get("max_drawdown_7d")),
        ("14d", row.get("max_drawdown_14d")),
        ("30d", row.get("max_drawdown_30d"))
    ]:
        if drop is not None:
            if drop <= -20:
                tags.append(f"📉 DIP -20% [{label}]")
            elif drop <= -10:
                tags.append(f"📉 DIP -10% [{label}]")
            elif drop <= -5:
                tags.append(f"📉 DIP -5% [{label}]")

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

    # Timing Context
    timing_tags = classify_timing_tags(row)
    tags += timing_tags  

    return tags