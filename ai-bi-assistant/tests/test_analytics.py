from app.analytics import total_revenue, top_products, monthly_revenue, regional_revenue, compare_months, data_summary
from app.ingestion import prepare_data
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "data" / "sales_data.csv"

def test_ingestion_detects_missing_price_and_return():
    _, report = prepare_data(CSV)
    assert report["rows_seen"] == 51
    assert report["missing_unit_prices"] == 1
    assert report["returned_rows"] == 1

def test_ingestion_is_idempotent(populated_db):
    from app.ingestion import ingest_csv
    first = ingest_csv(CSV, populated_db)
    second = ingest_csv(CSV, populated_db)
    assert first["rows_inserted"] == 0
    assert second["rows_inserted"] == 0

def test_revenue_is_calculated_from_database(populated_db):
    result = total_revenue(populated_db)
    assert result["transaction_count"] == 49
    assert result["total_revenue"] > 0
    assert result["units_sold"] > 0

def test_top_products_sorted(populated_db):
    rows = top_products(5, populated_db)
    assert 1 <= len(rows) <= 5
    assert rows == sorted(rows, key=lambda row: (-row["revenue"], row["product"]))

def test_monthly_and_regional_analytics(populated_db):
    assert len(monthly_revenue(populated_db)) >= 5
    regions = regional_revenue(populated_db)
    assert {row["region"] for row in regions} == {"North", "South", "East", "West"}

def test_month_comparison(populated_db):
    result = compare_months("2026-01", "2026-02", populated_db)
    assert result["month1"] == "2026-01"
    assert result["month2"] == "2026-02"
    assert result["absolute_change"] == round(result["revenue2"] - result["revenue1"], 2)

def test_invalid_month_rejected(populated_db):
    import pytest
    with pytest.raises(ValueError): compare_months("January", "2026-02", populated_db)

def test_summary_quality_counts(populated_db):
    summary = data_summary(populated_db)
    assert summary["total_rows"] == 51
    assert summary["missing_unit_prices"] == 1
    assert summary["returned_rows"] == 1
