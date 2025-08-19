import pandas as pd
import ast

from core.io.file_manager import load_latest_tagged_trades, save_scores, save_scores_filtered

# --- Settings ---
OUTCOME_TAGS = {"🟢 SUCCESSFUL TRADE C1", "⚪ NEUTRAL TRADE C1", "🔴 UNSUCCESSFUL TRADE C1"}

VALID_SIZE_TAGS = {"🔥 VERY LARGE TRADE", "💰 LARGE TRADE", "🟢 SMALL TRADE"}

TAG_WEIGHTS = {
    # Insider Role
    "👑 CEO": 3, "💼 CFO": 3, 
    "⚙️ COO": 2, "💰 CRO": 2, "🪑 Chairman": 2, "🔟 10% Owner": 2,
    "🎖️ President": 1, "📋 Director": 1, "🧍 EVP": 1,
    # Trade Size
    "🔥 VERY LARGE TRADE": 3, "💰 LARGE TRADE": 2, "🟢 SMALL TRADE": 1,
    # Company Size
    "🐣 MICRO CAP": 2, "🌱 SMALL CAP": 3, "🌿 MID CAP": 1, 
    # Timing
    "🧨 CAUGHT THE KNIFE [7d]": 1, "🧨 CAUGHT THE KNIFE [14d]": 2,
    # Indicators
    "⚡️ SMA SUPPORT RECLAIMED": 2, "📉 DIP SETUP": 2, "🔻 OVERSOLD (RSI < 30)": 2,
    "📈 ABOVE SMA20": 1, "💪 STRONG TREND": 1,
    # Behavioral
    "🔁 CLUSTER BUY": 4, "🧠 SMART INSIDER": 3, "🧩 MULTIPLE BUYS": 2,
    # Industry
    "📡 Tech": 2, "🏥 Healthcare": 3,  "🏦 Financial": 2, "🛍️ Consumer Cyclical": 1, "⚡ Energy": 1, "📞 Communication": 1,
}

BUCKETS = {
    "Low Conviction (0 - 4)": (0, 4),
    "Medium (5 - 7)": (5, 7),
    "High (8 - 11)": (8, 11),
    "Ultra Conviction (12 - 14)": (12, 14),
    "Highest Conviction (15+)": (15, float("inf")),
}

COMBO_BOOSTS = {
    ("🔥 VERY LARGE TRADE", "🏥 Healthcare"): 2,
    ("💰 LARGE TRADE", "🏥 Healthcare"): 1,
    ("📈 CIO", "🏦 Financial"): 2,

}

# --- Step 2: Filter rows with outcome tags ---
def filter_outcome_trades(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["tags"].apply(lambda tags: any(tag.strip() in OUTCOME_TAGS for tag in tags))]

# --- Step 3: Score each row based on tags ---
def score_trade(tags: list[str]) -> int | None:
    """
    Scores a trade based on tags, but only if it has a valid trade size.
    Returns None if the trade should be ignored.
    """
    # ✅ Filter out trades without size
    if not any(tag in tags for tag in VALID_SIZE_TAGS):
        return None  # trade ignored
    
    score = 0
    
    # Base tag weights
    for tag in tags:
        score += TAG_WEIGHTS.get(tag, 0)

    # Combo boosts
    for combo, bonus in COMBO_BOOSTS.items():
        if all(tag in tags for tag in combo):
            score += bonus

    return score

# --- Step 4: Bucketize score ---
def assign_bucket(score: int) -> str:
    for bucket_name, (low, high) in BUCKETS.items():
        if low <= score <= high:
            return bucket_name
    return "Uncategorized"

def filter_ultra_and_highest(df: pd.DataFrame, output_file: str) -> pd.DataFrame:
    """
    Filters only Ultra Conviction and Highest Conviction trades
    and saves them to a new CSV file.

    Args:
        df (pd.DataFrame): DataFrame with a 'bucket' column
        output_file (str): Path to save the filtered CSV

    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    keep_buckets = {"Ultra Conviction (12 - 14)", "Highest Conviction (15+)"}
    filtered = df[df["bucket"].isin(keep_buckets)].copy()
    filtered.to_csv(output_file, index=False)
    return filtered

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

    filtered_df = filter_ultra_and_highest(df, "filtered_scores.csv")

    save_scores_filtered(filtered_df)

    print(f"✅ Saved {len(filtered_df)} trades to filtered_scores.csv")