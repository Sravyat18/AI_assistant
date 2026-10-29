import argparse
from pathlib import Path
import pandas as pd

from app.database import get_connection, initialize_database, PROJECT_ROOT

REQUIRED_COLUMNS = [
    "Transaction_Id", "Order_date", "Product", "Category", "Region",
    "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"
]


def prepare_data(csv_path: str | Path) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(csv_path)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")
    df = df[REQUIRED_COLUMNS].copy()
    df["Order_date"] = pd.to_datetime(df["Order_date"], format="%d-%m-%Y", errors="coerce")
    for col in ["Quantity", "Unit_price", "Discount_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    flags = []
    for _, row in df.iterrows():
        row_flags = []
        if pd.isna(row["Order_date"]): row_flags.append("invalid_order_date")
        for col in ["Transaction_Id", "Product", "Category", "Region", "Sales_channel", "Status"]:
            if pd.isna(row[col]) or not str(row[col]).strip(): row_flags.append(f"missing_{col.lower()}")
        if pd.isna(row["Unit_price"]): row_flags.append("missing_unit_price")
        elif row["Unit_price"] < 0: row_flags.append("negative_unit_price")
        if pd.isna(row["Quantity"]): row_flags.append("invalid_quantity")
        elif row["Quantity"] < 0: row_flags.append("negative_quantity")
        elif row["Quantity"] == 0: row_flags.append("zero_quantity")
        if pd.isna(row["Discount_amount"]): row_flags.append("invalid_discount")
        elif row["Discount_amount"] < 0: row_flags.append("negative_discount")
        if str(row["Status"]).strip().lower() == "returned": row_flags.append("returned_transaction")
        flags.append(";".join(row_flags))
    df["data_quality_flags"] = flags
    duplicate_mask = df["Transaction_Id"].duplicated(keep="first")
    df.loc[duplicate_mask, "data_quality_flags"] = df.loc[duplicate_mask, "data_quality_flags"].apply(
        lambda x: (x + ";duplicate_transaction_id").strip(";")
    )
    df["order_date_iso"] = df["Order_date"].dt.strftime("%Y-%m-%d")
    df["Order_date"] = df["order_date_iso"]
    df = df.drop(columns=["order_date_iso"])
    summary = {
        "rows_seen": int(len(df)),
        "rows_flagged": int(sum(bool(x) for x in df["data_quality_flags"])),
        "duplicate_ids": int(duplicate_mask.sum()),
        "missing_unit_prices": int(df["Unit_price"].isna().sum()),
        "zero_quantity_rows": int((df["Quantity"] == 0).sum()),
        "returned_rows": int(df["Status"].astype(str).str.lower().eq("returned").sum()),
    }
    return df, summary


def ingest_csv(csv_path: str | Path, db_path: str | None = None) -> dict:
    df, summary = prepare_data(csv_path)
    initialize_database(db_path)
    inserted = 0
    with get_connection(db_path) as conn:
        for _, row in df.iterrows():
            if pd.isna(row["Order_date"]) or pd.isna(row["Transaction_Id"]) or not str(row["Transaction_Id"]).strip():
                continue
            try:
                cursor = conn.execute("""
                    INSERT OR IGNORE INTO transactions
                    (transaction_id, order_date, product, category, region, sales_channel,
                     quantity, unit_price, discount_amount, status, data_quality_flags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(row["Transaction_Id"]).strip(), str(row["Order_date"]), str(row["Product"]),
                    str(row["Category"]), str(row["Region"]), str(row["Sales_channel"]),
                    int(row["Quantity"]) if pd.notna(row["Quantity"]) else 0,
                    float(row["Unit_price"]) if pd.notna(row["Unit_price"]) else None,
                    float(row["Discount_amount"]) if pd.notna(row["Discount_amount"]) else 0.0,
                    str(row["Status"]), str(row["data_quality_flags"])
                ))
                inserted += cursor.rowcount
            except (ValueError, TypeError, OverflowError):
                continue
        conn.execute("INSERT INTO ingestion_runs(source_file, rows_seen, rows_inserted, rows_flagged) VALUES (?, ?, ?, ?)",
                     (str(Path(csv_path).name), summary["rows_seen"], inserted, summary["rows_flagged"]))
    summary.update({"rows_inserted": inserted, "rows_skipped_or_already_present": summary["rows_seen"] - inserted})
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import the supplied sales CSV into SQLite.")
    parser.add_argument("--csv", default=str(PROJECT_ROOT / "data" / "sales_data.csv"))
    parser.add_argument("--db", default=None)
    args = parser.parse_args()
    print(ingest_csv(args.csv, args.db))
