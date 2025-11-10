# backend/repo_analyzer.py
import requests
import os
from fastapi import HTTPException
from openai import OpenAI
import tempfile
import git
from backend.report_generator import generate_review_pdf
from backend import history
import logging
import re
import json

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_github_pr(repo: str, pr_number: int) -> str:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    diff_url = r.json().get("diff_url")
    diff_resp = requests.get(diff_url, headers=headers)
    if diff_resp.status_code != 200:
        raise HTTPException(status_code=diff_resp.status_code, detail=diff_resp.text)
    return diff_resp.text

def fetch_gitlab_mr(project_id: str, mr_id: int) -> str:
    url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{mr_id}/changes"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN} if GITLAB_TOKEN else {}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    data = r.json()
    diffs = []
    for change in data.get("changes", []):
        filename = change.get("new_path") or change.get("old_path") or "unknown"
        diff_text = change.get("diff", "")
        diffs.append(f"*** FILE: {filename} ***\n{diff_text}\n")
    return "\n".join(diffs)

def analyze_code_diff(diff_text: str) -> str:
    # If no API key is configured, return a friendly warning string instead of
    # raising an exception so the caller can still produce a PDF/history entry.
    if not OPENAI_API_KEY:
        return "⚠️ OpenAI API key not configured. Set OPENAI_API_KEY in the container environment to enable AI analysis."
    prompt = f"""
You are a senior DevSecOps engineer and code reviewer.
Analyze the following code diff for:
1) Security vulnerabilities (explain risk and impact)
2) Code quality & maintainability
3) Performance & algorithmic concerns
4) Concrete suggestions (code-level if possible)

Provide a short summary and grouped bullet points.

Diff (truncated):
{diff_text[:12000]}
"""
    # Force the model to reply in English so UI and downstream tooling remain
    # consistent regardless of repository/native language. If the diff contains
    # non-English content, summarize it in English.
    prompt = "Respond in English only. If the diff contains non-English text, provide the summary and suggestions in English.\n\n" + prompt
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a security-minded code reviewer."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # Don't propagate raw exceptions to the API surface. Mask any API keys
        # and return a friendly message so the flow can continue.
        import re
        text = str(e)
        masked = re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", text)
        low = masked.lower()
        # Detect common invalid-key / unauthorized responses and give a clear
        # actionable message the user can follow (without leaking keys).
        if "invalid_api_key" in low or "incorrect api key" in low or "unauthorized" in low or "invalid_api_key" in low:
            return (
                "⚠️ OpenAI API error: Invalid or unauthorized API key. "
                "Please rotate your OpenAI API key at https://platform.openai.com/account/api-keys and set the new value in OPENAI_API_KEY, "
                "then restart the backend. (Do NOT paste keys into logs or public channels.)"
            )
        return f"⚠️ AI analysis failed: {masked}"

def _simple_severity_counts_from_ai(ai_text: str):
    """
    Simple heuristic: count occurrences of words 'critical','high','medium','low'
    in AI output to produce a rough severity distribution.
    This is lightweight; you can later replace with proper extraction/parsing.
    """
    txt = ai_text.lower()
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    counts["critical"] = txt.count("critical")
    counts["high"] = txt.count("high")
    counts["medium"] = txt.count("medium")
    counts["low"] = txt.count("low")
    return counts

def post_github_comment(repo: str, pr_number: int, body: str) -> bool:
    if not GITHUB_TOKEN:
        return False
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    r = requests.post(url, headers=headers, json={"body": body})
    return r.status_code in (200, 201)

def post_gitlab_comment(project_id: str, mr_id: int, body: str) -> bool:
    if not GITLAB_TOKEN:
        return False
    url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{mr_id}/notes"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    r = requests.post(url, headers=headers, data={"body": body})
    return r.status_code in (200, 201)

def analyze_pr_and_make_pdf(platform: str, repo_or_project: str, number: int, post_comment: bool = False):
    # Accept either a short repo (user/repo) + number or a full PR/MR URL
    # If a full URL is given, prefer values parsed from the URL.
    url_match = re.search(r"(github|gitlab)\.com/([^/]+)/([^/]+)/(?:pull|pulls|merge_requests|-/merge_requests)/(\d+)", str(repo_or_project))
    if url_match:
        parsed_platform, user, repo_name, parsed_number = url_match.groups()
        platform = parsed_platform
        repo_or_project = f"{user}/{repo_name}"
        try:
            number = int(parsed_number)
        except Exception:
            # keep provided number if parse fails
            pass

    # Prepare filenames/paths up front so we can still attempt to save history
    # even if fetching the diff fails.
    slug = str(repo_or_project).replace("/", "_")
    if platform == "github":
        pdf_name = f"{slug}_pr{number}_review.pdf"
    else:
        pdf_name = f"{slug}_mr{number}_review.pdf"

    # Fetch diff (best-effort). If fetching fails, continue with an explanatory
    # diff_text so downstream steps can still produce a PDF and a history entry.
    diff_text = ""
    pdf_path = ""
    pdf_error = None
    try:
        if platform == "github":
            diff_text = fetch_github_pr(repo_or_project, number)
        else:
            diff_text = fetch_gitlab_mr(repo_or_project, number)
    except Exception as e:
        # mask api keys if present
        import re as _re
        msg = str(e)
        masked = _re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", msg)
        diff_text = f"⚠️ Failed to fetch diff: {masked}"

    # Run AI analysis (this function already returns friendly messages on error)
    ai_review = analyze_code_diff(diff_text)
    # Normalize common API-key failure messages that may come from the
    # provider or the SDK: present a concise, actionable message to the UI.
    try:
        low_ai = (ai_review or "").lower()
        # Broad pattern check to catch different SDK/provider message shapes
        if (
            "invalid_api_key" in low_ai
            or "invalid api key" in low_ai
            or "incorrect api key" in low_ai
            or ("invalid" in low_ai and "api" in low_ai)
            or "unauthorized" in low_ai
            or "invalid request error" in low_ai
        ):
            ai_review = (
                "⚠️ OpenAI API error: Invalid or unauthorized API key. "
                "Please rotate your OpenAI API key at https://platform.openai.com/account/api-keys and set the new value in OPENAI_API_KEY, "
                "then restart the backend. (Do NOT paste keys into logs or public channels.)"
            )
    except Exception:
        # best-effort: leave ai_review as-is if normalization fails
        pass
    severity_counts = _simple_severity_counts_from_ai(ai_review)

    # Save PDF (best-effort). If PDF generation fails, record the error but do
    # not abort — we still want a history record.
    reports_dir = "/app/reports"
    os.makedirs(reports_dir, exist_ok=True)
    if not pdf_path:
        pdf_path = os.path.join(reports_dir, pdf_name)
    try:
        generate_review_pdf(pdf_path, repo_or_project, number, ai_review, diff_text)
    except Exception as e:
        import re as _re
        pdf_error = _re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", str(e))
        # If PDF failed, ensure pdf_path is empty so callers don't try to open it
        pdf_path = ""

    # Optionally post comment
    posted = False
    comment_body = f"**AI DevSecOps Assistant Review**\n\nSummary:\n{ai_review[:4000]}\n\n(Full report attached or available in pipeline.)"
    try:
        if post_comment:
            if platform == "github":
                posted = post_github_comment(repo_or_project, number, comment_body)
            else:
                posted = post_gitlab_comment(repo_or_project, number, comment_body)
    except Exception:
        posted = False

    # Save history and return (store a small diff snippet for viewing).
    diff_snippet = (diff_text or "")[:4000]
    try:
        history_id = history.save_analysis(platform, repo_or_project, number, ai_review, pdf_path or "", severity_counts, diff_snippet, posted)
    except Exception as e:
        # Log the full exception so we can debug why DB writes fail.
        logging.exception("Failed to save history record")
        import re as _re
        hist_err = _re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", str(e))
        return {"ai_review": ai_review, "pdf_path": pdf_path, "pdf_error": pdf_error, "diff_text": diff_text, "severity": severity_counts, "posted_comment": posted, "history_id": None, "history_error": hist_err}

    result = {"ai_review": ai_review, "pdf_path": pdf_path, "diff_text": diff_text, "severity": severity_counts, "posted_comment": posted, "history_id": history_id}
    if pdf_error:
        result["pdf_error"] = pdf_error
    return result
