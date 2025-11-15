import os
import tempfile
import re
import git
from openai import OpenAI


def analyze_pr(pr_url: str):
    # --- GitHub/GitLab URL parsing ---
    match = re.search(r"(github|gitlab)\.com/([^/]+)/([^/]+)/(?:pull|merge_requests)/(\d+)", pr_url)
    if not match:
        return {"error": "Invalid PR/MR URL format. Please provide a valid GitHub or GitLab URL."}

    platform, user, repo, pr_number = match.groups()
    clone_url = f"https://{platform}.com/{user}/{repo}.git"

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, repo)
        git.Repo.clone_from(clone_url, repo_path)

        if platform == "github":
            os.system(f"cd {repo_path} && git fetch origin pull/{pr_number}/head:pr-{pr_number}")
        else:  # GitLab
            os.system(f"cd {repo_path} && git fetch origin merge-requests/{pr_number}/head:mr-{pr_number}")

        os.system(f"cd {repo_path} && git checkout pr-{pr_number} || git checkout mr-{pr_number}")

        # --- Run Bandit scan ---
        os.system(f"cd {repo_path} && bandit -r . -f json -o bandit_results.json")

        try:
            with open(os.path.join(repo_path, "bandit_results.json")) as f:
                bandit_data = f.read()
        except Exception as e:
            bandit_data = f"Bandit results unavailable: {str(e)}"

        # --- AI Analysis ---
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            ai_summary = "⚠️ OpenAI API key not configured. Set OPENAI_API_KEY in environment to enable AI analysis."
        else:
            try:
                client = OpenAI(api_key=api_key)
                ai_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a senior DevSecOps engineer analyzing code quality and security."},
                        {"role": "user", "content": f"Here are the Bandit scan results for a PR:\n{bandit_data}\n\nProvide a detailed, human-readable summary of vulnerabilities, their impact, and improvement suggestions."}
                    ],
                )
                ai_summary = ai_response.choices[0].message.content
            except Exception as e:
                # Mask any sk-... API keys that might appear in error text
                text = str(e)
                masked = re.sub(r"sk-[A-Za-z0-9\._-]+", "[REDACTED_API_KEY]", text)
                ai_summary = f"⚠️ AI analysis failed: {masked}"

        return {
            "repo": f"{user}/{repo}",
            "pr_number": pr_number,
            "bandit_results": bandit_data,
            "ai_summary": ai_summary
        }
