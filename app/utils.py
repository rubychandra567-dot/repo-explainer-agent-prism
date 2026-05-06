import logging
import sys
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("repo-explainer")


def log_info(msg: str) -> None:
    logger.info(msg)


def log_error(msg: str) -> None:
    logger.error(msg)


def log_warning(msg: str) -> None:
    logger.warning(msg)


def format_number(n: int) -> str:
    """Format large numbers with K/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def truncate_text(text: str, max_chars: int = 4000) -> str:
    """Truncate text to max_chars, adding ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...content truncated for brevity...]"


def sanitize_url(url: str) -> str:
    """Clean up a GitHub URL."""
    url = url.strip()
    # Remove trailing slashes and .git suffix
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url


def build_prompt_context(parsed: dict) -> str:
    """Build a rich context string from parsed repo data for the LLM."""
    lines = []

    lines.append(f"## Repository: {parsed.get('full_name', parsed.get('name', 'Unknown'))}")
    lines.append(f"**Description:** {parsed.get('description', 'N/A')}")
    lines.append(f"**Stars:** {format_number(parsed.get('stars', 0))} | **Forks:** {format_number(parsed.get('forks', 0))} | **Open Issues:** {parsed.get('open_issues', 0)}")
    lines.append(f"**Primary Language:** {parsed.get('primary_language', 'Unknown')}")
    lines.append(f"**License:** {parsed.get('license', 'None')}")

    if parsed.get("topics"):
        lines.append(f"**Topics:** {', '.join(parsed['topics'])}")

    if parsed.get("homepage"):
        lines.append(f"**Homepage:** {parsed['homepage']}")

    # Language breakdown
    if parsed.get("api_languages"):
        lang_str = ", ".join([f"{lang} ({pct}%)" for lang, pct in list(parsed["api_languages"].items())[:6]])
        lines.append(f"\n### Language Breakdown:\n{lang_str}")
    elif parsed.get("detected_languages"):
        lang_str = ", ".join([f"{lang} ({count} files)" for lang, count in list(parsed["detected_languages"].items())[:6]])
        lines.append(f"\n### Detected Languages:\n{lang_str}")


    # Frameworks
    if parsed.get("frameworks"):
        lines.append(f"\n### Detected Frameworks/Tools:\n{', '.join(parsed['frameworks'])}")

    # --- Run Info Section ---
    run_info = parsed.get("run_info", {})
    if run_info:
        lines.append("\n### How to Run This Project:")
        if run_info.get("clone"):
            lines.append(f"- Clone: `{run_info['clone']}`")
        if run_info.get("install"):
            lines.append(f"- Install dependencies: `{run_info['install']}`")
        if run_info.get("env_setup"):
            lines.append(f"- Setup env: `{run_info['env_setup']}`")
        if run_info.get("primary"):
            lines.append(f"- Run command: `{run_info['primary']}`")

    # File stats
    counts = parsed.get("file_counts", {})
    if counts:
        lines.append(
            f"\n### Repository Size:\n"
            f"- Total files: {counts.get('total_files', 0)}\n"
            f"- Directories: {counts.get('total_dirs', 0)}\n"
            f"- Test files: {counts.get('test_files', 0)}\n"
            f"- Documentation files: {counts.get('doc_files', 0)}"
        )

    # Folder structure
    if parsed.get("folder_structure"):
        lines.append(f"\n### Folder Structure (top-level):\n```\n{parsed['folder_structure']}\n```")

    # Key files
    if parsed.get("key_files"):
        lines.append(f"\n### Key Files Detected:\n" + "\n".join([f"- {f}" for f in parsed["key_files"]]))

    # README
    if parsed.get("readme"):
        readme_snippet = truncate_text(parsed["readme"], max_chars=3000)
        lines.append(f"\n### README Content:\n{readme_snippet}")

    return "\n".join(lines)


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")