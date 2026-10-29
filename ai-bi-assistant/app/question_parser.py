import re
from datetime import datetime

SUPPORTED_INTENTS = {"total_revenue", "top_product", "monthly_trend", "top_region", "compare_months", "channel_comparison", "category_comparison", "units_sold", "month_revenue", "returned_count", "top_products"}


def _month_from_text(text: str) -> list[str]:
    names = {name.lower(): i for i, name in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
    found = []
    for name, number in names.items():
        for m in re.finditer(rf"\b{name}\s+(20\d{{2}})\b", text, re.I):
            found.append((m.start(), f"{int(m.group(1)):04d}-{number:02d}"))
    for m in re.finditer(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", text):
        found.append((m.start(), f"{m.group(1)}-{m.group(2)}"))
    for m in re.finditer(r"\b(0?[1-9]|1[0-2])/(20\d{2})\b", text):
        found.append((m.start(), f"{m.group(2)}-{int(m.group(1)):02d}"))
    return [x[1] for x in sorted(found)]


def parse_question(question: str) -> dict:
    q = " ".join((question or "").strip().lower().split())
    if not q:
        raise ValueError("Please enter a question.")
    if any(x in q for x in ["drop table", "delete from", "update transactions", ";--", "insert into", "delete all"]):
        raise ValueError("This request contains a potentially unsafe database instruction. Ask a sales-analysis question instead.")
    months = _month_from_text(q)
    if any(k in q for k in ["returned", "returns"]):
        return {"intent": "returned_count"}
    if "channel" in q or "online and retail" in q or "online vs retail" in q or "compare online" in q:
        return {"intent": "channel_comparison"}
    if "categor" in q:
        return {"intent": "category_comparison"}
    if "compare" in q or "change between" in q or "between" in q and "revenue" in q:
        if len(months) >= 2:
            return {"intent": "compare_months", "month1": months[0], "month2": months[1]}
        raise ValueError("Please specify two months, for example: Compare revenue between January 2026 and February 2026.")
    if "unit" in q and ("sold" in q or "total" in q or "how many" in q):
        return {"intent": "units_sold"}
    if "region" in q:
        return {"intent": "top_region"}
    if "monthly" in q or "month trend" in q or "trend" in q:
        return {"intent": "monthly_trend"}
    if months and any(k in q for k in ["revenue", "sales"]):
        return {"intent": "month_revenue", "month": months[0]}
    if "product" in q and any(k in q for k in ["highest", "most", "best", "generated"]):
        if re.search(r"\btop\s+\d+\b", q):
            n = re.search(r"\btop\s+(\d+)\b", q)
            return {"intent": "top_products", "limit": min(int(n.group(1)), 20)}
        return {"intent": "top_product"}
    if "product" in q and any(k in q for k in ["top", "rank"]):
        n = re.search(r"\btop\s+(\d+)\b", q)
        return {"intent": "top_products", "limit": min(int(n.group(1)), 20) if n else 5}
    if "revenue" in q or "sales" in q or "total amount" in q:
        return {"intent": "total_revenue"}
    raise ValueError("I couldn't map that question to a supported analysis. Try total revenue, top product, monthly trend, top region, or compare two months.")
