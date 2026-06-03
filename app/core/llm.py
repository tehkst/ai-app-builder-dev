import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from app.core.observability import configure_langsmith


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)
LANGSMITH_STATUS = configure_langsmith()


def get_llm():

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            f"OPENAI_API_KEY is missing. Checked: {ENV_PATH}"
        )

    return ChatOpenAI(
        model=model,
        temperature=0.2,
        api_key=api_key,
        timeout=60,
        max_retries=0,
        tags=["ai-software-factory", "generator"],
        metadata={
            "langsmith_enabled": LANGSMITH_STATUS.get("enabled", False),
            "langsmith_project": LANGSMITH_STATUS.get("project"),
        },
    )
