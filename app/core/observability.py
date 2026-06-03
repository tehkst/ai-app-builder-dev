import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


def configure_langsmith() -> dict:
    """
    Configure LangSmith tracing for LangChain/LangGraph runs.

    Tracing is enabled only when LANGSMITH_API_KEY is present.
    This keeps local development working even before LangSmith credentials are configured.
    """
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
    project_name = os.getenv("LANGCHAIN_PROJECT", "AI-Software-Factory")

    if not langsmith_api_key:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
        return {
            "enabled": False,
            "project": project_name,
            "reason": "LANGSMITH_API_KEY is not configured",
        }

    os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
    os.environ["LANGCHAIN_PROJECT"] = project_name
    os.environ["LANGSMITH_API_KEY"] = langsmith_api_key

    return {
        "enabled": os.environ.get("LANGCHAIN_TRACING_V2") == "true",
        "project": project_name,
    }
