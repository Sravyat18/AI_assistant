"""Optional LLM intent parsing. The app remains functional without an API key."""
import json
import os
import re
from app.question_parser import parse_question, SUPPORTED_INTENTS


def interpret_question(question: str) -> tuple[dict, str]:
    # Apply safety checks before any optional LLM interpretation.
    if re.search(r"\b(drop\s+table|delete\s+from|update\s+transactions|insert\s+into|delete\s+all)\b|;--", question or "", re.I):
        raise ValueError("This request contains a potentially unsafe database instruction. Ask a sales-analysis question instead.")
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Convert the user's sales analytics question into JSON only. Allowed intents: " + ", ".join(sorted(SUPPORTED_INTENTS)) + ". Fields: intent, month (YYYY-MM), month1 (YYYY-MM), month2 (YYYY-MM), limit (integer 1-20). Never write SQL. If unsupported, return {\"intent\":\"unsupported\"}."},
                    {"role": "user", "content": question}
                ],
            )
            parsed = json.loads(response.choices[0].message.content)
            if parsed.get("intent") not in SUPPORTED_INTENTS:
                raise ValueError("The AI could not identify a supported analysis.")
            # Validate AI output by allowing only known fields and strict month/limit formats.
            allowed = {"intent", "month", "month1", "month2", "limit"}
            parsed = {k: v for k, v in parsed.items() if k in allowed}
            for key in ("month", "month1", "month2"):
                if key in parsed and (not isinstance(parsed[key], str) or len(parsed[key]) != 7 or parsed[key][4] != "-"):
                    raise ValueError("Invalid month returned by the AI interpreter.")
            if parsed["intent"] == "compare_months" and not all(parsed.get(k) for k in ("month1", "month2")):
                raise ValueError("Please specify two months for comparison.")
            if parsed["intent"] == "month_revenue" and not parsed.get("month"):
                raise ValueError("Please specify a month.")
            return parsed, "llm"
        except Exception:
            # Fall back safely; do not let an AI outage prevent deterministic analytics.
            pass
    return parse_question(question), "rule_based_fallback"
