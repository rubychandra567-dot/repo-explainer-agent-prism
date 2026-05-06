#!/usr/bin/env python3
"""
GitHub Repo Explainer Agent — CLI Entry Point

Usage:
    python main.py https://github.com/owner/repo
    python main.py https://github.com/owner/repo --model llama3-8b-8192
    python main.py --ui   # Launch Streamlit UI
"""

import argparse
import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def run_cli(github_url: str, model: str) -> None:
    """Run the full pipeline in CLI mode and print the explanation."""
    from app.github_fetcher import fetch_all
    from app.parser import parse_repo_data
    from app.agent import explain_repo
    from app.utils import log_info, timestamp

    print("=" * 70)
    print("  🔍 GitHub Repo Explainer Agent")
    print(f"  ⏱  Started at {timestamp()}")
    print("=" * 70)
    print(f"\n📦 Repository : {github_url}")
    print(f"🤖 Model      : {model}\n")

    # Step 1: Fetch
    print("─" * 40)
    print("Step 1/3 — Fetching repository data...")
    print("─" * 40)
    try:
        raw_data = fetch_all(github_url)
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to fetch repository: {e}")
        sys.exit(1)

    meta = raw_data.get("metadata", {})
    print(f"✅ {meta.get('full_name', '')} — ⭐ {meta.get('stars', 0)} stars | 🍴 {meta.get('forks', 0)} forks")
    print(f"   {meta.get('description', 'No description')[:120]}")
    print(f"   Files indexed: {len(raw_data.get('tree', []))}")

    # Step 2: Parse
    print("\n─" * 40)
    print("Step 2/3 — Parsing repository structure...")
    print("─" * 40)
    try:
        parsed = parse_repo_data(raw_data)
    except Exception as e:
        print(f"\n❌ Parse error: {e}")
        sys.exit(1)

    if parsed.get("frameworks"):
        print(f"✅ Frameworks detected: {', '.join(parsed['frameworks'][:5])}")
    if parsed.get("api_languages"):
        langs = list(parsed["api_languages"].keys())[:5]
        print(f"✅ Languages detected: {', '.join(langs)}")

    # Step 3: LLM Explanation
    print("\n─" * 40)
    print(f"Step 3/3 — Generating AI explanation ({model})...")
    print("─" * 40)

    if not os.getenv("GROQ_API_KEY"):
        print("\n❌ GROQ_API_KEY is not set.")
        print("   Add it to your .env file: GROQ_API_KEY=gsk_...")
        sys.exit(1)

    try:
        explanation = explain_repo(parsed, model=model)
    except RuntimeError as e:
        print(f"\n❌ LLM Error: {e}")
        sys.exit(1)

    # Output
    print("\n" + "=" * 70)
    print("  📋 EXPLANATION")
    print("=" * 70 + "\n")
    print(explanation)
    print("\n" + "=" * 70)
    print(f"  ✅ Done at {timestamp()}")
    print("=" * 70)


def launch_ui() -> None:
    """Launch the Streamlit UI."""
    import subprocess
    from pathlib import Path

    ui_path = Path(__file__).parent / "ui" / "streamlit_app.py"
    if not ui_path.exists():
        print(f"❌ UI file not found: {ui_path}")
        sys.exit(1)

    print("🚀 Launching Streamlit UI...")
    print(f"   File: {ui_path}")
    print("   Open http://localhost:8501 in your browser.\n")

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ui_path)],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Repo Explainer Agent — powered by Groq + LLaMA 3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py https://github.com/tiangolo/fastapi
  python main.py https://github.com/pallets/flask --model llama3-8b-8192
  python main.py --ui
        """,
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="GitHub repository URL to analyze",
    )
    parser.add_argument(
        "--model",
        default="llama-3.3-70b-versatile",
        choices=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        help="Groq model to use (default: llama-3.3-70b-versatile)",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the Streamlit web UI instead of CLI mode",
    )

    args = parser.parse_args()

    if args.ui:
        launch_ui()
    elif args.url:
        run_cli(args.url, args.model)
    else:
        parser.print_help()
        print("\n💡 Tip: Use --ui to launch the web interface, or pass a GitHub URL to analyze in the terminal.")
        sys.exit(0)


if __name__ == "__main__":
    main()