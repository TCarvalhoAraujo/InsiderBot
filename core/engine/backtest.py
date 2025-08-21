import pandas as pd
import ast

from core.io.file_manager import load_latest_tagged_trades, save_scores

# --- Settings ---
OUTCOME_TAGS_C1 = {
    "🟢 SUCCESSFUL TRADE C1",
    "⚪ NEUTRAL TRADE C1",
    "🔴 UNSUCCESSFUL TRADE C1"
}

OUTCOME_TAGS_C2 = {
    "🟢 SPIKE BEFORE DROP - SUCCESSFUL TRADE",
    "⚪ NEUTRAL TRADE",
    "🔴 DROP BEFORE SPIKE - BAD TRADE",
    "🔴 FINAL GAIN TOO LOW - BAD TRADE"
}

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
    return df[
        df["tags"].apply(lambda tags: any(tag.strip() in OUTCOME_TAGS_C1 for tag in tags))
        | df["case_2_outcome"].isin(OUTCOME_TAGS_C2)
    ]

# --- Step 3: Score each row based on tags ---
def score_trade(tags: list[str]) -> int:
    """
    Scores a trade based on tags. If there is no size tag,
    we still score (size contributes 0) so it can fall into Low Conviction.
    """
    score = 0

    # Base tag weights
    for tag in tags:
        score += TAG_WEIGHTS.get(tag, 0)

    # Combo boosts
    for combo, bonus in COMBO_BOOSTS.items():
        if all(tag in tags for tag in combo):
            score += bonus

    return int(score)

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
#def run_backtest_pipeline() -> None:
#    df = load_latest_tagged_trades()
#
#    df["tags"] = df["tags"].apply(ast.literal_eval)
#
#    df = filter_outcome_trades(df)
#    print(f"🔍 {len(df)} trades with outcome tags")
#
#    df["score"] = df["tags"].apply(score_trade)
#    df["bucket"] = df["score"].apply(assign_bucket)
#
#    # Map outcome tag from TAGS (Case 1)
#    def get_outcome_case_1(tags):
#        for tag in tags:
#            tag_clean = tag.strip()
#            if tag_clean in OUTCOME_TAGS_C1:
#                return tag_clean
#        return None
#
#    df["outcome_case_1"] = df["tags"].apply(get_outcome_case_1)
#
#    # --- Normalize outcome from case_2_outcome column
#    def normalize_case_2_outcome(text: str) -> str | None:
#        if pd.isna(text):
#            return None
#        text = text.strip()
#
#        if text == "🟢 SPIKE BEFORE DROP - SUCCESSFUL TRADE":
#            return "🟢 SUCCESSFUL TRADE"
#        elif text in {"⚪ NEUTRAL TRADE"}:
#            return "⚪ NEUTRAL TRADE"
#        elif text in {"🔴 DROP BEFORE SPIKE - BAD TRADE", "🔴 FINAL GAIN TOO LOW - BAD TRADE"}:
#            return "🔴 UNSUCCESSFUL TRADE"
#        else:
#            return None
#
#    df["outcome_case_2"] = df["case_2_outcome"].apply(normalize_case_2_outcome)
#
#    # Save cleaned file
#    save_scores(df, "scores.csv")
#
#    # --- Backtest Case 1 ---
#    df_case1 = df[df["outcome_case_1"].notna()]
#    grouped_1 = (
#        df_case1.groupby("bucket")["outcome_case_1"]
#        .value_counts(normalize=True)
#        .unstack()
#        .fillna(0)
#    )
#
#    print("\n📈 Case 1 – Backtest Based on 30-Day Outcome Tags:")
#    print((grouped_1 * 100).round(1))
#
#    # --- Backtest Case 2 ---
#    df_case2 = df[df["outcome_case_2"].notna()]
#    grouped_2 = (
#        df_case2.groupby("bucket")["outcome_case_2"]
#        .value_counts(normalize=True)
#        .unstack()
#        .fillna(0)
#    )
#
#    print("\n⏳ Case 2 – Backtest Based on Drawdown vs Spike Timing:")
#    print((grouped_2 * 100).round(1))
#
#    filtered_df = filter_ultra_and_highest(df, "filtered_scores.csv")
#
#    save_scores(filtered_df, "filtered_scores.csv")
#
#    print(f"✅ Saved {len(filtered_df)} trades to filtered_scores.csv")
#
#    # --- Identify trades with no outcome tag
#    df_unlabeled = df[
#        df["outcome_case_1"].isna() & df["outcome_case_2"].isna()
#    ].copy()
#
#    # --- Score and bucket the unlabeled ones
#    df_unlabeled["score"] = df_unlabeled["tags"].apply(score_trade)
#    df_unlabeled["bucket"] = df_unlabeled["score"].apply(assign_bucket)    
#
#    # --- Sort by date (most recent first or oldest first)
#    df_unlabeled["transaction_date"] = pd.to_datetime(df_unlabeled["transaction_date"])
#    df_unlabeled_sorted = df_unlabeled.sort_values("transaction_date", ascending=False)  # recent first
#
#
#    save_scores(df_unlabeled_sorted, "unlabeled_scores.csv") 
#    print(f"🆕 Scored {len(df_unlabeled_sorted)} trades without outcome tags")

def run_backtest_pipeline() -> None:
    # --- Load everything
    df_all = load_latest_tagged_trades()
    df_all["tags"] = df_all["tags"].apply(ast.literal_eval)

    # --- Map outcome tags
    def get_outcome_case_1(tags):
        for tag in tags:
            tag_clean = tag.strip()
            if tag_clean in OUTCOME_TAGS_C1:
                return tag_clean
        return None

    df_all["outcome_case_1"] = df_all["tags"].apply(get_outcome_case_1)

    def normalize_case_2_outcome(text: str) -> str | None:
        if pd.isna(text):
            return None
        text = text.strip()
        if text == "🟢 SPIKE BEFORE DROP - SUCCESSFUL TRADE":
            return "🟢 SUCCESSFUL TRADE"
        elif text == "⚪ NEUTRAL TRADE":
            return "⚪ NEUTRAL TRADE"
        elif text in {"🔴 DROP BEFORE SPIKE - BAD TRADE", "🔴 FINAL GAIN TOO LOW - BAD TRADE"}:
            return "🔴 UNSUCCESSFUL TRADE"
        return None

    df_all["outcome_case_2"] = df_all["case_2_outcome"].apply(normalize_case_2_outcome)

    # --- Score and bucket ALL trades (including unlabeled)
    df_all["score"] = df_all["tags"].apply(score_trade)
    df_all["bucket"] = df_all["score"].apply(assign_bucket)

    # --- Save all scored trades
    save_scores(df_all, "scores.csv")

    # --- FILTER for backtest: trades WITH outcome
    df = filter_outcome_trades(df_all)
    print(f"🔍 {len(df)} trades with outcome tags")

    df_case1 = df[df["outcome_case_1"].notna()]
    grouped_1 = (
        df_case1.groupby("bucket")["outcome_case_1"]
        .value_counts(normalize=True)
        .unstack()
        .fillna(0)
    )
    
    print("\n📈 Case 1 – Backtest Based on 30-Day Outcome Tags:")
    print((grouped_1 * 100).round(1))
    
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
    save_scores(filtered_df, "filtered_scores.csv")
    print(f"✅ Saved {len(filtered_df)} trades to filtered_scores.csv")

    # --- Get trades WITHOUT outcome
    df_unlabeled = df_all[
        df_all["outcome_case_1"].isna() & df_all["outcome_case_2"].isna()
    ].copy()

    df_unlabeled["transaction_date"] = pd.to_datetime(df_unlabeled["transaction_date"])
    df_unlabeled_sorted = df_unlabeled.sort_values("transaction_date", ascending=False)

    save_scores(df_unlabeled_sorted, "unlabeled_scores.csv")
    print(f"🆕 Scored {len(df_unlabeled_sorted)} trades without outcome tags")