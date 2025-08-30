import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt
import seaborn as sns

def train_logreg(path: str, target_col: str):
    print(f"\n🔎 Training Logistic Regression on {path} ...")
    
    # Load dataset
    df = pd.read_csv(path)
    X = df.drop(columns=[target_col])
    y = df[target_col]

    print("🔎 Class distribution:", y.value_counts().to_dict())

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Model
    model = LogisticRegression(max_iter=500, solver="liblinear")  # liblinear handles small datasets well
    model.fit(X_train, y_train)

    # Eval
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, digits=3))

    # Cross-validation score (5-fold)
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"📊 Cross-val Accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Feature importance (coefficients)
    coefs = pd.Series(model.coef_[0], index=X.columns).sort_values(ascending=False)

    # 🔧 Strip emojis & extra spaces for cleaner labels in the plot
    coefs = coefs.rename(lambda s: s.encode("ascii", "ignore").decode().strip())

    plt.figure(figsize=(8, 10))
    sns.barplot(x=coefs.values, y=coefs.index, palette="coolwarm")
    plt.title(f"Feature Importance (Logistic Regression) – {path}")
    plt.xlabel("Coefficient (log-odds impact)")
    plt.axvline(0, color="black", linestyle="--")
    plt.tight_layout()
    plt.show()

    return model

if __name__ == "__main__":
    # Train Case 1
    model_case1 = train_logreg("train_case1.csv", "outcome_case1_binary")

    # Train Case 2
    model_case2 = train_logreg("train_case2.csv", "outcome_case2_binary")
