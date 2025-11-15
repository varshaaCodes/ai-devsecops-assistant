import tempfile
import subprocess
import json

def calculate_security_score(issues: list) -> int:
    """
    Calculate a simple security score (0–100) based on issue severities.
    """
    if not issues or issues == ["No major issues detected ✅"]:
        return 100  # Perfect score if no issues

    severity_weights = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 10, "LOW": 5}
    total_deduction = 0

    for issue in issues:
        sev = str(issue.get("severity", "LOW")).upper()
        total_deduction += severity_weights.get(sev, 5)

    score = max(0, 100 - total_deduction)
    return score

def scan_code(code: str, language: str = "python") -> dict:
    """
    Scan code for vulnerabilities.
    - Uses Bandit for Python
    - Uses Semgrep for other languages
    - Returns severity breakdown + security score
    """
    try:
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "java": ".java",
            "go": ".go",
            "c": ".c",
        }
        suffix = ext_map.get(language.lower(), ".txt")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="w") as tmp:
            tmp.write(code)
            tmp.flush()
            tmp_filename = tmp.name

        issues = []

        # --- Python → Bandit ---
        if language.lower() == "python":
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", tmp_filename],
                capture_output=True,
                text=True
            )
            if result.stdout:
                bandit_report = json.loads(result.stdout)
                issues = [
                    {
                        "issue": i.get("issue_text"),
                        "severity": i.get("issue_severity"),
                        "confidence": i.get("issue_confidence"),
                        "line_number": i.get("line_number"),
                    }
                    for i in bandit_report.get("results", [])
                ]

        # --- Other Languages → Semgrep ---
        else:
            result = subprocess.run(
                ["semgrep", "--config=auto", "--json", tmp_filename],
                capture_output=True,
                text=True
            )
            if result.stdout:
                semgrep_report = json.loads(result.stdout)
                issues = [
                    {
                        "rule": i.get("check_id"),
                        "message": i.get("extra", {}).get("message"),
                        "severity": i.get("extra", {}).get("severity", "LOW"),
                        "line": i.get("start", {}).get("line"),
                    }
                    for i in semgrep_report.get("results", [])
                ]

        # If no issues found
        if not issues:
            issues = ["No major issues detected ✅"]

        # Compute score
        score = calculate_security_score(issues if isinstance(issues, list) else [])

        return {
            "language": language,
            "vulnerabilities_found": issues,
            "security_score": score
        }

    except Exception as e:
        return {"error": str(e)}
