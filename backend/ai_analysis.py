import os
from backend.ai_providers import get_ai_response

def analyze_vulnerabilities(vulnerabilities: list, model: str = "openai") -> str:
    if not vulnerabilities:
        return "✅ No vulnerabilities found!"

    prompt = f"""
    Analyze the following security vulnerabilities and summarize them:
    {vulnerabilities}

    Provide:
    1. A concise summary of risk.
    2. Recommended fixes in plain English.
    """

    try:
        result = get_ai_response(prompt, model)
        # If provider returned an error-like string starting with the warning marker,
        # propagate it as-is (it will be sanitized/masked by the provider layer).
        if isinstance(result, str) and result.startswith("⚠️"):
            return result
        return result
    except Exception:
        # Avoid returning raw exception details (which may contain secrets).
        return "⚠️ AI analysis encountered an unexpected error. Please check backend logs for details."
