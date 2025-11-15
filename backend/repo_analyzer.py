# backend/repo_analyzer.py
import os
import requests
from fastapi import HTTPException
import json
import textwrap
from openai import OpenAI  # uses openai python package (new-style client)
from backend.report_generator import generate_review_pdf
from backend import history  # optional: requires history.py (below)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def fetch_github_pr(repo: str, pr_number: int) -> str:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {"Accept": "application/vnd.github.v3.diff"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=f"GitHub API error: {r.text}")
    return r.text

def fetch_gitlab_mr(project_id: str, mr_id: int) -> str:
    url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{mr_id}/changes"
    headers = {}
    if GITLAB_TOKEN:
        headers["PRIVATE-TOKEN"] = GITLAB_TOKEN
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=f"GitLab API error: {r.text}")
    data = r.json()
    diffs = []
    for ch in data.get("changes", []):
        filename = ch.get("new_path") or ch.get("old_path") or "unknown"
        diffs.append(f"*** FILE: {filename} ***\n{ch.get('diff','')}\n")
    return "\n".join(diffs)

def analyze_code_diff_with_ai(diff_text: str) -> str:
    if not client:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")
    prompt = f"""
You are a senior DevSecOps code reviewer. Analyze the diff below for security vulnerabilities, code quality, performance and possible fixes.
Provide: (1) Short summary, (2) Security findings, (3) Code quality issues, (4) Concrete fixes/snippets.

Diff (truncated to 12000 chars):
{diff_text[:12000]}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You are an expert security-minded code reviewer."},
                {"role":"user","content":prompt},
            ],
            max_tokens=1500,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {e}")

def _heuristic_severity_counts(ai_text: str):
    txt = ai_text.lower()
    return {
        "critical": txt.count("critical"),
        "high": txt.count("high"),
        "medium": txt.count("medium"),
        "low": txt.count("low"),
    }

def analyze_pr_and_make_pdf(platform: str, repo_or_project: str, number: int, post_comment: bool=False):
    # fetch diff
    if platform == "github":
        diff = fetch_github_pr(repo_or_project, number)
    else:
        diff = fetch_gitlab_mr(repo_or_project, number)

    ai_review = analyze_code_diff_with_ai(diff)
    severity = _heuristic_severity_counts(ai_review)

    # ensure reports dir
    reports_dir = "/app/reports"
    os.makedirs(reports_dir, exist_ok=True)
    slug = repo_or_project.replace("/", "_")
    pdf_name = f"{slug}_{platform}_{number}_review.pdf"
    pdf_path = os.path.join(reports_dir, pdf_name)
    generate_review_pdf(pdf_path, repo_or_project, number, ai_review, diff)

    # optionally post as comment (basic)
    posted = False
    try:
        if post_comment:
            body = f"**AI DevSecOps Review**\n\n{ai_review[:3000]}\n\n(Full PDF in CI/artifacts.)"
            if platform == "github" and GITHUB_TOKEN:
                url = f"https://api.github.com/repos/{repo_or_project}/issues/{number}/comments"
                r = requests.post(url, headers={"Authorization":f"token {GITHUB_TOKEN}"}, json={"body":body})
                posted = r.status_code in (200,201)
            elif platform == "gitlab" and GITLAB_TOKEN:
                url = f"https://gitlab.com/api/v4/projects/{repo_or_project}/merge_requests/{number}/notes"
                r = requests.post(url, headers={"PRIVATE-TOKEN":GITLAB_TOKEN}, data={"body":body})
                posted = r.status_code in (200,201)
    except Exception:
        posted = False

    # save history if history module present
    try:
        hid = history.save_analysis(platform, repo_or_project, number, ai_review, pdf_path, severity, diff[:4000], posted)
    except Exception:
        hid = None

    return {"ai_review": ai_review, "pdf_path": pdf_path, "diff_text": diff, "severity": severity, "posted_comment": posted, "history_id": hid}
