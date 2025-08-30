import pandas as pd
import ast
from core.io.file_manager import load_scored_trades

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
    "🔁 CLUSTER BUY", "🧠 SMART INSIDER", "🧩 MULTIPLE BUYS", "📅 NEAR EARNINGS"
]

def one_hot_tags(df, tag_col, tag_list):
    for tag in tag_list:
        df[tag] = df[tag_col].apply(lambda tags: 1 if tag in tags else 0)
    return df

def prepare_training_data(df_all: pd.DataFrame):
    # Ensure tags are lists
    df_all["tags"] = df_all["tags"].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

    # Map outcomes explicitly
    df_all["outcome_case1_binary"] = df_all["outcome_case_1"].map(mapping_case1)
    df_all["outcome_case2_binary"] = df_all["outcome_case_2"].map(mapping_case2)

    # === Case 1 ===
    case1_df = df_all[df_all["outcome_case1_binary"].notna()].copy()
    case1_df = one_hot_tags(case1_df, "tags", POSSIBLE_TAGS)
    case1_df = case1_df[POSSIBLE_TAGS + ["outcome_case1_binary"]]
    case1_df.to_csv("train_case1.csv", index=False)

    # === Case 2 ===
    case2_df = df_all[df_all["outcome_case2_binary"].notna()].copy()
    case2_df = one_hot_tags(case2_df, "tags", POSSIBLE_TAGS)
    case2_df = case2_df[POSSIBLE_TAGS + ["outcome_case2_binary"]]
    case2_df.to_csv("train_case2.csv", index=False)

    print("✅ Clean binary datasets saved: train_case1.csv, train_case2.csv")

if __name__ == "__main__":
    # Load trades
    df_all = load_scored_trades()
    df_all["tags"] = df_all["tags"].apply(ast.literal_eval)

    # --- Call preparation logic ---
    prepare_training_data(df_all)
