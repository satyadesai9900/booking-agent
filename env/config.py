"""
Environment configuration module.
Loads settings from .env in env/ or root directory.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Search paths for .env file
_ENV_SEARCH_PATHS = [
    Path(__file__).parent / ".env",
    Path.cwd() / "env" / ".env",
    Path.cwd() / ".env",
    Path(__file__).parent.parent / ".env",
]

# Load first found .env
for _path in _ENV_SEARCH_PATHS:
    if _path.exists():
        load_dotenv(dotenv_path=_path)
        break
else:
    load_dotenv()


@dataclass
class Settings:
    """Application and Agent Settings."""
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    default_thread_id: str = os.getenv("DEFAULT_THREAD_ID", "1")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    temperature: float = float(os.getenv("TEMPERATURE", "0.3"))


config = Settings()


def get_gemini_api_key() -> str:
    """Retrieve Gemini API key from environment, config, or user prompt."""
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    if config.gemini_api_key and config.gemini_api_key.strip() and config.gemini_api_key != "your_gemini_api_key_here":
        return config.gemini_api_key.strip()

    print("\n" + "=" * 60)
    print(" GEMINI API KEY REQUIRED")
    print("=" * 60)
    print("No GEMINI_API_KEY found in .env file or environment.")
    print("Get your API key at: https://aistudio.google.com/app/apikey\n")
    try:
        user_key = input("Please enter your Gemini API Key: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        sys.exit(0)

    if not user_key:
        print("Error: Gemini API Key cannot be empty.")
        sys.exit(1)

    return user_key
