import pytest
from app.question_parser import parse_question

def test_total_revenue_intent():
    assert parse_question("What is the total revenue?")["intent"] == "total_revenue"

def test_compare_months_intent():
    result = parse_question("Compare revenue between January 2026 and February 2026")
    assert result == {"intent": "compare_months", "month1": "2026-01", "month2": "2026-02"}

def test_unsupported_question_rejected():
    with pytest.raises(ValueError): parse_question("What is the weather tomorrow?")

def test_destructive_request_rejected():
    with pytest.raises(ValueError): parse_question("DROP TABLE transactions")

def test_blank_question_rejected():
    with pytest.raises(ValueError): parse_question("   ")

def test_highest_product_maps_to_single_product():
    assert parse_question("Which product generated the highest revenue?")["intent"] == "top_product"

def test_top_five_products_maps_to_ranking():
    assert parse_question("Show the top five products by revenue")["intent"] == "top_products"

def test_channel_comparison_not_misread_as_month_comparison():
    assert parse_question("Compare online and retail sales")["intent"] == "channel_comparison"
