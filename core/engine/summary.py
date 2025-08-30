import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

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

import pandas as pd

def analyze_cluster(df: pd.DataFrame, ticker: str, trade_date: pd.Timestamp, window: int = 7) -> str:
    """
    Analyze insider buy clusters for a given ticker and trade date.

    Parameters
    ----------
    df : pd.DataFrame
        Must include ['ticker','transaction_date','price','insider_name','relationship'].
    ticker : str
        Ticker symbol to analyze.
    trade_date : pd.Timestamp
        Date of the insider trade to analyze.
    window : int
        Days before/after to consider part of the same cluster (default=7).

    Returns
    -------
    str
        Markdown-formatted cluster analysis.
    """
    trade_date = pd.to_datetime(trade_date).normalize()  # ensure Timestamp

    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.normalize()

    # Select trades in ±window days
    cluster = df[
        (df["ticker"] == ticker) &
        (df["transaction_date"].between(
            trade_date - pd.Timedelta(days=window),
            trade_date + pd.Timedelta(days=window)
        ))
    ].copy()

    if cluster.empty or cluster["insider_name"].nunique() < 3:
        return "No cluster detected (isolated or <3 unique insiders)."

    # Sort chronologically
    cluster = cluster.sort_values("transaction_date")

    # Cluster size & duration
    cluster_size = len(cluster)
    duration = (cluster["transaction_date"].max() - cluster["transaction_date"].min()).days

    # Position of this trade
    cluster.reset_index(drop=True, inplace=True)
    pos_idx = cluster.index[cluster["transaction_date"] == trade_date].tolist()
    position_str = f"{pos_idx[0] + 1} of {cluster_size}" if pos_idx else "Unknown"

    # Detect cluster signal
    prices = cluster["price"].tolist()
    if all(prices[i] > prices[i+1] for i in range(len(prices)-1)):
        signal = "📉 Averaging Down Cluster"
    elif all(prices[i] < prices[i+1] for i in range(len(prices)-1)):
        signal = "🚀 Chasing Up Cluster"
    else:
        signal = "⚖️ Mixed Cluster"

    # Average price comparison
    avg_price = cluster["price"].mean()
    this_price = cluster.loc[pos_idx[0], "price"] if pos_idx else None
    if this_price:
        diff_pct = (this_price - avg_price) / avg_price * 100
        avg_cmp = f"{diff_pct:+.1f}% vs cluster avg (${avg_price:.2f})"
    else:
        avg_cmp = "N/A"

    # Roles summary
    roles_summary = ", ".join(cluster["relationship"].unique())

    # Progression table
    progression_lines = []
    for _, row in cluster.iterrows():
        progression_lines.append(
            f"- {row['transaction_date'].date()} ({row['insider_name']} – {row['relationship']}) → ${row['price']:.2f}"
        )

    progression_md = "\n".join(progression_lines)

    # Build Markdown output
    md = f"""
## 👥 Cluster Analysis
- Cluster Size: {cluster_size} trades
- This Buy: {position_str}
- Cluster Duration: {duration} days
- Cluster Signal: {signal}
- Price vs Avg: {avg_cmp}
- Unique Insiders: {cluster['insider_name'].nunique()}
- Roles Involved: {roles_summary}

**Progression:**
{progression_md}
"""
    return md

def analyze_sec_form(df: pd.DataFrame, ticker: str, trade_date: pd.Timestamp) -> str:
    """
    Fetches the SEC filing for a given ticker & trade_date,
    extracts footnotes (either XML <footnote> tags or 'Explanation of Responses'),
    and returns a Markdown summary.
    """
    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.normalize()
    trade_date = pd.to_datetime(trade_date).normalize()

    row = df[(df["ticker"] == ticker) & (df["transaction_date"] == trade_date)]
    if row.empty:
        return f"❌ No filing found for {ticker} on {trade_date.date()}"

    filing_url = row.iloc[0]["sec_form4"]

    # Clean and normalize URL
    if "finviz.com/" in filing_url:
        filing_url = filing_url.split("finviz.com/")[-1]
    filing_url = filing_url.replace("http://", "https://")

    try:
        resp = requests.get(
            filing_url,
            headers={"User-Agent": "InsiderBot - CaseStudy (thicoaraujo1@gmail.com)",
                     "Accept-Encoding": "gzip, deflate",
                     "Host": "www.sec.gov"})
        resp.raise_for_status()
    except Exception as e:
        return f"❌ Error fetching SEC filing: {e}"

    soup = BeautifulSoup(resp.text, "lxml")

    # --- Step 1: Try XML <footnote> tags first ---
    footnotes = [fn.get_text(strip=True) for fn in soup.find_all("footnote")]

    # --- Step 2: If none found, look for "Explanation of Responses:" ---
    if not footnotes:
        text = soup.get_text("\n")
        match = re.search(
            r"Explanation of Responses:(.*?)(Remarks:|\*\* Signature of Reporting Person|Reminder:|$)",
            text,
            re.S
        )

        footnotes = []
        if match:
            block = match.group(1).strip()

            # ✅ Capture only numbered footnotes ("1. ...", "2. ...", etc.)
            numbered = re.findall(r"(\d+\..*?)(?=\n\d+\.|\Z)", block, re.S)
            footnotes = [fn.strip().replace("\n", " ") for fn in numbered]


    # --- Step 3: Detect signals ---
    tags, notes = [], []
    for fn in footnotes:
        if "dividend reinvestment" in fn.lower():
            tags.append("📥 DRIP")
            notes.append("Includes shares from Dividend Reinvestment Plan (automatic, weaker signal).")
        if "disclaims beneficial ownership" in fn.lower():
            tags.append("⚖️ DISCLAIMER")
            notes.append("Insider disclaims beneficial ownership → indirect/limited financial interest.")

    if not tags:
        tags.append("✅ No special footnotes")
        notes.append("No DRIP or disclaimer language detected in this filing.")

    # --- Step 4: Build Markdown ---
    md = f"""
# 📑 SEC Filing Footnote Analysis – {ticker}

**Date:** {trade_date.date()}  
**Filing URL:** [{filing_url}]({filing_url})

---

## 📝 Detected Footnotes
{"".join([f"- {fn}\n" for fn in footnotes]) if footnotes else "None found."}

---

## 🧩 Tags
{", ".join(tags)}

---

## ⚖️ Notes
{"".join([f"- {n}\n" for n in notes])}
    """.strip()

    return md

def generate_trade_md(
    ticker: str,
    insider_price: float,
    current_price: float,
    num_stocks: int,
    date: str,
    sma20: float,
    rsi14: float,
    df: pd.DataFrame,
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

    # --- Cluster Section
    cluster_md = analyze_cluster(df, ticker, pd.to_datetime(date))

    # --- Sec Form Setion
    sec_form = analyze_sec_form(df, ticker, pd.to_datetime(date))

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

{cluster_md}

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

{sec_form}

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