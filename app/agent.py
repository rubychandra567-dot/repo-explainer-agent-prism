import os
from pathlib import Path
from groq import Groq
from app.utils import log_info, log_error, build_prompt_context


SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"


def load_system_prompt() -> str:
    """Load the system prompt from file."""
    if not SYSTEM_PROMPT_PATH.exists():
        raise FileNotFoundError(f"System prompt not found at: {SYSTEM_PROMPT_PATH}")
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def get_groq_client() -> Groq:
    """Initialize and return a Groq client."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Please add it to your .env file."
        )
    return Groq(api_key=api_key)


def explain_repo(parsed_data: dict, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Call the LLM with parsed repo data and return a structured explanation.

    Args:
        parsed_data: Dictionary of parsed repository information.
        model: Groq model to use (default: llama3-70b-8192).

    Returns:
        A structured string explanation from the LLM.
    """
    log_info(f"Calling LLM model: {model}")

    system_prompt = load_system_prompt()
    context = build_prompt_context(parsed_data)

    user_message = (
        f"Please analyze the following GitHub repository and explain it using the required format:\n\n"
        f"{context}"
    )

    client = get_groq_client()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=2048,
            top_p=1,
            stream=False,
        )
        explanation = response.choices[0].message.content
        log_info("LLM response received successfully.")
        return explanation

    except Exception as e:
        log_error(f"LLM call failed: {e}")
        raise RuntimeError(f"Failed to get explanation from Groq API: {e}") from e


def explain_repo_streaming(parsed_data: dict, model: str = "llama-3.3-70b-versatile"):
    """
    Streaming version of explain_repo. Yields text chunks as they arrive.

    Args:
        parsed_data: Dictionary of parsed repository information.
        model: Groq model to use.

    Yields:
        String chunks of the response.
    """
    log_info(f"Calling LLM model (streaming): {model}")

    system_prompt = load_system_prompt()
    context = build_prompt_context(parsed_data)

    user_message = (
        f"Please analyze the following GitHub repository and explain it using the required format:\n\n"
        f"{context}"
    )

    client = get_groq_client()

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=2048,
            top_p=1,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    except Exception as e:
        log_error(f"Streaming LLM call failed: {e}")
        raise RuntimeError(f"Failed to stream explanation from Groq API: {e}") from e