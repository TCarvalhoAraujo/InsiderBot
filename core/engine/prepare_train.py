import pandas as pd
import ast
from core.io.file_manager import load_scored_with_tags_trades

# === Explicit outcome mappings ===
mapping_case1 = {
    "🟢 SUCCESSFUL TRADE C1": 1,
    "⚪ NEUTRAL TRADE C1": 0,
    "🔴 UNSUCCESSFUL TRADE C1": 0,
}

mapping_case2 = {
    "🟢 SUCCESSFUL TRADE": 1,
    "🔴 UNSUCCESSFUL TRADE": 0,
}

# === Master tag list (WITHOUT DIP/SPIKE or insufficient data tags) ===
POSSIBLE_TAGS = [
    "👑 CEO", "💼 CFO", "⚙️ COO", "💰 CRO", "📈 CIO", "🧠 CBO", "🪑 Chairman",
    "🎖️ President", "🧍 EVP", "📊 Portfolio Manager", "🔟 10% Owner", "📋 Director",
    "🔥 VERY LARGE TRADE", "💰 LARGE TRADE", "🟢 SMALL TRADE", "❓ UNKNOWN SIZE",
    "🐣 MICRO CAP", "🌱 SMALL CAP", "🌿 MID CAP", "🌳 LARGE CAP", "🏔️ MEGA CAP",
    "📡 Tech", "🏥 Healthcare", "🛍️ Consumer Cyclical", "⚡ Energy",
    "🏗️ Industrial", "🔌 Utilities", "🏘️ Real Estate", "⚙️ Materials",
    "📞 Communication", "🧰 Other",
    "📉 DIP BUY", 
    "🧨 CAUGHT THE KNIFE [7d]", "🧨 CAUGHT THE KNIFE [14d]",
    "🚀 BUYING INTO STRENGTH", 
    # "📈 ABOVE CLOSE", "📉 BELOW CLOSE",
    # "📈 ABOVE SMA20", "📉 BELOW SMA20", "⚡️ SMA SUPPORT RECLAIMED",
    # "🔻 SMA LOST", "🔻 OVERSOLD (RSI < 30)", "🚀 OVERBOUGHT (RSI > 70)",
    # "🟡 NEUTRAL (RSI)", "💪 STRONG TREND", "📉 DIP SETUP",
    "🔁 CLUSTER BUY", "🧠 SMART INSIDER", "🧩 MULTIPLE BUYS", "📅 NEAR EARNINGS",
    "Automatic/Scheduled", "Compensation/Accounting", "Ownership Disclaimer/Indirect", "Conviction Buy"
]

def normalize_tags(val):
    """Parse stringified list, deduplicate, and return list."""
    if isinstance(val, str):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, list):
                return list(set(parsed))
            return []
        except Exception:
            return []
    elif isinstance(val, list):
        return list(set(val))
    return []

def one_hot_tags(df, tag_col, tag_list):
    """Create one-hot encoded columns for each tag in tag_list."""
    for tag in tag_list:
        df[tag] = df[tag_col].apply(lambda tags: 1 if tag in tags else 0)
    return df

def prepare_training_data(df_all: pd.DataFrame):
    """
    Prepare clean one-hot encoded training datasets for Case 1 and Case 2.
    - Deduplicates both tags & footnote_tags
    - Merges them into a single list
    - Maps outcomes to binary labels
    - Saves train_case1.csv and train_case2.csv
    """

    # --- Normalize and merge tags ---
    df_all["tags"] = df_all["tags"].apply(normalize_tags)
    df_all["footnote_tags"] = df_all["footnote_tags"].apply(normalize_tags)

    # Merge both columns
    df_all["all_tags"] = df_all.apply(lambda row: list(set(row["tags"] + row["footnote_tags"])), axis=1)

    # Map outcomes explicitly
    df_all["outcome_case1_binary"] = df_all["outcome_case_1"].map(mapping_case1)
    df_all["outcome_case2_binary"] = df_all["outcome_case_2"].map(mapping_case2)

    # === Case 1 ===
    case1_df = df_all[df_all["outcome_case1_binary"].notna()].copy()
    case1_df = one_hot_tags(case1_df, "all_tags", POSSIBLE_TAGS)
    case1_df = case1_df[POSSIBLE_TAGS + ["outcome_case1_binary"]]
    case1_df.to_csv("train_case1.csv", index=False)

    # === Case 2 ===
    case2_df = df_all[df_all["outcome_case2_binary"].notna()].copy()
    case2_df = one_hot_tags(case2_df, "all_tags", POSSIBLE_TAGS)
    case2_df = case2_df[POSSIBLE_TAGS + ["outcome_case2_binary"]]
    case2_df.to_csv("train_case2.csv", index=False)

    print("✅ Clean binary datasets saved: train_case1.csv, train_case2.csv")

if __name__ == "__main__":
    # Load trades
    df_all = load_scored_with_tags_trades()
    df_all["tags"] = df_all["tags"].apply(ast.literal_eval)

    # --- Call preparation logic ---
    prepare_training_data(df_all)
