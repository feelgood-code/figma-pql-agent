import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
DEMO_MODE = os.getenv("DEMO_MODE", "live")

ROOT_DIR = Path(__file__).parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
CACHE_DIR = ROOT_DIR / "data" / "cached"
