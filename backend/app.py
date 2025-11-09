# backend/app.py
from fastapi import FastAPI, HTTPException, Query
from backend.code_scanner import scan_repository
from backend.ai_analysis import analyze_vulnerabilities
from backend.report_generator import generate_review_pdf, generate_summary_pdf
import time
from backend.repo_analyzer import analyze_pr_and_make_pdf
from backend import history
import os
import traceback
import logging

app = FastAPI(title="AI DevSecOps Assistant Backend")


@app.on_event("startup")
def check_env():
    # Give an early, helpful warning if OPENAI_API_KEY is missing. If the
    # key is present but invalid, the analyzer will still surface a clear
    # message when it tries to call the API.
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logging.warning("OPENAI_API_KEY not set. AI analysis will be disabled until you set OPENAI_API_KEY in the environment.")
    else:
        if not key.startswith("sk-"):
            logging.info("OPENAI_API_KEY appears to be set but does not start with 'sk-'. Ensure this is a valid OpenAI key.")

@app.get("/")
def root():
    return {"message": "Backend running"}

@app.get("/report")
def get_report(generate_pdf: bool = False):
    try:
        issues = scan_repository("./")
        ai_summary = analyze_vulnerabilities(issues)
        result = {"issues": issues, "ai_summary": ai_summary}
        if generate_pdf:
            reports_dir = "/app/reports"
            os.makedirs(reports_dir, exist_ok=True)
            pdf_name = f"security_report_{int(time.time())}.pdf"
            pdf_path = os.path.join(reports_dir, pdf_name)
            try:
                generate_summary_pdf(pdf_path, ai_summary or "", issues)
                result["pdf_path"] = pdf_path
            except Exception as e:
                # don't fail the entire request if PDF generation fails
                result["pdf_error"] = str(e)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_pr")
def analyze_pr(repo: str = Query(...), pr_number: int = Query(...), post_comment: bool = Query(False)):
    try:
        result = analyze_pr_and_make_pdf("github", repo, pr_number, post_comment)
        return {"message": "GitHub PR analyzed", **result}
    except Exception as e:
        # Log full traceback to container logs for debugging, but return a
        # friendly JSON error to the caller. Mask common API key patterns.
        tb = traceback.format_exc()
        logging.error("analyze_pr exception: %s", tb)
        import re
        safe = re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", str(e))
        return {"message": "GitHub PR analyzed", "error": safe, "ai_review": f"⚠️ Analysis failed: {safe}", "history_id": None}

@app.post("/analyze_mr")
def analyze_mr(project_id: str = Query(...), mr_id: int = Query(...), post_comment: bool = Query(False)):
    try:
        result = analyze_pr_and_make_pdf("gitlab", project_id, mr_id, post_comment)
        return {"message": "GitLab MR analyzed", **result}
    except Exception as e:
        tb = traceback.format_exc()
        logging.error("analyze_mr exception: %s", tb)
        import re
        safe = re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", str(e))
        return {"message": "GitLab MR analyzed", "error": safe, "ai_review": f"⚠️ Analysis failed: {safe}", "history_id": None}

@app.get("/history")
def list_history(limit: int = 100):
    try:
        items = history.list_analyses(limit)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{analysis_id}")
def get_history(analysis_id: int):
    try:
        item = history.get_analysis(analysis_id)
        if not item:
            raise HTTPException(status_code=404, detail="Not found")
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
