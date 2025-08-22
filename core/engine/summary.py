import datetime

def generate_trade_md(
    ticker: str,
    insider_price: float,
    current_price: float,
    num_stocks: int,
    date: str,
    sma9: float,
    rsi14: float,
    tags: list[str] = None,
    news: list[str] = None,
    tax_rate: float = 0.30,
    filename: str = None
):
    """
    Generate a Markdown trade signal overview.
    """

    # % change from insider buy
    pct_change = ((current_price - insider_price) / insider_price) * 100

    # Targets
    targets = {
        15: insider_price * 1.15,
        17: insider_price * 1.17,
        20: insider_price * 1.20,
    }

    # Stop loss (-10%)
    stop_loss = insider_price * 0.90

    # Per stock gains/losses
    gains_after_tax = {}
    for pct, target in targets.items():
        gross_gain = (target - current_price) * num_stocks
        net_gain = gross_gain * (1 - tax_rate)
        gains_after_tax[pct] = (target, net_gain)

    loss_10 = (current_price - stop_loss) * num_stocks

    # RRR (using +17% vs -10%)
    potential_gain = (targets[17] - current_price) * num_stocks
    potential_loss = loss_10
    rrr = potential_gain / potential_loss if potential_loss > 0 else "∞"

    # Markdown output
    md = f"""
# 📝 Trade Signal Overview – {ticker.upper()}

**Date:** {date}

---

## 📊 Core Info
- **Insider Buy Price:** ${insider_price:.2f}
- **Current Price:** ${current_price:.2f} (**{pct_change:+.2f}%**)
- **Position Size:** {num_stocks} shares (${current_price * num_stocks:.2f})

---

## 🎯 Targets & Risk

**Upside Potential (after {int(tax_rate*100)}% tax):**
- +15% → ${gains_after_tax[15][0]:.2f} → Gain: **${gains_after_tax[15][1]:.2f}**
- +17% → ${gains_after_tax[17][0]:.2f} → Gain: **${gains_after_tax[17][1]:.2f}**
- +20% → ${gains_after_tax[20][0]:.2f} → Gain: **${gains_after_tax[20][1]:.2f}**

**Downside Risk:**
- -10% → ${stop_loss:.2f} → Loss: **${loss_10:.2f}**

**Risk-to-Reward Ratio (RRR):** ~**{rrr:.2f}**

---

## 📈 Technicals
- **SMA 9 (daily):** ${sma9:.2f}
- **RSI 14 (daily):** {rsi14:.2f}

---

## 🧩 Tags (from Insider Bot)
{tags if tags else "None"}

---

## 📢 News
{chr(10).join(f"- {n}" for n in news)} if news else "None"

---

## ⚖️ Summary
- **Signal Strength:** (to be filled manually)
- **Notes:** (add your notes here)

---
"""

    # Save to file
    if not filename:
        filename = f"trade_{ticker.lower()}_{date}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md)

    return filename
