"""
github_utils.py
Fetches the latest commit for a given public GitHub repo URL.
"""

import re
import requests

GITHUB_API = "https://api.github.com"


def parse_owner_repo(repo_url: str):
    """
    Extracts (owner, repo) from a GitHub URL like:
    https://github.com/owner/repo
    https://github.com/owner/repo.git
    https://github.com/owner/repo/
    """
    repo_url = repo_url.strip().rstrip("/")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(\.git)?$", repo_url)
    if not match:
        raise ValueError(f"Could not parse GitHub owner/repo from URL: {repo_url}")
    return match.group(1), match.group(2)


def get_latest_commit(repo_url: str, github_token: str | None = None):
    """
    Returns a dict with details of the latest commit on the repo's default branch.
    Raises an exception with a readable message on failure (private repo, bad URL, rate limit, etc.)
    """
    owner, repo = parse_owner_repo(repo_url)

    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    # First get default branch
    repo_resp = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers, timeout=15)
    if repo_resp.status_code == 404:
        raise ValueError(f"Repo not found or private: {owner}/{repo}")
    repo_resp.raise_for_status()
    default_branch = repo_resp.json().get("default_branch", "main")

    # Get latest commit on default branch
    commits_resp = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/commits",
        headers=headers,
        params={"sha": default_branch, "per_page": 1},
        timeout=15,
    )
    commits_resp.raise_for_status()
    commits = commits_resp.json()

    if not commits:
        return {
            "owner": owner,
            "repo": repo,
            "has_commits": False,
        }

    commit = commits[0]
    commit_info = commit.get("commit", {})
    author_info = commit_info.get("author", {})

    return {
        "owner": owner,
        "repo": repo,
        "has_commits": True,
        "sha": commit.get("sha", "")[:7],
        "author_name": author_info.get("name", "Unknown"),
        "date": author_info.get("date", "Unknown"),
        "message": commit_info.get("message", "").strip(),
        "url": commit.get("html_url", ""),
    }
