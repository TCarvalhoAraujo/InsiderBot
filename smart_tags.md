# 📊 InsiderBot Tagging System

This document explains the meaning and detection logic for each tag used to classify insider trades in the InsiderBot system.

---

## ✅ Implemented Tags

### 🧑‍💼 Insider Role Tags

| Tag                    | Meaning                                      | How to Detect                                    |
|------------------------|----------------------------------------------|--------------------------------------------------|
| 👑 CEO                 | Chief Executive Officer                      | `relationship` field includes "CEO"              |
| 💼 CFO                | Chief Financial Officer                      | `relationship` includes "CFO" or "chief financial" |
| ⚙️ COO                | Chief Operating Officer                      | `relationship` includes "COO" or "chief operating" |
| 💰 CRO                | Chief Revenue Officer                        | `relationship` includes "CRO" or "chief revenue" |
| 📈 CIO                | Chief Investment Officer                     | `relationship` includes "CIO" or "chief investment" |
| 🧠 CBO                | Chief Business Officer                       | `relationship` includes "CBO" or "chief business" |
| 🪑 Chairman           | Chairman of the Board                        | `relationship` includes "chairman"               |
| 🎖️ President          | President of the company                     | `relationship` includes "president"              |
| 🧍 EVP                | Executive Vice President                     | `relationship` includes "evp"                    |
| 📊 Portfolio Manager  | Manages portfolios                           | `relationship` includes "portfolio manager"      |
| 🔟 10% Owner           | Owns 10% or more of the company              | `relationship` includes "10% owner" or "10 percent" |
| 📋 Director           | Board Director                               | `relationship` includes "director"               |
| 🕵️ Other              | Other roles not classified above             | Fallback default if no match                     |

---

### 💸 Trade Size Tags

| Tag                    | Meaning                                      | How to Detect                                    |
|------------------------|----------------------------------------------|--------------------------------------------------|
| 🔥 VERY LARGE TRADE   | Trade represents ≥ 0.5% of company ownership | Calculated via `ownership_pct >= 0.005`         |
| 💰 LARGE TRADE        | Trade represents ≥ 0.1%                      | `ownership_pct >= 0.001`                         |
| 🟢 SMALL TRADE        | Trade represents ≥ 0.01%                     | `ownership_pct >= 0.0001`                        |
| ❓ UNKNOWN SIZE        | Ownership % unavailable                      | Ownership calc fails or snapshot missing        |

---

### 🏢 Company Size Tags

| Tag                    | Meaning                                      | How to Detect                                    |
|------------------------|----------------------------------------------|--------------------------------------------------|
| 🐣 MICRO CAP          | Market Cap < $300M                          | Based on Yahoo market cap                        |
| 🌱 SMALL CAP          | Market Cap $300M–$2B                        |                                                  |
| 🌿 MID CAP            | Market Cap $2B–$10B                         |                                                  |
| 🌳 LARGE CAP          | Market Cap $10B–$200B                       |                                                  |
| 🏔️ MEGA CAP           | Market Cap > $200B                          |                                                  |
| ❓ UNKNOWN SIZE        | Market cap unavailable                       |                                                  |

---

### ⏱️ Timing and Price Action Tags

| Tag                        | Meaning                                                    | How to Detect                                                                 |
|----------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------|
| 📉 DIP BUY                | Insider bought after a dip from recent 7-day low           | `(close - low_7d)/close ≥ ~10%`                                               |
| 🚀 BUYING INTO STRENGTH   | Price surged from recent 15-day low                        | `(close - low_15d)/low_15d ≥ ~10%`                                            |
| 📈 ABOVE CLOSE            | Trade price ≥1% above market close                         | `price >= close * 1.01`                                                       |
| 📉 BELOW CLOSE            | Trade price ≤1% below market close                         | `price <= close * 0.99`                                                       |
| 🚀 SPIKE +X% [Xd]         | Price increased by ≥5%, 10%, or 20% after 7/14/30 days     | Compare max price within [Xd] window after trade to close on trade day        |
| 📉 DIP -X% [Xd]           | Price dropped by ≥5%, 10%, or 20% after 7/14/30 days       | Compare min price within [Xd] window after trade to close on trade day        |

### 📈 Outcome Tags

| Tag                      | Meaning                                                | How to Detect                                                                  |
|--------------------------|--------------------------------------------------------|--------------------------------------------------------------------------------|
| 🟢 SUCCESSFUL TRADE      | Trade led to a strong price gain after the purchase    | `max_gain_7d`, `14d`, or `30d` ≥ 10% (with tolerance, e.g. 9%)                 |
| ⚪ NEUTRAL TRADE         | Trade gained slightly or stayed flat                   | Max gain between 0% and success threshold (e.g. < 9%)                         |
| 🔴 UNSUCCESSFUL TRADE    | Price dropped after the trade                          | All post-trade gains < 0% across 7, 14, and 30-day windows                    |

---

## 🔜 Upcoming Tags

| Tag                      | Meaning                                                        | How to Detect                                                            |
| ------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 📅 **Near Earnings**     | Trade happened shortly before earnings                         | Use snapshot cache to get `earnings_date`, compare to `transaction_date` |
| 🔁 **Cluster Buy**       | Multiple insiders bought in a short window (e.g. 3+ in 5 days) | Group by `ticker + transaction_date ± 5d`, count distinct insiders       |
| 🧠 **Smart Insider**     | High win-rate insider in the past                              | Track success rate of insiders over time, tag them if > threshold        |
| 🤯 **Unusual Buyer**     | Insider who rarely buys suddenly buys                          | If insider has <3 lifetime buys and this is a large one                  |
| 🩸 **Post-Sell-Off Buy** | Insider buys right after a big dip (e.g. -10% over 5d)         | Use OHLC to detect recent crash before trade                             |
| 🧩 **Multiple Buys**     | Same insider buys multiple times within 1–2 weeks              | Look at repeated filings for same insider                                |
| 🏭 **Sector Tag**        | Sector tag (e.g. Tech, Energy, Healthcare...)                  | Add `sector` to your company list JSON and propagate to the trade        |

---

## 🧠 Notes

- All price-based tags depend on clean OHLC data. If data is missing or stale, tag application should be skipped.
- Tags are stored as a list in each trade row and can be used to filter, score, or visualize trades.
- For performance, consider caching calculations like insider success rate or cluster patterns.

