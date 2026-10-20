"""Shared JEV wrapper — points TypeSafe SDK at OpenRouter."""

import os
from dotenv import load_dotenv
from typesafe_sdk import TypeSafeClient

# Load OPENROUTER_API_KEY from .env into os.environ
load_dotenv()

# Same TypeSafe SDK, redirected to OpenRouter's base URL
_client = TypeSafeClient(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api",
)

JEV_MODEL = "jev-latest"


def ask_jev(state: str, questions: dict):
    """Send any mix of Choice/Noul/Score questions to JEV in one call.

    state: the thing being judged (a shell command, in this project)
    questions: dict of name -> Choice/Noul/Score instance
    """
    return _client.system_one(state, questions, model=JEV_MODEL)
