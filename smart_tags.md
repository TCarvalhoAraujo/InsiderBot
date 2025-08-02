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

### 🏭 Sector Tags

| Tag Example              | Meaning                        | Detection (from snapshot)         |
|--------------------------|--------------------------------|-----------------------------------|
| 📡 **Tech**              | Technology sector              | `snapshot["sector"] == Technology` |
| 🏥 **Healthcare**        | Healthcare sector              | ... and so on                    |
| 🛍️ **Consumer Cyclical** | Discretionary spending sector |                                   |
| ⚡ **Energy**             | Oil, gas, renewables          |                                   |
| 🏗️ **Industrial**         | Manufacturing, services       |                                   |
| 🔌 **Utilities**          | Power, water, gas providers   |                                   |
| 🏘️ **Real Estate**        | REITs, property companies     |                                   |
| ⚙️ **Materials**          | Chemicals, mining             |                                   |
| 📞 **Communication**      | Media, telecom                |                                   |
| 🧰 **Other**              | Any unknown or unmatched tag  | Fallback                         |

---

### ⏱️ Timing and Price Action Tags

| Tag                        | Meaning                                                    | How to Detect                                                                 |
|----------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------|
| 📉 DIP BUY                | Insider bought after a dip from recent 7-day low           | `(close - low_7d)/close ≥ ~10%`                                               |
| 🧨 CAUGHT THE KNIFE [Xd]  | Insider bought **below** lowest price in last 7 or 14 days | `price < low_7d` or `price < low_14d`                                         |
| 🚀 BUYING INTO STRENGTH   | Price surged from recent 15-day low                        | `(close - low_15d)/low_15d ≥ ~10%`                                            |
| 📈 ABOVE CLOSE            | Trade price ≥1% above market close                         | `price >= close * 1.01`                                                       |
| 📉 BELOW CLOSE            | Trade price ≤1% below market close                         | `price <= close * 0.99`                                                       |
| 🚀 SPIKE +X% [Xd]         | Price increased by ≥5%, 10%, or 20% after 7/14/30 days     | Compare max price within [Xd] window after trade to close on trade day        |
| 📉 DIP -X% [Xd]           | Price dropped by ≥5%, 10%, or 20% after 7/14/30 days       | Compare min price within [Xd] window after trade to close on trade day        |

---

### 📊 Indicator-Based Tags

| Tag                             | Meaning                                                | How to Detect                                        |
| ------------------------------- | ------------------------------------------------------ | ---------------------------------------------------- |
| 📈 ABOVE SMA20                  | Price on trade day was above the 20-day moving average | `price > sma_20`                                     |
| 📉 BELOW SMA20                  | Price was under the 20-day moving average              | `price < sma_20`                                     |
| ⚡️ SMA SUPPORT RECLAIMED        | Price crossed **above** SMA20 after being below it     | `price_prev < sma_20_prev` and `price > sma_20`      |
| 🔻 SMA LOST                     | Price crossed **below** SMA20 after being above it     | `price_prev > sma_20_prev` and `price < sma_20`      |
| 🔻 OVERSOLD (RSI < 30)          | RSI indicates stock may be oversold                    | `rsi_14 < 30`                                        |
| 🚀 OVERBOUGHT (RSI > 70)        | RSI indicates stock may be overbought                  | `rsi_14 > 70`                                        |
| 🟡 NEUTRAL (RSI)                | RSI is between 30 and 70 (neutral zone)                | `30 ≤ rsi_14 ≤ 70`                                   |
| 💪 STRONG TREND                 | Price above SMA20 **and** RSI above 60                 | `price > sma_20` and `rsi_14 > 60`                   |
| 📉 DIP SETUP                    | Price below SMA20 **and** RSI below 40                 | `price < sma_20` and `rsi_14 < 40`                   |
| ⚠️ INSUFFICIENT DATA FOR MA/RSI | Indicators not available due to limited price history  | One or more of `sma_20` or `rsi_14` is missing (NaN) |

---

### 🧠 Behavioral Tags

| Tag                          | Meaning                                                        | Detection Logic                                                                 |
|------------------------------|----------------------------------------------------------------|----------------------------------------------------------------------------------|
| 🔁 **CLUSTER BUY**           | 3+ insiders bought within 5 business days                     | Group trades by ticker ± 5bd window and count unique insiders                   |
| 🧠 **SMART INSIDER**         | Insider has >70% win rate historically                        | Analyze past trades with outcome tags                                           |                                  |
| 🧩 **MULTIPLE BUYS**         | Insider bought multiple times within 14 business days         | Group by insider name + ticker ± 7bd, must include at least one small+ trade   |

---

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
| 🤯 **Unusual Buyer**     | Insider who rarely buys suddenly buys                          | If insider has <3 lifetime buys and this is a large one                  |

---

## 🧠 Notes

- All price-based tags depend on clean OHLC data. If data is missing or stale, tag application should be skipped.
- Tags are stored as a list in each trade row and can be used to filter, score, or visualize trades.
- For performance, consider caching calculations like insider success rate or cluster patterns.

