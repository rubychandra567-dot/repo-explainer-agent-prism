from collections import defaultdict
from app.utils import log_info


# Map of file extensions to language names
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/React",
    ".jsx": "JavaScript/React",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".scala": "Scala",
    ".r": "R",
    ".sh": "Shell",
    ".bash": "Bash",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".md": "Markdown",
    ".sql": "SQL",
    ".dockerfile": "Docker",
    ".tf": "Terraform",
    ".vue": "Vue.js",
    ".svelte": "Svelte",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".clj": "Clojure",
    ".hs": "Haskell",
    ".lua": "Lua",
    ".m": "MATLAB/Objective-C",
    ".pl": "Perl",
    ".ipynb": "Jupyter Notebook",
}

# Files that indicate frameworks or tools
FRAMEWORK_SIGNALS = {
    "package.json": "Node.js",
    "requirements.txt": "Python (pip)",
    "pyproject.toml": "Python (pyproject)",
    "Pipfile": "Python (pipenv)",
    "poetry.lock": "Poetry",
    "Cargo.toml": "Rust (Cargo)",
    "go.mod": "Go Modules",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "Gemfile": "Ruby (Bundler)",
    "composer.json": "PHP (Composer)",
    "Makefile": "Make build system",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    ".github/workflows": "GitHub Actions (CI/CD)",
    "kubernetes": "Kubernetes",
    "helm": "Helm Charts",
    "terraform": "Terraform IaC",
    "next.config.js": "Next.js",
    "next.config.ts": "Next.js",
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "angular.json": "Angular",
    "nuxt.config.js": "Nuxt.js",
    "svelte.config.js": "SvelteKit",
    "tailwind.config.js": "Tailwind CSS",
    "jest.config.js": "Jest (Testing)",
    "pytest.ini": "pytest",
    "setup.py": "Python (setuptools)",
    ".env.example": "dotenv config",
    "manage.py": "Django",
    "app.py": "Flask/FastAPI/Streamlit",
    "streamlit": "Streamlit",
    "fastapi": "FastAPI",
    "alembic.ini": "Alembic (DB migrations)",
}


def detect_languages_from_tree(tree: list[dict]) -> dict[str, int]:
    """Count file extensions to detect languages used."""
    lang_count: dict[str, int] = defaultdict(int)
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        dot_idx = path.rfind(".")
        if dot_idx != -1:
            ext = path[dot_idx:].lower()
            if ext in EXTENSION_LANGUAGE_MAP:
                lang_count[EXTENSION_LANGUAGE_MAP[ext]] += 1
    return dict(sorted(lang_count.items(), key=lambda x: x[1], reverse=True))


def detect_frameworks(tree: list[dict]) -> list[str]:
    """Detect frameworks and tools from filenames/directories in the tree."""
    paths = {item.get("path", "").lower() for item in tree}
    filenames = {p.split("/")[-1].lower() for p in paths}
    detected = []

    for signal, label in FRAMEWORK_SIGNALS.items():
        signal_lower = signal.lower()
        # Check exact filename match
        if signal_lower in filenames:
            if label not in detected:
                detected.append(label)
        # Check directory prefix match
        elif any(p.startswith(signal_lower + "/") or signal_lower in p for p in paths):
            if label not in detected:
                detected.append(label)

    return detected


def build_folder_structure(tree: list[dict], max_depth: int = 3) -> str:
    """Build a readable folder structure string from the tree."""
    dirs = set()
    files_at_root = []

    for item in tree:
        path = item.get("path", "")
        parts = path.split("/")

        if len(parts) == 1 and item.get("type") == "blob":
            files_at_root.append(path)
        else:
            if len(parts) <= max_depth:
                dirs.add("/".join(parts[:-1]) if item.get("type") == "blob" else path)

    structure_lines = []
    sorted_dirs = sorted(dirs)
    seen = set()

    for d in sorted_dirs:
        parts = d.split("/")
        for depth in range(len(parts)):
            prefix_key = "/".join(parts[:depth + 1])
            if prefix_key not in seen:
                seen.add(prefix_key)
                indent = "  " * depth
                structure_lines.append(f"{indent}📁 {parts[depth]}/")

    for f in sorted(files_at_root)[:20]:
        structure_lines.append(f"📄 {f}")

    return "\n".join(structure_lines) if structure_lines else "Could not determine structure."


def extract_key_files(tree: list[dict]) -> list[str]:
    """Return a list of key/important files from the tree."""
    important_names = {
        "main.py", "app.py", "index.js", "index.ts", "server.js", "server.py",
        "api.py", "routes.py", "models.py", "views.py", "urls.py",
        "manage.py", "settings.py", "config.py", "config.yaml", "config.json",
        "requirements.txt", "package.json", "Cargo.toml", "go.mod",
        "Dockerfile", "docker-compose.yml", ".github/workflows",
        "README.md", "setup.py", "pyproject.toml"
    }
    found = []
    for item in tree:
        path = item.get("path", "")
        filename = path.split("/")[-1]
        if filename in important_names or path in important_names:
            found.append(path)
    return found[:15]


def count_files_by_type(tree: list[dict]) -> dict[str, int]:
    """Count total files, dirs, test files, config files."""
    total_files = sum(1 for i in tree if i.get("type") == "blob")
    total_dirs = sum(1 for i in tree if i.get("type") == "tree")
    test_files = sum(1 for i in tree if "test" in i.get("path", "").lower() and i.get("type") == "blob")
    doc_files = sum(1 for i in tree if i.get("path", "").lower().endswith((".md", ".rst", ".txt")) and i.get("type") == "blob")
    return {
        "total_files": total_files,
        "total_dirs": total_dirs,
        "test_files": test_files,
        "doc_files": doc_files,
    }


def parse_repo_data(raw_data: dict) -> dict:
    """Master parser: extract all insights from raw fetched data."""
    log_info("Parsing repository data...")
    tree = raw_data.get("tree", [])
    metadata = raw_data.get("metadata", {})
    languages_api = raw_data.get("languages", {})

    lang_from_tree = detect_languages_from_tree(tree)
    frameworks = detect_frameworks(tree)
    folder_structure = build_folder_structure(tree)
    key_files = extract_key_files(tree)
    file_counts = count_files_by_type(tree)

    # Merge API languages with tree-detected languages
    if languages_api:
        total_bytes = sum(languages_api.values()) or 1
        api_languages = {lang: round((bytes_ / total_bytes) * 100, 1) for lang, bytes_ in languages_api.items()}
    else:
        api_languages = {}
    
    # Detect run commands and setup info
    run_info = detect_run_commands(tree, raw_data.get("readme", ""), repo_url=metadata.get("html_url", ""))

    return {
        "name": metadata.get("name", ""),
        "full_name": metadata.get("full_name", ""),
        "description": metadata.get("description", ""),
        "stars": metadata.get("stars", 0),
        "forks": metadata.get("forks", 0),
        "primary_language": metadata.get("language", "Unknown"),
        "topics": metadata.get("topics", []),
        "license": metadata.get("license", ""),
        "homepage": metadata.get("homepage", ""),
        "open_issues": metadata.get("open_issues", 0),
        "size_kb": metadata.get("size", 0),
        "api_languages": api_languages,
        "detected_languages": lang_from_tree,
        "frameworks": frameworks,
        "folder_structure": folder_structure,
        "key_files": key_files,
        "file_counts": file_counts,
        "readme": raw_data.get("readme", ""),
        "run_info": run_info,
    }


def detect_run_commands(tree, readme, repo_url=None):
    """
    Detects the main run command and setup steps from the repo tree and README.
    Returns dict: {primary, install, clone, env_setup}
    """
    import re
    # Patterns to search for
    run_patterns = [
        r"python +[\w./-]+", r"streamlit run +[\w./-]+", r"npm start", r"npm run dev",
        r"uvicorn +[\w.:_-]+", r"flask run", r"go run +[\w./-]+", r"cargo run", r"node +[\w./-]+", r"yarn (start|dev)"
    ]
    install_cmd = None
    env_setup = None
    primary = None
    # Detect install command
    filenames = {item.get("path", "").lower() for item in tree}
    if "requirements.txt" in filenames:
        install_cmd = "pip install -r requirements.txt"
    elif "package.json" in filenames:
        install_cmd = "npm install"
    elif "cargo.toml" in filenames:
        install_cmd = "cargo build"
    elif "go.mod" in filenames:
        install_cmd = "go mod tidy"
    # Detect env setup
    if ".env.example" in filenames:
        env_setup = "cp .env.example .env"
    # Detect primary run command from key files
    key_files = ["manage.py", "app.py", "main.py", "index.js", "server.js", "Makefile"]
    for f in key_files:
        if f in filenames:
            if f.endswith(".py"):
                primary = f"python {f}"
                break
            elif f == "index.js" or f == "server.js":
                primary = f"node {f}"
                break
            elif f == "Makefile":
                primary = "make run"
                break
    # Scan README for code blocks with run commands
    code_blocks = re.findall(r"```[a-zA-Z0-9]*\n(.*?)\n```", readme, re.DOTALL)
    for block in code_blocks:
        for pat in run_patterns:
            m = re.search(pat, block)
            if m:
                primary = m.group(0)
                break
        if primary:
            break
    # Fallback: scan README for inline run commands
    if not primary:
        for pat in run_patterns:
            m = re.search(pat, readme)
            if m:
                primary = m.group(0)
                break
    # Compose clone command
    clone = f"git clone {repo_url}" if repo_url else "git clone <url>"
    return {
        "primary": primary or "",
        "install": install_cmd or "",
        "clone": clone,
        "env_setup": env_setup or "",
    }