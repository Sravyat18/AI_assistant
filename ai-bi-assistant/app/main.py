from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app.analytics import (data_summary, total_revenue, top_products, monthly_revenue,
                           regional_revenue, compare_months, channel_revenue,
                           category_revenue, returned_count, query_all, VALID_SALES, NET_REVENUE_EXPR)
from app.ai_service import interpret_question
from app.database import initialize_database
from app.schemas import AskRequest

@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield

app = FastAPI(title="AI Business Intelligence Assistant", version="1.0.0",
              description="Natural-language sales analytics backed by validated SQLite queries.", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok", "service": "AI Business Intelligence Assistant"}

@app.get("/data/summary")
def summary():
    return data_summary()

@app.get("/analytics/monthly-revenue")
def get_monthly_revenue():
    return {"data": monthly_revenue(), "metric": "net_revenue"}

@app.get("/analytics/top-products")
def get_top_products(limit: int = 5):
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 50")
    return {"data": top_products(limit)}

@app.get("/analytics/regions")
def get_regions():
    return {"data": regional_revenue()}

@app.post("/ask")
def ask(request: AskRequest):
    try:
        intent_data, method = interpret_question(request.question)
        intent = intent_data["intent"]
        if intent == "total_revenue":
            result = total_revenue()
            answer = f"Total net revenue is {result['total_revenue']:,.2f} across {result['transaction_count']} eligible completed transactions."
            supporting = result
        elif intent == "top_product":
            rows = top_products(1)
            if not rows: raise ValueError("No eligible sales data is available.")
            result = rows[0]
            answer = f"{result['product']} generated the highest net revenue: {result['revenue']:,.2f}."
            supporting = rows
        elif intent == "top_products":
            supporting = top_products(int(intent_data.get("limit", 5)))
            result = supporting
            answer = "Top products by net revenue are shown in the supporting data."
        elif intent == "monthly_trend":
            result = monthly_revenue(); supporting = result
            answer = "Monthly net revenue trend is shown in the supporting data."
        elif intent == "top_region":
            rows = regional_revenue()
            if not rows: raise ValueError("No eligible sales data is available.")
            result = rows[0]; supporting = rows
            answer = f"{result['region']} generated the highest net revenue: {result['revenue']:,.2f}."
        elif intent == "compare_months":
            result = compare_months(intent_data["month1"], intent_data["month2"]); supporting = result
            if result["revenue1"] == 0:
                change = "percentage change is unavailable because the first month's revenue is zero"
            else:
                change = f"percentage change is {result['percentage_change']:.2f}%"
            answer = f"Revenue changed from {result['revenue1']:,.2f} in {result['month1']} to {result['revenue2']:,.2f} in {result['month2']}; absolute change: {result['absolute_change']:,.2f}; {change}."
        elif intent == "month_revenue":
            month = intent_data["month"]
            rows = query_all(f"SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM({NET_REVENUE_EXPR}), 2) AS revenue, COUNT(*) AS transaction_count FROM transactions WHERE {VALID_SALES} AND strftime('%Y-%m', order_date)=? GROUP BY strftime('%Y-%m', order_date)", (month,))
            result = rows[0] if rows else {"month": month, "revenue": 0, "transaction_count": 0}; supporting = result
            answer = f"Net revenue for {month} is {result['revenue']:,.2f}."
        elif intent == "channel_comparison":
            result = channel_revenue(); supporting = result; answer = "Net revenue by sales channel is shown in the supporting data."
        elif intent == "category_comparison":
            result = category_revenue(); supporting = result; answer = "Net revenue by category is shown in the supporting data."
        elif intent == "units_sold":
            result = {"units_sold": total_revenue()["units_sold"]}; supporting = result
            answer = f"Total units sold in eligible completed transactions: {result['units_sold']}."
        elif intent == "returned_count":
            result = returned_count(); supporting = result
            answer = f"There are {result['returned_transactions']} returned transaction(s) in the dataset."
        else:
            raise ValueError("Unsupported question intent.")
        warnings = []
        ds = data_summary()
        if ds.get("missing_unit_prices", 0): warnings.append(f"{ds['missing_unit_prices']} row(s) have missing unit prices and are excluded from revenue metrics.")
        if ds.get("returned_rows", 0): warnings.append(f"{ds['returned_rows']} returned row(s) are excluded from sales performance metrics but retained for auditing.")
        if ds.get("zero_quantity_rows", 0): warnings.append(f"{ds['zero_quantity_rows']} zero-quantity row(s) are retained and contribute zero gross sales.")
        return {"question": request.question, "intent": intent, "answer": answer, "result": result,
                "supporting_data": supporting, "query_method": method,
                "assumptions": ["Net sales = quantity × unit price − discount amount.", "Only Completed transactions with known non-negative prices, quantities, and discounts are included in sales KPIs."],
                "warnings": warnings}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Required question detail is missing: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics request failed. Check that the CSV has been imported and review the server logs.") from exc
