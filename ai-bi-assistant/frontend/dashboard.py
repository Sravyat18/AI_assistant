import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="AI Business Intelligence Assistant", page_icon="📊", layout="wide")
st.title("📊 AI Business Intelligence Assistant")
st.caption("Ask questions about sales data. Answers are calculated from SQLite queries; AI is used only to interpret the question when configured.")

@st.cache_data(ttl=30)
def get_json(path):
    response = requests.get(f"{API_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()

try:
    summary = get_json("/data/summary")
    monthly = get_json("/analytics/monthly-revenue")["data"]
    products = get_json("/analytics/top-products?limit=5")["data"]
    regions = get_json("/analytics/regions")["data"]
    total_response = requests.post(f"{API_URL}/ask", json={"question": "What is the total revenue?"}, timeout=15)
    total_response.raise_for_status()
    total = total_response.json()["result"]
except Exception as exc:
    st.error("Cannot connect to the backend. Start FastAPI in another terminal with: uvicorn app.main:app --reload")
    st.caption(f"Technical detail: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Net revenue", f"{total['total_revenue']:,.2f}")
c2.metric("Eligible transactions", f"{total['transaction_count']:,}")
c3.metric("Units sold", f"{total['units_sold']:,}")
c4.metric("Flagged rows", f"{summary.get('flagged_rows') or 0:,}")
st.info("Calculation policy: Net sales = quantity × unit price − discount. Returned transactions and rows with missing unit prices are excluded from sales KPIs.")

st.subheader("Ask a business question")
examples = [
    "What is the total revenue?",
    "Which product generated the highest revenue?",
    "What is the monthly revenue trend?",
    "Which region generated the highest sales?",
    "Compare revenue between January 2026 and February 2026",
    "Compare online and retail sales",
    "Which category performed best?",
    "How many transactions were returned?",
]
selected = st.selectbox("Example questions", ["Choose an example..."] + examples)
with st.form("ask_form"):
    question = st.text_input("Your question", value="" if selected == "Choose an example..." else selected, placeholder="e.g. Which product generated the highest revenue?")
    submitted = st.form_submit_button("Ask", type="primary")
if submitted:
    try:
        with st.spinner("Analyzing sales data..."):
            response = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=30)
        if response.ok:
            answer_data = response.json()
            st.success(answer_data["answer"])
            st.caption(f"Intent: {answer_data['intent']} · Interpreter: {answer_data['query_method']}")
            st.write("**Supporting figures**")
            result_data = answer_data["supporting_data"]
            if isinstance(result_data, list): st.dataframe(pd.DataFrame(result_data), use_container_width=True, hide_index=True)
            else: st.json(result_data)
            if answer_data.get("warnings"):
                for warning in answer_data["warnings"]: st.warning(warning)
            with st.expander("Calculation assumptions"):
                for assumption in answer_data.get("assumptions", []): st.write(f"- {assumption}")
        else:
            st.error(response.json().get("detail", "The question could not be processed."))
    except Exception as exc:
        st.error(f"Request failed: {exc}")

left, right = st.columns(2)
with left:
    st.subheader("Monthly net revenue")
    if monthly:
        frame = pd.DataFrame(monthly)
        st.plotly_chart(px.line(frame, x="month", y="revenue", markers=True, title="Revenue by month"), use_container_width=True)
    else: st.info("No eligible monthly sales data available.")
with right:
    st.subheader("Regional performance")
    if regions:
        frame = pd.DataFrame(regions)
        st.plotly_chart(px.bar(frame, x="region", y="revenue", title="Net revenue by region"), use_container_width=True)
    else: st.info("No eligible regional sales data available.")

st.subheader("Top products")
if products: st.dataframe(pd.DataFrame(products), use_container_width=True, hide_index=True)
with st.expander("Data quality report"):
    st.write("Summary of source rows and flagged records:")
    st.json(summary)
    st.write("Rows with issues are retained for audit where possible. Missing prices are not imputed; zero-quantity rows are retained; returned rows are excluded from sales KPIs.")
st.caption("AI Business Intelligence Assistant · Data-backed answers, safe question interpretation, and deterministic calculations.")
