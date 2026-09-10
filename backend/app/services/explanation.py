import json
from app.core.config import settings


def deterministic_explanation(invoice, failures):
    if not failures:
        return (
            "All configured deterministic checks passed. The invoice matches its purchase order and can follow the automatic approval path.",
            "Proceed with the normal payment workflow."
        )
    top = failures[:4]
    summary = " ".join(v.message for v in top)
    return (
        f"The invoice was flagged by {len(failures)} deterministic check(s). {summary}",
        "Manual review is required before payment. Verify the source document and purchase order, then approve or reject with a note."
    )


def explain(invoice, failures):
    fallback = deterministic_explanation(invoice, failures)
    if settings.llm_provider.lower() != "openai" or not settings.openai_api_key:
        return fallback
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        payload = {
            "invoice_number": invoice.invoice_number,
            "supplier": invoice.supplier_name,
            "po_number": invoice.po_number,
            "risk_score": invoice.risk_score,
            "risk_level": invoice.risk_level,
            "findings": [{"code": v.rule_code, "message": v.message, "expected": v.expected_value, "actual": v.actual_value} for v in failures],
        }
        response = client.responses.create(
            model=settings.openai_model,
            instructions=(
                "You are an accounts-payable reviewer assistant. Explain only the supplied deterministic findings. "
                "Do not recalculate, invent facts, or override the decision. Produce two short sections: Explanation and Recommendation."
            ),
            input=json.dumps(payload),
            store=False,
        )
        text = response.output_text.strip()
        if "Recommendation" in text:
            a, b = text.split("Recommendation", 1)
            return a.replace("Explanation", "").strip(" :\n#*"), b.strip(" :\n#*")
        return text, fallback[1]
    except Exception:
        return fallback
