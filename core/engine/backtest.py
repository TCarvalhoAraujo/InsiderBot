import pandas as pd
import ast

from core.io.file_manager import load_latest_tagged_trades, save_scores

# --- Settings ---
OUTCOME_TAGS = {"🟢 SUCCESSFUL TRADE", "⚪ NEUTRAL TRADE", "🔴 UNSUCCESSFUL TRADE"}

TAG_WEIGHTS = {
    # Insider Role
    "👑 CEO": 3, "💼 CFO": 3, "🪑 Chairman": 3, "🔟 10% Owner": 2,
    "🎖️ President": 2, "📋 Director": 1, "🧍 EVP": 1,
    # Trade Size
    "🔥 VERY LARGE TRADE": 3, "💰 LARGE TRADE": 2, "🟢 SMALL TRADE": 1,
    # Company Size
    "🐣 MICRO CAP": 3, "🌱 SMALL CAP": 2, "🌿 MID CAP": 1,
    # Timing
    "🧨 CAUGHT THE KNIFE [7d]": 3, "🧨 CAUGHT THE KNIFE [14d]": 3,
    "📉 DIP BUY": 2, "📉 BELOW CLOSE": 1, "🚀 BUYING INTO STRENGTH": 1,
    # Indicators
    "⚡️ SMA SUPPORT RECLAIMED": 2, "📉 DIP SETUP": 2, "🔻 OVERSOLD (RSI < 30)": 2,
    "📈 ABOVE SMA20": 1, "💪 STRONG TREND": 1,
    # Behavioral
    "🔁 CLUSTER BUY": 3, "🧠 SMART INSIDER": 4, "🧩 MULTIPLE BUYS": 2,
}

BUCKETS = {
    "Low Conviction (0 - 4)": (0, 4),
    "Medium (5 - 8)": (5, 8),
    "High (9 - 12)": (9, 12),
    "Ultra Conviction (13+)": (13, float("inf")),
}

# --- Step 2: Filter rows with outcome tags ---
def filter_outcome_trades(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["tags"].apply(lambda tags: any(tag.strip() in OUTCOME_TAGS for tag in tags))]

# --- Step 3: Score each row based on tags ---
def score_trade(tags: list[str]) -> int:
    return sum(TAG_WEIGHTS.get(tag, 0) for tag in tags)

# --- Step 4: Bucketize score ---
def assign_bucket(score: int) -> str:
    for bucket_name, (low, high) in BUCKETS.items():
        if low <= score <= high:
            return bucket_name
    return "Uncategorized"

# --- Step 5: Run full test pipeline ---
def run_backtest_pipeline() -> None:
    df = load_latest_tagged_trades()

    df["tags"] = df["tags"].apply(ast.literal_eval)

    df = filter_outcome_trades(df)
    print(f"🔍 {len(df)} trades with outcome tags")

    df["score"] = df["tags"].apply(score_trade)
    df["bucket"] = df["score"].apply(assign_bucket)

    # Map outcome tag to single label
    def get_outcome(tags):
        for tag in tags:
            tag_clean = tag.strip()
            if tag_clean in OUTCOME_TAGS:
                return tag_clean
        return "❓ Unknown"

    df["outcome"] = df["tags"].apply(get_outcome)

    # Save cleaned file
    save_scores(df)

    # --- Show backtest results ---
    grouped = df.groupby("bucket")["outcome"].value_counts(normalize=True).unstack().fillna(0)
    print("\n📈 Backtest Success Rate by Score Bucket (%):")
    print((grouped * 100).round(1))