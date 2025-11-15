# dashboard/app.py
import streamlit as st
import requests
import os
import html
from pathlib import Path
import pandas as pd

BASE_URL = os.getenv("BASE_URL", "http://backend:8000")
REPORTS_DIR = "/app/repora# dashboard/app.py
import streamlit as st
import requests
import os
import html
from pathlib import Path
import pandas as pd

BASE_URL = os.getenv("BASE_URL", "http://backend:8000")
REPORTS_DIR = "/app/reports"

st.set_page_config(page_title="AI DevSecOps Assistant", layout="wide")
st.title("🛡️ AI DevSecOps Assistant Dashboard")

tabs = st.tabs(["Local Scan", "PR/MR Analysis", "History"])

# Local scan (keeps previous behavior)
with tabs[0]:
    st.header("Local Security Scan")
    if st.button("Run local scan"):
        try:
            r = requests.get(f"{BASE_URL}/report", timeout=60)
            data = r.json()
            st.success("Scan completed")
            st.json(data.get("issues", {}))
            st.markdown("### AI Summary")
            st.write(data.get("ai_summary", "No summary"))
        except Exception as e:
            st.error(f"Error: {e}")

# PR/MR Analysis
with tabs[1]:
    st.header("PR / MR Analysis")
    platform = st.selectbox("Platform", ["GitHub", "GitLab"])
    post_comment = st.checkbox("Post AI review as comment on PR/MR (requires token)", value=False)

    if platform == "GitHub":
        repo = st.text_input("GitHub repo (user/repo)")
        pr_num = st.number_input("Pull Request number", min_value=1, step=1)
        if st.button("Analyze GitHub PR"):
            if not repo:
                st.warning("Enter repo")
            else:
                with st.spinner("Analyzing PR..."):
                    try:
                        r = requests.post(f"{BASE_URL}/analyze_pr", params={"repo":repo, "pr_number":pr_num, "post_comment": post_comment}, timeout=180)
                        data = r.json()
                        st.success("Analysis complete")
                        st.markdown("### AI Review")
                        st.write(data.get("ai_review",""))
                        # show severity
                        if data.get("severity"):
                            df = pd.DataFrame.from_dict(data["severity"], orient="index", columns=["count"])
                            st.bar_chart(df)
                        # highlight diff
                        diff = data.get("diff_text","")
                        if diff:
                            lines = diff.splitlines()
                            html_lines = []
                            for ln in lines:
                                esc = html.escape(ln)
                                if ln.startswith("+") and not ln.startswith("+++"):
                                    html_lines.append(f'<div style="background:#e6ffed;padding:2px;border-left:4px solid #2ecc71;">{esc}</div>')
                                elif ln.startswith("-") and not ln.startswith("---"):
                                    html_lines.append(f'<div style="background:#ffecec;padding:2px;border-left:4px solid #e74c3c;">{esc}</div>')
                                elif ln.startswith("@@"):
                                    html_lines.append(f'<div style="background:#f0f3f5;padding:2px;border-left:4px solid #3498db;font-weight:bold;">{esc}</div>')
                                else:
                                    html_lines.append(f'<div style="padding:2px;font-family:monospace;">{esc}</div>')
                            st.markdown("<div style='font-family:monospace;line-height:1.25;'>" + "\n".join(html_lines[:2000]) + "</div>", unsafe_allow_html=True)
                        pdf_path = data.get("pdf_path","")
                        if pdf_path and Path(pdf_path).exists():
                            with open(pdf_path,"rb") as f:
                                st.download_button("Download PDF", data=f.read(), file_name=Path(pdf_path).name, mime="application/pdf")
                        else:
                            st.info("PDF not found in reports (may still be generating).")
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        proj = st.text_input("GitLab project id (numeric)")
        mr_num = st.number_input("Merge Request number", min_value=1, step=1)
        if st.button("Analyze GitLab MR"):
            if not proj:
                st.warning("Enter project id")
            else:
                with st.spinner("Analyzing MR..."):
                    try:
                        r = requests.post(f"{BASE_URL}/analyze_mr", params={"project_id":proj, "mr_id":mr_num, "post_comment": post_comment}, timeout=180)
                        data = r.json()
                        st.success("Analysis complete")
                        st.markdown("### AI Review")
                        st.write(data.get("ai_review",""))
                        if data.get("severity"):
                            df = pd.DataFrame.from_dict(data["severity"], orient="index", columns=["count"])
                            st.bar_chart(df)
                        diff = data.get("diff_text","")
                        if diff:
                            lines = diff.splitlines()
                            html_lines=[]
                            for ln in lines:
                                esc = html.escape(ln)
                                if ln.startswith("+") and not ln.startswith("+++"):
                                    html_lines.append(f'<div style="background:#e6ffed;padding:2px;border-left:4px solid #2ecc71;">{esc}</div>')
                                elif ln.startswith("-") and not ln.startswith("---"):
                                    html_lines.append(f'<div style="background:#ffecec;padding:2px;border-left:4px solid #e74c3c;">{esc}</div>')
                                elif ln.startswith("@@"):
                                    html_lines.append(f'<div style="background:#f0f3f5;padding:2px;border-left:4px solid #3498db;font-weight:bold;">{esc}</div>')
                                else:
                                    html_lines.append(f'<div style="padding:2px;font-family:monospace;">{esc}</div>')
                            st.markdown("<div style='font-family:monospace;line-height:1.25;'>" + "\n".join(html_lines[:2000]) + "</div>", unsafe_allow_html=True)
                        pdf_path = data.get("pdf_path","")
                        if pdf_path and Path(pdf_path).exists():
                            with open(pdf_path,"rb") as f:
                                st.download_button("Download PDF", data=f.read(), file_name=Path(pdf_path).name, mime="application/pdf")
                        else:
                            st.info("PDF not found.")
                    except Exception as e:
                        st.error(f"Error: {e}")

# History tab (simple)
with tabs[2]:
    st.header("History")
    try:
        r = requests.get(f"{BASE_URL}/history", timeout=20)
        items = r.json().get("items", [])
        if not items:
            st.info("No history yet.")
        else:
            st.dataframe(pd.DataFrame(items))
    except Exception as e:
        st.error(f"Could not fetch history: {e}")
ts"

st.set_page_config(page_title="AI DevSecOps Assistant", layout="wide")
st.title("🛡️ AI DevSecOps Assistant Dashboard")

tab_scan, tab_pr, tab_history = st.tabs(["🧠 Local Security Scan", "🌐 PR/MR AI Analysis", "📚 History"])

# ---------------- Tab 1: Local Scan ----------------
with tab_scan:
    st.subheader("🔍 Run Local Security Scan")
    if st.button("Start Scan"):
        with st.spinner("Scanning repository..."):
            try:
                r = requests.get(f"{BASE_URL}/report")
                data = r.json()
                st.success("✅ Scan Completed")
                st.json(data.get("issues", {}))
                st.markdown("### 🤖 AI Summary")
                st.write(data.get("ai_summary", "No summary"))
            except Exception as e:
                st.error(f"Backend error: {e}")

# ---------------- Tab 2: PR/MR Analysis ----------------
with tab_pr:
    st.subheader("🌐 Analyze Pull / Merge Requests")
    platform = st.selectbox("Platform", ["GitHub", "GitLab"])
    post_comment = st.checkbox("Post AI review as comment on PR/MR (requires token)", value=False)

    if platform == "GitHub":
        repo = st.text_input("GitHub repo (user/repo)")
        pr_num = st.number_input("PR number", min_value=1, step=1)
        if st.button("Analyze GitHub PR"):
            if not repo:
                st.warning("Enter repo")
            else:
                with st.spinner("Analyzing..."):
                    try:
                        r = requests.post(f"{BASE_URL}/analyze_pr", params={"repo": repo, "pr_number": pr_num, "post_comment": post_comment}, timeout=120)
                        data = r.json()
                        st.success("Analysis complete")
                        st.markdown("### 🧠 AI Review")
                        st.write(data.get("ai_review", "No review"))
                        # show severity
                        severity = data.get("severity", {})
                        if severity:
                            st.markdown("### 📊 Severity distribution (heuristic)")
                            df = pd.DataFrame(list(severity.items()), columns=["severity","count"]).set_index("severity")
                            st.bar_chart(df)
                        # show diff highlighted
                        diff_text = data.get("diff_text", "") or data.get("diff", "")
                        if diff_text:
                            st.markdown("### 🔎 Diff (highlighted)")
                            lines = diff_text.splitlines()
                            html_lines = []
                            for ln in lines:
                                esc = html.escape(ln)
                                if ln.startswith("+") and not ln.startswith("+++"):
                                    html_lines.append(f'<div style="background:#e6ffed;padding:2px 4px;border-left:4px solid #2ecc71;">{esc}</div>')
                                elif ln.startswith("-") and not ln.startswith("---"):
                                    html_lines.append(f'<div style="background:#ffecec;padding:2px 4px;border-left:4px solid #e74c3c;">{esc}</div>')
                                elif ln.startswith("@@"):
                                    html_lines.append(f'<div style="background:#f0f3f5;padding:2px 4px;border-left:4px solid #3498db;font-weight:bold;">{esc}</div>')
                                else:
                                    html_lines.append(f'<div style="padding:2px 4px;font-family:monospace;">{esc}</div>')
                            st.markdown("<div style='font-family:monospace;line-height:1.25;'>" + "\n".join(html_lines[:2000]) + "</div>", unsafe_allow_html=True)
                        pdf_path = data.get("pdf_path", "")
                        if pdf_path and Path(pdf_path).exists():
                            with open(pdf_path, "rb") as f:
                                st.download_button("📄 Download AI Review PDF", data=f.read(), file_name=Path(pdf_path).name, mime="application/pdf")
                        else:
                            st.info("PDF may still be generating or not found.")
                        if data.get("posted_comment"):
                            st.success("✅ Posted AI review as a comment on PR")
                        st.write(f"History ID: {data.get('history_id')}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    else:  # GitLab
        project_id = st.text_input("GitLab project id (numeric)")
        mr_id = st.number_input("MR number", min_value=1, step=1)
        if st.button("Analyze GitLab MR"):
            if not project_id:
                st.warning("Enter project id")
            else:
                with st.spinner("Analyzing..."):
                    try:
                        r = requests.post(f"{BASE_URL}/analyze_mr", params={"project_id": project_id, "mr_id": mr_id, "post_comment": post_comment}, timeout=120)
                        data = r.json()
                        st.success("Analysis complete")
                        st.markdown("### 🧠 AI Review")
                        st.write(data.get("ai_review", "No review"))
                        severity = data.get("severity", {})
                        if severity:
                            st.markdown("### 📊 Severity distribution (heuristic)")
                            df = pd.DataFrame(list(severity.items()), columns=["severity","count"]).set_index("severity")
                            st.bar_chart(df)
                        diff_text = data.get("diff_text", "") or data.get("diff", "")
                        if diff_text:
                            lines = diff_text.splitlines()
                            html_lines = []
                            for ln in lines:
                                esc = html.escape(ln)
                                if ln.startswith("+") and not ln.startswith("+++"):
                                    html_lines.append(f'<div style="background:#e6ffed;padding:2px 4px;border-left:4px solid #2ecc71;">{esc}</div>')
                                elif ln.startswith("-") and not ln.startswith("---"):
                                    html_lines.append(f'<div style="background:#ffecec;padding:2px 4px;border-left:4px solid #e74c3c;">{esc}</div>')
                                elif ln.startswith("@@"):
                                    html_lines.append(f'<div style="background:#f0f3f5;padding:2px 4px;border-left:4px solid #3498db;font-weight:bold;">{esc}</div>')
                                else:
                                    html_lines.append(f'<div style="padding:2px 4px;font-family:monospace;">{esc}</div>')
                            st.markdown("<div style='font-family:monospace;line-height:1.25;'>" + "\n".join(html_lines[:2000]) + "</div>", unsafe_allow_html=True)
                        pdf_path = data.get("pdf_path", "")
                        if pdf_path and Path(pdf_path).exists():
                            with open(pdf_path, "rb") as f:
                                st.download_button("📄 Download AI Review PDF", data=f.read(), file_name=Path(pdf_path).name, mime="application/pdf")
                        else:
                            st.info("PDF may still be generating or not found.")
                        if data.get("posted_comment"):
                            st.success("✅ Posted AI review as a comment on MR")
                        st.write(f"History ID: {data.get('history_id')}")
                    except Exception as e:
                        st.error(f"Error: {e}")

# ---------------- Tab 3: History ----------------
with tab_history:
    st.subheader("📚 Analysis History")
    try:
        r = requests.get(f"{BASE_URL}/history", params={"limit": 200})
        items = r.json().get("items", [])
        if not items:
            st.info("No analysis history yet.")
        else:
            df = []
            for it in items:
                df.append({
                    "id": it["id"],
                    "platform": it["platform"],
                    "repo_or_project": it["repo_or_project"],
                    "number": it["number"],
                    "posted_comment": it["posted_comment"],
                    "created_at": it["created_at"]
                })
            hist_df = pd.DataFrame(df)
            st.dataframe(hist_df)

            st.markdown("### View analysis details")
            aid = st.number_input("Enter history id to view", min_value=1, step=1)
            if st.button("Get Analysis"):
                detail_resp = requests.get(f"{BASE_URL}/history/{aid}")
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    st.markdown("#### AI Review")
                    st.write(detail.get("ai_review"))
                    st.markdown("#### Severity (heuristic)")
                    sev = detail.get("severity", {})
                    if sev:
                        s_df = pd.DataFrame(list(sev.items()), columns=["severity","count"]).set_index("severity")
                        st.bar_chart(s_df)
                    st.markdown("#### Diff Snippet")
                    st.code(detail.get("diff_snippet", "")[:2000], language=None)
                    pdfp = detail.get("pdf_path", "")
                    if pdfp and Path(pdfp).exists():
                        with open(pdfp, "rb") as f:
                            st.download_button("📄 Download PDF", data=f.read(), file_name=Path(pdfp).name, mime="application/pdf")
                    else:
                        st.info("PDF not available locally.")
                else:
                    st.error("Analysis not found.")
    except Exception as e:
        st.error(f"Failed to fetch history: {e}")
