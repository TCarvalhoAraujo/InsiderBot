import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt
import seaborn as sns
from xgboost import XGBClassifier
import re

def sanitize_column(col: str) -> str:
    # Replace problematic characters with underscores
    return re.sub(r'[\[\]<>]', '_', col)

def train_logreg(path: str, target_col: str):
    print(f"\n🔎 Training Logistic Regression on {path} ...")
    
    # Load dataset
    df = pd.read_csv(path)
    X = df.drop(columns=[target_col])
    y = df[target_col]

    # Debug: show class distribution
    print("🔎 Class distribution:", y.value_counts().to_dict())

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Logistic Regression
    model = LogisticRegression(max_iter=500, solver="liblinear")
    model.fit(X_train, y_train)

    # Eval
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, digits=3))

    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"📊 Cross-val Accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Feature importance
    coefs = pd.Series(model.coef_[0], index=X.columns).sort_values(ascending=False)
    coefs = coefs.rename(lambda s: s.encode("ascii", "ignore").decode().strip())

    # 🔎 Print top 10 positive/negative signals
    print("\n📈 Top 10 bullish tags:")
    print(coefs.head(10))
    print("\n📉 Top 10 bearish tags:")
    print(coefs.tail(10))

    # Plot
    plt.figure(figsize=(8, 10))
    sns.barplot(x=coefs.values, y=coefs.index, palette="coolwarm", legend=False)
    plt.title(f"Feature Importance (Logistic Regression) – {path}")
    plt.xlabel("Coefficient (log-odds impact)")
    plt.axvline(0, color="black", linestyle="--")
    plt.tight_layout()
    plt.show()

    return model


def train_random_forest(path: str, target_col: str):
    print(f"\n🌲 Training Random Forest on {path} ...")

    df = pd.read_csv(path)
    X = df.drop(columns=[target_col])
    y = df[target_col]

    print("🔎 Class distribution:", y.value_counts().to_dict())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Random Forest
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        random_state=42,
        class_weight="balanced"  # handle imbalances better
    )
    model.fit(X_train, y_train)

    # Eval
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, digits=3))

    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"📊 Cross-val Accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Feature importances
    importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    importances = importances.rename(lambda s: s.encode("ascii", "ignore").decode().strip())

    print("\n🌟 Top 10 important tags (Random Forest):")
    print(importances.head(10))

    plt.figure(figsize=(8, 10))
    sns.barplot(x=importances.values, y=importances.index, palette="viridis", legend=False)
    plt.title(f"Feature Importance (Random Forest) – {path}")
    plt.xlabel("Importance (Gini)")
    plt.tight_layout()
    plt.show()

    return model

def train_xgboost(path: str, target_col: str):
    print(f"\n⚡ Training XGBoost on {path} ...")

    df = pd.read_csv(path)
    X = df.drop(columns=[target_col])
    y = df[target_col]

    print("🔎 Class distribution:", y.value_counts().to_dict())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # anitize after split
    X_train = X_train.rename(columns=sanitize_column)
    X_test = X_test.rename(columns=sanitize_column)
    X = X.rename(columns=sanitize_column)  
    
    # XGBoost model
    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
        use_label_encoder=False
    )
    model.fit(X_train, y_train)

    # Eval
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, digits=3))

    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"📊 Cross-val Accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Feature importance
    importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    importances = importances.rename(lambda s: s.encode("ascii", "ignore").decode().strip())

    print("\n⚡ Top 10 important tags (XGBoost):")
    print(importances.head(10))

    plt.figure(figsize=(8, 10))
    sns.barplot(x=importances.values, y=importances.index, palette="mako", legend=False)
    plt.title(f"Feature Importance (XGBoost) – {path}")
    plt.xlabel("Importance (Gain)")
    plt.tight_layout()
    plt.show()

    return model

if __name__ == "__main__":
    # Logistic Regression
    model_case1 = train_logreg("train_case1.csv", "outcome_case1_binary")
    model_case2 = train_logreg("train_case2.csv", "outcome_case2_binary")

    # Random Forest
    rf_case1 = train_random_forest("train_case1.csv", "outcome_case1_binary")
    rf_case2 = train_random_forest("train_case2.csv", "outcome_case2_binary")

    # XGBoost
    xgb_case1 = train_xgboost("train_case1.csv", "outcome_case1_binary")
    xgb_case2 = train_xgboost("train_case2.csv", "outcome_case2_binary")
