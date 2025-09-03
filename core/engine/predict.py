# core/engine/predict.py
import pandas as pd
import joblib
import os

MODELS_DIR = "models"

def load_models():
    return {
        "logreg_case1": joblib.load(os.path.join(MODELS_DIR, "logreg_case1.pkl")),
        "logreg_case2": joblib.load(os.path.join(MODELS_DIR, "logreg_case2.pkl")),
        "rf_case1": joblib.load(os.path.join(MODELS_DIR, "rf_case1.pkl")),
        "rf_case2": joblib.load(os.path.join(MODELS_DIR, "rf_case2.pkl")),
        "xgb_case1": joblib.load(os.path.join(MODELS_DIR, "xgb_case1.pkl")),
        "xgb_case2": joblib.load(os.path.join(MODELS_DIR, "xgb_case2.pkl")),
    }

def sanitize_column(col: str) -> str:
    return col.replace("[", "_").replace("]", "_")

def predict_unlabeled(file_path: str, models: dict):
    df = pd.read_csv(file_path)

    # Drop non-feature columns
    non_feature_cols = ["ticker", "insider_name", "transaction_date", "price"]

    # --- Sanitize feature names ---
    df = df.rename(columns=sanitize_column)

    feature_cols = [c for c in df.columns if c not in non_feature_cols]
    X = df[feature_cols].astype(float)  # force numeric

    # 🔑 Force feature alignment with training set
    expected_features = models["xgb_case1"].get_booster().feature_names
    X = X.reindex(columns=expected_features, fill_value=0)

    # --- Case 1 XGB ---
    preds1 = models["xgb_case1"].predict_proba(X)[:, 1]
    df["case1_pred_XGB"] = preds1

    # --- Case 2 XGB ---
    preds2 = models["xgb_case2"].predict_proba(X)[:, 1]
    df["case2_pred_XGB"] = preds2

    # Re-attach identifiers if available
    # if identifiers is not None:
    #    df = pd.concat([identifiers, df], axis=1)

    return df

if __name__ == "__main__":
    models = load_models()
    df_all = predict_unlabeled("predict.csv", models)

    # --- Sort everything by transaction_date ---
    if "transaction_date" in df_all.columns:
        df_all = df_all.sort_values("transaction_date", ascending=False)

    print("\n=== 🔮 Top Predictions (Case 1) ===")
    top_case1 = df_all.sort_values("case1_pred_XGB", ascending=False).head(10)
    print(top_case1[["transaction_date", "ticker", "insider_name", "case1_pred_XGB", "case2_pred_XGB"]])

    print("\n=== 🔮 Top Predictions (Case 2) ===")
    top_case2 = df_all.sort_values("case2_pred_XGB", ascending=False).head(10)
    print(top_case2[["transaction_date", "ticker", "insider_name", "case1_pred_XGB", "case2_pred_XGB"]])

    # Save predictions
    df_all.to_csv("predicted_trades_new.csv", index=False)
    print("\n✅ Predictions saved to predicted_trades_new.csv")

