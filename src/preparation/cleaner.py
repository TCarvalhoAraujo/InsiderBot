import pandas as pd

from config.problematic_tickers import IPO_TICKERS, NO_MARKET_CAP_TICKERS

def pre_ohlc_noise_reduction(
    tickers: list[str], 
    snapshots: dict, 
    min_market_cap: int = 150_000_000
) -> list[str]:
    """
    Filters tickers before tagging:
    - Excludes IPO_TICKERS and NO_MARKET_CAP_TICKERS
    - Excludes tickers with market cap < min_market_cap

    Args:
        tickers (list[str]): List of tickers to evaluate.
        snapshots (dict): Snapshot cache containing metadata.
        min_market_cap (int): Minimum market cap to keep (default=150M).

    Returns:
        list[str]: Valid tickers that pass filtering.
    """
    exclude_tickers = IPO_TICKERS.union(NO_MARKET_CAP_TICKERS)

    valid = []
    dropped = []

    for t in tickers:
        cap = snapshots.get(t, {}).get("market_cap")

        if t in exclude_tickers:
            dropped.append((t, "excluded list"))
            continue
        if cap is None:
            dropped.append((t, "no market cap"))
            continue
        if cap < min_market_cap:
            dropped.append((t, f"market cap {cap:,} < {min_market_cap:,}"))
            continue

        valid.append(t)

    print(f"🧹 Prefilter: {len(valid)} valid tickers, {len(dropped)} dropped")
    for t, reason in dropped[:10]:  # show first 10 reasons
        print(f"   - {t}: {reason}")
    if len(dropped) > 10:
        print(f"   ... and {len(dropped) - 10} more dropped")

    return valid

def drop_low_atr_trades(df: pd.DataFrame, min_atr_pct: float = 0.02) -> pd.DataFrame:
    """
    Drops trades where ATR% is below the minimum threshold.
    
    Parameters
    ----------
    df : pd.DataFrame
        Must include 'ticker' and 'atr_14_pct'.
    min_atr_pct : float
        Minimum ATR% required (default = 0.02 = 2%).
    
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame with low-ATR trades removed.
    """
    before = len(df)

    # Identify tickers to drop
    dropped_rows = df[df["atr_14_pct"] < min_atr_pct]
    dropped_tickers = dropped_rows["ticker"].unique().tolist()

    # Keep only valid rows
    df = df[df["atr_14_pct"] >= min_atr_pct].copy()
    after = len(df)

    print(f"🧹 ATR Filter: removed {before - after} rows (ATR% < {min_atr_pct:.2%}), kept {after}")
    if dropped_tickers:
        print("📉 Dropped tickers due to low volatility:")
        for t in dropped_tickers:
            print(f"   - {t}")
    else:
        print("✅ No tickers dropped by ATR filter.")

    return df

def drop_split_merger_anomalies(df: pd.DataFrame, threshold: float = 1.70) -> pd.DataFrame:
    """
    Drops trades where insider buy price differs significantly
    from the market open price on the trade date (possible split/merger).
    
    Parameters
    ----------
    df : pd.DataFrame
        Must include 'ticker', 'transaction_date', 'price' (insider buy), and 'market_open_at_trade'.
    threshold : float
        Ratio cutoff for anomaly detection (default = 1.70).
    
    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with anomalies removed.
    """
    before = len(df)

    ratios = df.apply(
        lambda row: (
            max(row["price"], row["market_open_at_trade"]) /
            min(row["price"], row["market_open_at_trade"])
        ) if row["market_open_at_trade"] and row["price"] else 1,
        axis=1
    )

    anomalies = df[ratios > threshold]
    df = df[ratios <= threshold].copy()
    after = len(df)

    print(f"🧹 Split/Merger Filter: removed {before - after} rows (ratio > {threshold}), kept {after}")
    if not anomalies.empty:
        print("⚠️ Dropped anomalies:")
        for _, row in anomalies.iterrows():
            print(f"   - {row['ticker']} on {row['transaction_date'].date()} "
                  f"(insider price={row['price']}, open={row['market_open_at_trade']})")
    else:
        print("✅ No anomalies detected.")

    return df