import datetime

def calculate_rrr(targets: dict, entry_price: float, stop_price: float, num_stocks: int) -> dict:
    """
    Calculate Risk-to-Reward ratios for given targets.

    Args:
        targets (dict): mapping of {percent: target_price}.
        entry_price (float): price at which entry is made (insider or trader).
        stop_price (float): stop-loss price (based on insider).
        num_stocks (int): number of shares.

    Returns:
        dict: {percent: RRR} for each target.
    """
    rr_ratios = {}
    risk = (entry_price - stop_price) * num_stocks

    if risk <= 0:
        return {pct: float("inf") for pct in targets}  # if no risk, all RRR = ∞

    for pct, tgt in targets.items():
        reward = (tgt - entry_price) * num_stocks
        rr_ratios[pct] = reward / risk if reward > 0 else 0

    return rr_ratios


def generate_trade_md(
    ticker: str,
    insider_price: float,
    current_price: float,
    num_stocks: int,
    date: str,
    sma20: float,
    rsi14: float,
    tags: list[str] = None,
    news: list[str] = None,
    tax_rate: float = 0.30,
    filename: str = None
):
    """
    Generate a Markdown trade signal overview with both Insider and Trader setups.
    """

    # --- Insider Section ---
    pct_change_insider = ((current_price - insider_price) / insider_price) * 100

    targets = {15: insider_price * 1.15,
               17: insider_price * 1.17,
               20: insider_price * 1.20}
    stop_target = insider_price * 0.90

    insider_gains = {}
    for pct, tgt in targets.items():
        gross = (tgt - insider_price) * num_stocks
        net = gross * (1 - tax_rate)
        insider_gains[pct] = (tgt, net)

    insider_loss = (insider_price - stop_target) * num_stocks
    insider_rrr_dict = calculate_rrr(targets, insider_price, stop_target, num_stocks)

    # --- Trader Section (uses insider targets/stops, not % from trader entry) ---
    trader_gains = {}
    for pct, tgt in targets.items():
        gross = (tgt - current_price) * num_stocks
        net = gross * (1 - tax_rate)
        trader_gains[pct] = (tgt, net)

    trader_loss = (current_price - stop_target) * num_stocks
    trader_rrr_dict = calculate_rrr(targets, current_price, stop_target, num_stocks)

    # --- Markdown Output ---
    md = f"""
# 📝 Trade Signal Overview – {ticker.upper()}

**Date:** {date}

---

## 👤 Insider Setup
- **Buy Price:** ${insider_price:.2f}
- **Current Price:** ${current_price:.2f} (**{pct_change_insider:+.2f}% vs insider entry**)
- **Position Size:** {num_stocks} shares (${insider_price * num_stocks:.2f})

**Upside Potential (after {int(tax_rate*100)}% tax):**
- +15% → ${insider_gains[15][0]:.2f} → Gain: **${insider_gains[15][1]:.2f}**
- +17% → ${insider_gains[17][0]:.2f} → Gain: **${insider_gains[17][1]:.2f}**
- +20% → ${insider_gains[20][0]:.2f} → Gain: **${insider_gains[20][1]:.2f}**

**Downside Risk:**
- -10% → ${stop_target:.2f} → Loss: **${insider_loss:.2f}**

**Risk-to-Reward Ratio (RRR):**
- +15%: ~**{insider_rrr_dict[15]:.2f}**
- +17%: ~**{insider_rrr_dict[17]:.2f}**
- +20%: ~**{insider_rrr_dict[20]:.2f}**

---

## 💸 Trader Setup
- **Entry Price:** ${current_price:.2f}
- **Position Size:** {num_stocks} shares (${current_price * num_stocks:.2f})

**Upside Potential (after {int(tax_rate*100)}% tax):**
- +15% → ${trader_gains[15][0]:.2f} → Gain: **${trader_gains[15][1]:.2f}**
- +17% → ${trader_gains[17][0]:.2f} → Gain: **${trader_gains[17][1]:.2f}**
- +20% → ${trader_gains[20][0]:.2f} → Gain: **${trader_gains[20][1]:.2f}**

**Downside Risk:**
- -10% → ${stop_target:.2f} → Loss: **${trader_loss:.2f}**

**Risk-to-Reward Ratio (RRR):**
- +15%: ~**{trader_rrr_dict[15]:.2f}**
- +17%: ~**{trader_rrr_dict[17]:.2f}**
- +20%: ~**{trader_rrr_dict[20]:.2f}**

---

## 📈 Technicals
- **SMA 20 (daily):** ${sma20:.2f}
- **RSI 14 (daily):** {rsi14:.2f}

---

## 🧩 Tags (from Insider Bot)
{tags if tags else "None"}

---

## 📢 News
{chr(10).join(f"- {n}" for n in news) if news else "None"}

---

## ⚖️ Summary
- **Signal Strength (Insider):** (fill manually)
- **Signal Strength (Trader):** (fill manually)
- **Notes:** (add your notes here)

---
"""

    # Save to file
    if not filename:
        filename = f"trade_{ticker.lower()}_{date}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md)

    return filename