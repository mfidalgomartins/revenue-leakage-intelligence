"""
Data Profiling Module
Formal data profiling workflow: types, nulls, distributions, coverage, anomalies.
"""
import pandas as pd
import numpy as np
from datetime import datetime


def profile_dataframe(df, name="dataset"):
    """Run comprehensive profiling on a DataFrame."""
    report = {
        "dataset_name": name,
        "profiled_at": datetime.now().isoformat(),
        "row_count": len(df),
        "column_count": len(df.columns),
        "duplicate_rows": df.duplicated().sum(),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1e6, 2),
        "columns": {},
    }

    for col in df.columns:
        col_info = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "null_pct": round(df[col].isna().mean() * 100, 2),
            "unique_values": int(df[col].nunique()),
            "sample_values": df[col].dropna().head(3).tolist(),
        }

        if pd.api.types.is_bool_dtype(df[col]):
            col_info.update({
                "true_count": int(df[col].sum()),
                "true_pct": round(df[col].mean() * 100, 2),
            })
        elif pd.api.types.is_numeric_dtype(df[col]):
            desc = df[col].describe()
            col_info.update({
                "mean": round(float(desc.get("mean", 0)), 2),
                "std": round(float(desc.get("std", 0)), 2),
                "min": float(desc.get("min", 0)),
                "p25": float(desc.get("25%", 0)),
                "median": float(desc.get("50%", 0)),
                "p75": float(desc.get("75%", 0)),
                "max": float(desc.get("max", 0)),
                "zeros": int((df[col] == 0).sum()),
                "negatives": int((df[col] < 0).sum()),
            })
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_info.update({
                "min_date": str(df[col].min()),
                "max_date": str(df[col].max()),
                "date_range_days": (df[col].max() - df[col].min()).days,
            })
        elif df[col].dtype == "object":
            vc = df[col].value_counts()
            col_info.update({
                "top_values": vc.head(5).to_dict(),
                "avg_length": round(df[col].dropna().str.len().mean(), 1)
                if df[col].dropna().str.len().mean() else None,
            })

        report["columns"][col] = col_info

    return report


def print_profile(report):
    """Print a formatted profiling report."""
    print(f"\n{'='*60}")
    print(f"DATA PROFILE: {report['dataset_name']}")
    print(f"{'='*60}")
    print(f"Rows: {report['row_count']:,}  |  Columns: {report['column_count']}")
    print(f"Duplicates: {report['duplicate_rows']:,}  |  Memory: {report['memory_mb']} MB")
    print(f"{'='*60}")

    for col, info in report["columns"].items():
        null_flag = " ⚠️" if info["null_pct"] > 5 else ""
        print(f"\n  {col} ({info['dtype']}){null_flag}")
        print(f"    Nulls: {info['null_count']} ({info['null_pct']}%)")
        print(f"    Unique: {info['unique_values']}")

        if "mean" in info:
            print(f"    Range: [{info['min']}, {info['max']}]")
            print(f"    Mean: {info['mean']} (±{info['std']})")
            if info.get("negatives", 0) > 0:
                print(f"    ⚠️ Negatives: {info['negatives']}")
            if info.get("zeros", 0) > 0:
                print(f"    Zeros: {info['zeros']}")
        elif "top_values" in info:
            top3 = dict(list(info["top_values"].items())[:3])
            print(f"    Top: {top3}")

    print(f"\n{'='*60}\n")
    return report


def check_suspicious_values(df, name="dataset"):
    """Flag suspicious data patterns."""
    issues = []

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            # Extreme outliers (>5 std from mean)
            mean, std = df[col].mean(), df[col].std()
            if std > 0:
                outliers = ((df[col] - mean).abs() > 5 * std).sum()
                if outliers > 0:
                    issues.append(f"[{name}.{col}] {outliers} extreme outliers (>5σ)")

            # Negative values in typically positive fields
            if any(kw in col.lower() for kw in ["revenue", "mrr", "price", "amount", "collected"]):
                negs = (df[col] < 0).sum()
                if negs > 0:
                    issues.append(f"[{name}.{col}] {negs} unexpected negative values")

    # Check for future dates
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            future = (df[col] > pd.Timestamp.now()).sum()
            if future > 0:
                issues.append(f"[{name}.{col}] {future} future dates")

    return issues
