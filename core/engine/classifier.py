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

    #Company Cap
    cap_tag = classify_company_cap(snapshot.get("market_cap"))
    if cap_tag:
        tags.append(cap_tag)

    return tags