# backend/app.py
import os
from fastapi import FastAPI, HTTPException, Query
from backend.repo_analyzer import analyze_pr_and_make_pdf
from backend.code_scanner import scan_repository  # if you have this already
from backend.ai_analysis import analyze_vulnerabilities  # optional repo-level AI summary

app = FastAPI(title="AI DevSecOps Assistant Backend")

@app.get("/")
def root():
    return {"message": "backend running"}

@app.get("/report")
def get_report():
    try:
        issues = scan_repository("./")
        summary = analyze_vulnerabilities(issues)
        return {"issues": issues, "ai_summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_pr")
def analyze_pr(repo: str = Query(..., description="user/repo or project id"), pr_number: int = Query(...), post_comment: bool = Query(False)):
    try:
        result = analyze_pr_and_make_pdf(platform="github", repo_or_project=repo, number=pr_number, post_comment=post_comment)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_mr")
def analyze_mr(project_id: str = Query(...), mr_id: int = Query(...), post_comment: bool = Query(False)):
    try:
        result = analyze_pr_and_make_pdf(platform="gitlab", repo_or_project=project_id, number=mr_id, post_comment=post_comment)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
