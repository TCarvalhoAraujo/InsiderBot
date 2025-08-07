import pandas as pd
import ast

from core.io.file_manager import load_latest_tagged_trades, save_scores

# --- Settings ---
OUTCOME_TAGS = {"🟢 SUCCESSFUL TRADE C1", "⚪ NEUTRAL TRADE C1", "🔴 UNSUCCESSFUL TRADE C1"}

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

    # Map outcome tag from TAGS (Case 1)
    def get_outcome_case_1(tags):
        for tag in tags:
            tag_clean = tag.strip()
            if tag_clean in OUTCOME_TAGS:
                return tag_clean
        return None

    df["outcome_case_1"] = df["tags"].apply(get_outcome_case_1)

    # Step 3: Parse outcome from CASE 2 column
    def simplify_case_2_outcome(text: str):
        if pd.isna(text):
            return None
        if "SUCCESSFUL" in text:
            return "🟢 SUCCESSFUL TRADE"
        if "NEUTRAL" in text:
            return "⚪ NEUTRAL TRADE"
        if "BAD" in text:
            return "🔴 UNSUCCESSFUL TRADE"
        return None

    df["outcome_case_2"] = df["case_2_outcome"].apply(simplify_case_2_outcome)

    # Save cleaned file
    save_scores(df)

    # --- Backtest Case 1 ---
    df_case1 = df[df["outcome_case_1"].notna()]
    grouped_1 = (
        df_case1.groupby("bucket")["outcome_case_1"]
        .value_counts(normalize=True)
        .unstack()
        .fillna(0)
    )

    print("\n📈 Case 1 – Backtest Based on 30-Day Outcome Tags:")
    print((grouped_1 * 100).round(1))

    # --- Backtest Case 2 ---
    df_case2 = df[df["outcome_case_2"].notna()]
    grouped_2 = (
        df_case2.groupby("bucket")["outcome_case_2"]
        .value_counts(normalize=True)
        .unstack()
        .fillna(0)
    )

    print("\n⏳ Case 2 – Backtest Based on Drawdown vs Spike Timing:")
    print((grouped_2 * 100).round(1))