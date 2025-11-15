import os
import re
import requests
from openai import OpenAI

# Optional: Gemini via REST API
from typing import Literal

ModelType = Literal["openai", "gemini", "llama"]

def get_ai_response(prompt: str, model: ModelType = "openai") -> str:
    """
    Returns a response from the selected AI provider.
    """

    if model == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "⚠️ OpenAI API key not configured. Set OPENAI_API_KEY in environment."

        client = OpenAI(api_key=api_key)
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert DevSecOps AI assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            # Mask any raw-looking API key in the exception text before returning
            text = str(exc)
            masked = re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", text)
            # Detect common invalid key patterns and return a clear, non-sensitive hint
            lower = text.lower()
            if "invalid_api_key" in lower or "incorrect api key" in lower or "401" in lower:
                return "⚠️ OpenAI API error: Invalid or unauthorized API key. Please set a valid OPENAI_API_KEY."
            return f"⚠️ OpenAI provider error: {masked}"

    elif model == "gemini":
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            return "⚠️ Gemini API key not configured."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload)
        try:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            # Mask any sk-... occurrences before returning
            masked = re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", response.text)
            return f"⚠️ Gemini Error: {masked}"

    elif model == "llama":
        LLAMA_API_URL = os.getenv("LLAMA_API_URL", "http://localhost:11434/api/generate")
        payload = {"model": "llama3", "prompt": prompt}
        response = requests.post(LLAMA_API_URL, json=payload, stream=True)
        output = ""
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                if '"response":"' in data:
                    output += data.split('"response":"')[1].split('"')[0]
        return output.strip()

    else:
        return "❌ Unsupported AI model type."
