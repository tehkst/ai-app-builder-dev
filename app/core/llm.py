import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


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
    )
