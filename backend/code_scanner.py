import subprocess
import json
import tempfile
import os

def scan_repository(repo_path="./"):
    all_issues = []

    # --- Run Bandit ---
    try:
        bandit_result = subprocess.run(
            ["bandit", "-r", repo_path, "-f", "json"],
            capture_output=True,
            text=True
        )
        bandit_output = json.loads(bandit_result.stdout)
        for issue in bandit_output.get("results", []):
            all_issues.append({
                "tool": "bandit",
                "file": issue.get("filename"),
                "line": issue.get("line_number"),
                "issue": issue.get("issue_text"),
                "severity": issue.get("issue_severity"),
                "confidence": issue.get("issue_confidence")
            })
    except Exception as e:
        all_issues.append({"tool": "bandit", "error": str(e)})

    # --- Run Semgrep ---
    try:
        semgrep_result = subprocess.run(
            ["semgrep", "--json", "--config", "auto", repo_path],
            capture_output=True,
            text=True
        )
        semgrep_output = json.loads(semgrep_result.stdout)
        for result in semgrep_output.get("results", []):
            all_issues.append({
                "tool": "semgrep",
                "file": result.get("path"),
                "line": result.get("start", {}).get("line"),
                "issue": result.get("extra", {}).get("message"),
                "severity": result.get("extra", {}).get("severity")
            })
    except Exception as e:
        all_issues.append({"tool": "semgrep", "error": str(e)})

    return all_issues
