import os
import requests
from typing import Optional
from app.utils import log_info, log_error


GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse a GitHub URL and return (owner, repo)."""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return parts[0], parts[1]


def get_headers() -> dict:
    """Return authorization headers if GITHUB_TOKEN is set."""
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_repo_metadata(owner: str, repo: str) -> dict:
    """Fetch repository metadata from GitHub API."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    log_info(f"Fetching metadata for {owner}/{repo}")
    response = requests.get(url, headers=get_headers(), timeout=15)
    if response.status_code == 404:
        raise ValueError(f"Repository '{owner}/{repo}' not found. Check the URL or make it public.")
    response.raise_for_status()
    data = response.json()
    return {
        "name": data.get("name", ""),
        "full_name": data.get("full_name", ""),
        "description": data.get("description", "No description provided."),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "language": data.get("language", "Unknown"),
        "topics": data.get("topics", []),
        "default_branch": data.get("default_branch", "main"),
        "created_at": data.get("created_at", ""),
        "updated_at": data.get("updated_at", ""),
        "open_issues": data.get("open_issues_count", 0),
        "license": data.get("license", {}).get("name", "No license") if data.get("license") else "No license",
        "homepage": data.get("homepage", ""),
        "size": data.get("size", 0),
    }


def fetch_readme(owner: str, repo: str, branch: str = "main") -> str:
    """Fetch README.md content from the repository."""
    branches_to_try = list(dict.fromkeys([branch, "main", "master", "develop", "dev", "trunk"]))
    filenames_to_try = [
        "README.md", "readme.md", "Readme.md", "README.MD",
        "README.rst", "readme.rst",
        "README.txt", "readme.txt",
        "README", "readme",
    ]

    for br in branches_to_try:
        for fname in filenames_to_try:
            url = f"{GITHUB_RAW_BASE}/{owner}/{repo}/{br}/{fname}"
            log_info(f"Trying README at {url}")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    log_info(f"Found README at {url}")
                    return response.text[:8000]  # Limit to 8000 chars to stay within LLM context
            except requests.RequestException:
                continue

    log_error("No README found in the repository.")
    return "No README found in this repository."


def fetch_repo_tree(owner: str, repo: str, branch: str = "main") -> list[dict]:
    """Fetch the repository file tree using GitHub API."""
    branches_to_try = list(dict.fromkeys([branch, "main", "master", "develop", "dev", "trunk"]))
    for br in branches_to_try:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{br}?recursive=1"
        log_info(f"Fetching tree for branch: {br}")
        try:
            response = requests.get(url, headers=get_headers(), timeout=15)
            if response.status_code == 200:
                data = response.json()
                tree = data.get("tree", [])
                return [item for item in tree if item.get("type") in ("blob", "tree")]
        except requests.RequestException:
            continue
    log_error("Could not fetch repository tree.")
    return []


def fetch_repo_languages(owner: str, repo: str) -> dict:
    """Fetch language breakdown from GitHub API."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
    log_info(f"Fetching languages for {owner}/{repo}")
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return {}


def fetch_all(github_url: str) -> dict:
    """Main entry point: fetch everything needed from a GitHub repo URL."""
    owner, repo = parse_github_url(github_url)
    metadata = fetch_repo_metadata(owner, repo)
    branch = metadata.get("default_branch", "main")
    readme = fetch_readme(owner, repo, branch)
    tree = fetch_repo_tree(owner, repo, branch)
    languages = fetch_repo_languages(owner, repo)
    return {
        "owner": owner,
        "repo": repo,
        "metadata": metadata,
        "readme": readme,
        "tree": tree,
        "languages": languages,
    }