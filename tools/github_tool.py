import urllib.request
import json
from utils.logger import logger

def _get(url: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PersonalAgent/1.0",
            "Accept": "application/vnd.github+json",
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())

def get_github_repo_info(owner: str, repo: str) -> str:
    """Get basic info about a GitHub repository.

    Args:
        owner: GitHub username or organization (e.g. 'torvalds').
        repo: Repository name (e.g. 'linux').

    Returns:
        Repo description, stars, forks, open issues, and latest activity.
    """
    try:
        data = _get(f"https://api.github.com/repos/{owner}/{repo}")
        return (
            f"📦 {data['full_name']}\n\n"
            f"📝 {data.get('description', 'No description')}\n\n"
            f"⭐ Stars: {data['stargazers_count']:,}\n"
            f"🍴 Forks: {data['forks_count']:,}\n"
            f"🐛 Open issues: {data['open_issues_count']:,}\n"
            f"🌿 Default branch: {data['default_branch']}\n"
            f"🔤 Language: {data.get('language', 'N/A')}\n"
            f"📅 Last push: {data['pushed_at'][:10]}\n"
            f"🔗 {data['html_url']}"
        )
    except Exception as e:
        return f"Could not fetch repo {owner}/{repo}: {e}"

def get_github_recent_commits(owner: str, repo: str, count: int = 7) -> str:
    """Get the most recent commits from a GitHub repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        count: Number of recent commits to return (default 7).

    Returns:
        List of recent commits with messages, authors, and dates.
    """
    try:
        commits = _get(f"https://api.github.com/repos/{owner}/{repo}/commits?per_page={count}")
        out = f"📋 Last {len(commits)} commits in {owner}/{repo}:\n\n"
        for c in commits:
            sha = c["sha"][:7]
            msg = c["commit"]["message"].split("\n")[0][:80]
            author = c["commit"]["author"]["name"]
            date = c["commit"]["author"]["date"][:10]
            out += f"`{sha}` {date} — {msg} ({author})\n"
        return out
    except Exception as e:
        return f"Could not fetch commits for {owner}/{repo}: {e}"

def get_github_open_issues(owner: str, repo: str, count: int = 10) -> str:
    """Get open issues from a GitHub repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        count: Number of issues to return (default 10).

    Returns:
        List of open issues with titles, labels, and links.
    """
    try:
        issues = _get(f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&per_page={count}")
        if not issues:
            return f"No open issues in {owner}/{repo}."
        out = f"🐛 Open issues in {owner}/{repo}:\n\n"
        for i in issues:
            if "pull_request" in i:
                continue  # skip PRs
            labels = ", ".join(l["name"] for l in i.get("labels", [])) or "no labels"
            out += f"#{i['number']} {i['title']}\n   🏷️ {labels}\n   🔗 {i['html_url']}\n\n"
        return out
    except Exception as e:
        return f"Could not fetch issues for {owner}/{repo}: {e}"
