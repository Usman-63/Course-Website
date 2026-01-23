"""
DataFrame normalization helpers.
"""
import pandas as pd


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize DataFrame: strip whitespace, handle NaN values.
    """
    df = df.copy()

    # Strip whitespace from string columns
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
            # Replace 'nan' strings with actual NaN
            df[col] = df[col].replace(["nan", "None", ""], pd.NA)

    return df


