import pandas as pd
import ast
from core.io.file_manager import load_scored_with_tags_trades

# === Master tag list (same as training) ===
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

def prepare_predict_data(df_all: pd.DataFrame):
    """
    Prepare dataset for prediction (unlabeled trades only).
    - Deduplicates both tags & footnote_tags
    - Merges them into a single list
    - Keeps only rows where BOTH outcome_case_1 and outcome_case_2 are NaN
    - One-hot encodes tags
    - Saves predict.csv
    """

    # --- Normalize and merge tags ---
    df_all["tags"] = df_all["tags"].apply(normalize_tags)
    df_all["footnote_tags"] = df_all["footnote_tags"].apply(normalize_tags)

    df_all["all_tags"] = df_all.apply(lambda row: list(set(row["tags"] + row["footnote_tags"])), axis=1)

    # Keep only rows with NO outcomes at all
    predict_df = df_all[
        df_all["outcome_case_1"].isna() & df_all["outcome_case_2"].isna()
    ].copy()

    # One-hot encode tags
    predict_df = one_hot_tags(predict_df, "all_tags", POSSIBLE_TAGS)

    # Save only tag features + identifier columns
    predict_df = predict_df.rename(columns=lambda c: c.replace("[", "_").replace("]", "_"))

    output_cols = POSSIBLE_TAGS + ["ticker", "insider_name", "transaction_date", "price"]
    output_cols = [col for col in output_cols if col in predict_df.columns]  # keep only existing

    predict_df[output_cols].to_csv("predict.csv", index=False)
    print(f"✅ Prediction dataset saved: predict.csv with {len(predict_df)} rows")

if __name__ == "__main__":
    # Load trades
    df_all = load_scored_with_tags_trades()
    df_all["tags"] = df_all["tags"].apply(ast.literal_eval)

    # --- Call preparation logic ---
    prepare_predict_data(df_all)
