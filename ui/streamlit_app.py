
# ...existing code...

import os
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Add project root to path so imports work regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from app.github_fetcher import fetch_all, parse_github_url
from app.parser import parse_repo_data
from app.agent import explain_repo_streaming


# ─────────────────────────────────────────────
#  Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="GitHub Repo Explainer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
#  Custom CSS
# ─────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Syne', sans-serif;
    }

    .main-header {
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 2.8rem;
        background: linear-gradient(135deg, #00d4ff, #7b2fff, #ff2d78);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
        margin-bottom: 0.2rem;
    }

    .sub-header {
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    .metric-card {
        background: linear-gradient(135deg, #0f172a, #1e293b);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
    }

    .metric-label {
        color: #64748b;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    .metric-value {
        color: #f1f5f9;
        font-size: 1.5rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
    }

    .explanation-box {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 16px;
        padding: 2rem;
        line-height: 1.8;
        color: #e6edf3;
        font-size: 0.95rem;
    }

    .tag-pill {
        display: inline-block;
        background: rgba(123, 47, 255, 0.15);
        border: 1px solid rgba(123, 47, 255, 0.4);
        border-radius: 999px;
        padding: 0.2rem 0.8rem;
        font-size: 0.75rem;
        color: #a78bfa;
        font-family: 'JetBrains Mono', monospace;
        margin: 0.15rem;
    }

    .stTextInput > div > div > input {
        font-family: 'JetBrains Mono', monospace;
        background: #0d1117;
        border: 1px solid #30363d;
        color: #e6edf3;
        border-radius: 10px;
        font-size: 0.9rem;
    }

    .stButton > button {
        background: linear-gradient(135deg, #7b2fff, #ff2d78);
        color: white;
        border: none;
        border-radius: 10px;
        font-family: 'Syne', sans-serif;
        font-weight: 700;
        font-size: 1rem;
        padding: 0.6rem 2rem;
        width: 100%;
        transition: opacity 0.2s;
    }

    .stButton > button:hover {
        opacity: 0.88;
    }

    .sidebar-title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #64748b;
        margin-bottom: 0.5rem;
    }

    code {
        font-family: 'JetBrains Mono', monospace !important;
        background: #161b22 !important;
        border-radius: 4px;
        padding: 0.1rem 0.4rem;
    }

    .stSpinner > div {
        border-top-color: #7b2fff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")

    groq_key = st.text_input(
        "Groq API Key",
        type="password",
        value=os.getenv("GROQ_API_KEY", ""),
        placeholder="gsk_...",
        help="Get your free key at console.groq.com",
    )
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key

    github_token = st.text_input(
        "GitHub Token (optional)",
        type="password",
        value=os.getenv("GITHUB_TOKEN", ""),
        placeholder="ghp_...",
        help="Increases GitHub API rate limit from 60 to 5000 req/hr",
    )
    if github_token:
        os.environ["GITHUB_TOKEN"] = github_token

    model = st.selectbox(
        "LLM Model",
        options=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-8b-8192",
            "gemma2-9b-it",
            "mixtral-8x7b-32768",
        ],
        index=0,
        help="All models run on Groq's ultra-fast inference.",
    )

    st.markdown("---")
    st.markdown("### 📌 Example Repos")
    examples = [
        "https://github.com/streamlit/streamlit",
        "https://github.com/tiangolo/fastapi",
        "https://github.com/pallets/flask",
        "https://github.com/huggingface/transformers",
        "https://github.com/pytorch/pytorch",
        "https://github.com/django/django",
    ]
    for ex in examples:
        name = ex.split("/")[-1]
        if st.button(f"🔗 {name}", key=ex):
            st.session_state["prefill_url"] = ex

    st.markdown("---")
    st.markdown(
        "<div style='color:#475569; font-size:0.75rem;'>Built with Groq + Streamlit<br/>LLaMA 3 powered</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  Main UI
# ─────────────────────────────────────────────
st.markdown('<div class="main-header">🔍 GitHub Repo Explainer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Paste any public GitHub repository URL and get an instant, beginner-friendly explanation powered by LLaMA 3 on Groq.</div>',
    unsafe_allow_html=True,
)

# URL input
default_url = st.session_state.get("prefill_url", "")
col_input, col_btn = st.columns([4, 1])
with col_input:
    github_url = st.text_input(
        "GitHub Repository URL",
        value=default_url,
        placeholder="https://github.com/owner/repo",
        label_visibility="collapsed",
    )
with col_btn:
    analyze_clicked = st.button("Analyze ✨", use_container_width=True)


# ─────────────────────────────────────────────
#  Analysis Pipeline
# ─────────────────────────────────────────────
if analyze_clicked and github_url:
    if not os.getenv("GROQ_API_KEY"):
        st.error("🔑 Please enter your Groq API key in the sidebar before analyzing.")
        st.stop()

    github_url = github_url.strip()

    # Validate URL
    try:
        owner, repo_name = parse_github_url(github_url)
    except ValueError as e:
        st.error(f"❌ Invalid GitHub URL: {e}")
        st.stop()

    st.markdown("---")

    # Step 1: Fetch
    with st.status("🚀 Fetching repository data from GitHub...", expanded=True) as status:
        st.write(f"📡 Connecting to GitHub API for `{owner}/{repo_name}`...")
        try:
            t0 = time.time()
            raw_data = fetch_all(github_url)
            fetch_time = round(time.time() - t0, 2)
            st.write(f"✅ Data fetched in {fetch_time}s — {len(raw_data.get('tree', []))} files indexed.")
        except Exception as e:
            status.update(label="❌ Fetch failed", state="error")
            st.error(f"Could not fetch repository: {e}")
            st.stop()

        # Step 2: Parse
        st.write("🔍 Parsing repository structure and detecting languages...")
        try:
            parsed = parse_repo_data(raw_data)
            st.write(f"✅ Detected {len(parsed.get('frameworks', []))} frameworks, {len(parsed.get('api_languages', {}))} languages.")
        except Exception as e:
            status.update(label="❌ Parse failed", state="error")
            st.error(f"Parsing failed: {e}")
            st.stop()

        status.update(label="✅ Data ready! Generating explanation...", state="complete", expanded=False)

    # ── Metadata Cards ──────────────────────
    st.markdown("### 📊 Repository Stats")
    c1, c2, c3, c4, c5 = st.columns(5)

    def metric_card(col, label, value):
        col.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

    def fmt_num(n):
        if n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)

    metric_card(c1, "⭐ Stars", fmt_num(parsed.get("stars", 0)))
    metric_card(c2, "🍴 Forks", fmt_num(parsed.get("forks", 0)))
    metric_card(c3, "📂 Files", str(parsed.get("file_counts", {}).get("total_files", 0)))
    metric_card(c4, "🐛 Issues", str(parsed.get("open_issues", 0)))
    metric_card(c5, "💻 Language", parsed.get("primary_language", "?"))

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Topics ───────────────────────────────
    if parsed.get("topics"):
        topics_html = "".join([f'<span class="tag-pill">{t}</span>' for t in parsed["topics"]])
        st.markdown(f"**Topics:** {topics_html}", unsafe_allow_html=True)
        st.markdown("<br/>", unsafe_allow_html=True)

    # ── Frameworks & Languages ───────────────
    col_lang, col_fw = st.columns(2)
    with col_lang:
        if parsed.get("api_languages"):
            st.markdown("**🌐 Language Breakdown**")
            for lang, pct in list(parsed["api_languages"].items())[:6]:
                st.progress(pct / 100, text=f"{lang} — {pct}%")

    with col_fw:
        if parsed.get("frameworks"):
            st.markdown("**🧰 Detected Frameworks & Tools**")
            fw_html = "".join([f'<span class="tag-pill">{f}</span>' for f in parsed["frameworks"]])
            st.markdown(fw_html, unsafe_allow_html=True)

    st.markdown("---")


    # Step 3: LLM Explanation (streaming)
    st.markdown("### 🤖 AI Explanation")
    explanation_placeholder = st.empty()
    full_explanation = ""

    try:
        with st.spinner(f"Generating explanation using `{model}`..."):
            chunks = []
            for chunk in explain_repo_streaming(parsed, model=model):
                chunks.append(chunk)
                full_explanation = "".join(chunks)
                explanation_placeholder.markdown(
                    f'<div class="explanation-box">{full_explanation}</div>',
                    unsafe_allow_html=True,
                )
    except Exception as e:
        st.error(f"❌ LLM Error: {e}")
        st.stop()

    # --- Improved Explanation Display ---
    import re
    def split_sections(text):
        # Split on emoji headers, keep header with section
        pattern = r'(\n|^)([🔍🛠📁⚙️🚀💡🎯])([^\n]*)\n'
        matches = list(re.finditer(pattern, text))
        sections = []
        for i, m in enumerate(matches):
            start = m.start(2)
            header = m.group(2) + m.group(3)
            end = matches[i+1].start(2) if i+1 < len(matches) else len(text)
            body = text[m.end():end].strip()
            sections.append((header.strip(), body))
        return sections

    if full_explanation:
        sections = split_sections(full_explanation)
        for header, body in sections:
            with st.expander(header, expanded=True):
                st.markdown(body)
        with st.expander("📝 Full Explanation (raw)", expanded=False):
            st.code(full_explanation)

    # ── Copy / Download ───────────────────────
    st.markdown("---")
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            label="⬇️ Download Explanation (.md)",
            data=full_explanation,
            file_name=f"{parsed.get('name', 'repo')}_explanation.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with dl_col2:
        st.download_button(
            label="⬇️ Download Raw Data (.txt)",
            data=str(parsed),
            file_name=f"{parsed.get('name', 'repo')}_raw.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # ── Folder Structure ─────────────────────
    with st.expander("📁 View Folder Structure", expanded=False):
        st.code(parsed.get("folder_structure", "Not available"), language="bash")

    # ── README Preview ─────────────────────
    if parsed.get("readme") and parsed["readme"] != "No README found in this repository.":
        with st.expander("📄 View README Preview", expanded=False):
            st.markdown(parsed["readme"][:3000])
elif analyze_clicked and not github_url:
    st.warning("⚠️ Please enter a GitHub repository URL first.")
else:
    # Welcome screen
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; padding: 3rem 1rem; color: #475569;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">🚀</div>
            <div style="font-size: 1.2rem; font-weight: 600; color: #94a3b8; margin-bottom: 0.5rem;">
                Ready to decode any GitHub repository
            </div>
            <div style="font-size: 0.9rem;">
                Enter a GitHub URL above and click <strong>Analyze</strong> to get started.<br/>
                Try one of the example repos from the sidebar!
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 💡 What you'll get")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.info("**🔍 Project Overview**\nUnderstand what the project does in plain English.")
    with f2:
        st.info("**🛠 Tech Stack**\nSee every language, framework, and tool used.")
    with f3:
        st.info("**⚙️ How It Works**\nStep-by-step explanation of the architecture.")