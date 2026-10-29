from datetime import date
from app.database import get_connection

# Sales KPIs include only completed rows with known non-negative prices/quantities/discounts.
# Returned rows remain stored for auditing but are excluded from sales performance metrics.
VALID_SALES = "LOWER(status) = 'completed' AND unit_price IS NOT NULL AND unit_price >= 0 AND quantity >= 0 AND discount_amount >= 0"
NET_REVENUE_EXPR = "(quantity * unit_price - discount_amount)"


def query_all(sql: str, params: tuple = (), db_path: str | None = None) -> list[dict]:
    with get_connection(db_path) as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def query_one(sql: str, params: tuple = (), db_path: str | None = None) -> dict:
    with get_connection(db_path) as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else {}


def data_summary(db_path: str | None = None) -> dict:
    return query_one("""
        SELECT COUNT(*) AS total_rows,
               SUM(CASE WHEN data_quality_flags <> '' THEN 1 ELSE 0 END) AS flagged_rows,
               SUM(CASE WHEN unit_price IS NULL THEN 1 ELSE 0 END) AS missing_unit_prices,
               SUM(CASE WHEN LOWER(status) = 'returned' THEN 1 ELSE 0 END) AS returned_rows,
               SUM(CASE WHEN quantity = 0 THEN 1 ELSE 0 END) AS zero_quantity_rows
        FROM transactions
    """, db_path=db_path)


def total_revenue(db_path: str | None = None) -> dict:
    return query_one(f"SELECT ROUND(COALESCE(SUM({NET_REVENUE_EXPR}), 0), 2) AS total_revenue, COUNT(*) AS transaction_count, COALESCE(SUM(quantity), 0) AS units_sold FROM transactions WHERE {VALID_SALES}", db_path=db_path)


def top_products(limit: int = 5, db_path: str | None = None) -> list[dict]:
    limit = max(1, min(int(limit), 50))
    return query_all(f"SELECT product, ROUND(SUM({NET_REVENUE_EXPR}), 2) AS revenue, SUM(quantity) AS units_sold, COUNT(*) AS transaction_count FROM transactions WHERE {VALID_SALES} GROUP BY product ORDER BY revenue DESC, product ASC LIMIT ?", (limit,), db_path)


def monthly_revenue(db_path: str | None = None) -> list[dict]:
    return query_all(f"SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM({NET_REVENUE_EXPR}), 2) AS revenue, COUNT(*) AS transaction_count FROM transactions WHERE {VALID_SALES} GROUP BY strftime('%Y-%m', order_date) ORDER BY month", db_path=db_path)


def regional_revenue(db_path: str | None = None) -> list[dict]:
    return query_all(f"SELECT region, ROUND(SUM({NET_REVENUE_EXPR}), 2) AS revenue, SUM(quantity) AS units_sold, COUNT(*) AS transaction_count FROM transactions WHERE {VALID_SALES} GROUP BY region ORDER BY revenue DESC, region ASC", db_path=db_path)


def compare_months(month1: str, month2: str, db_path: str | None = None) -> dict:
    for month in (month1, month2):
        try:
            date.fromisoformat(month + "-01")
        except ValueError:
            raise ValueError("Months must use YYYY-MM format, for example 2026-01")
        if len(month) != 7:
            raise ValueError("Months must use YYYY-MM format, for example 2026-01")
    sql = f"SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM({NET_REVENUE_EXPR}), 2) AS revenue FROM transactions WHERE {VALID_SALES} AND strftime('%Y-%m', order_date) IN (?, ?) GROUP BY strftime('%Y-%m', order_date)"
    rows = query_all(sql, (month1, month2), db_path)
    by_month = {r["month"]: float(r["revenue"] or 0) for r in rows}
    a, b = by_month.get(month1, 0.0), by_month.get(month2, 0.0)
    return {"month1": month1, "revenue1": round(a, 2), "month2": month2, "revenue2": round(b, 2), "absolute_change": round(b - a, 2), "percentage_change": round(((b - a) / a) * 100, 2) if a else None}


def channel_revenue(db_path: str | None = None) -> list[dict]:
    return query_all(f"SELECT sales_channel, ROUND(SUM({NET_REVENUE_EXPR}), 2) AS revenue, SUM(quantity) AS units_sold FROM transactions WHERE {VALID_SALES} GROUP BY sales_channel ORDER BY revenue DESC", db_path=db_path)


def category_revenue(db_path: str | None = None) -> list[dict]:
    return query_all(f"SELECT category, ROUND(SUM({NET_REVENUE_EXPR}), 2) AS revenue, SUM(quantity) AS units_sold FROM transactions WHERE {VALID_SALES} GROUP BY category ORDER BY revenue DESC", db_path=db_path)


def returned_count(db_path: str | None = None) -> dict:
    return query_one("SELECT COUNT(*) AS returned_transactions FROM transactions WHERE LOWER(status) = 'returned'", db_path=db_path)
