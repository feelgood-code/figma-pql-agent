from __future__ import annotations

import hashlib
from pathlib import Path

from src.config import CACHE_DIR
from src.models import AccountBrief


def _key(company: str, champion: str) -> str:
    raw = f"{company.strip().lower()}|{champion.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load(company: str, champion: str) -> AccountBrief | None:
    path = CACHE_DIR / _key(company, champion) / "brief.json"
    if path.exists():
        try:
            return AccountBrief.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save(brief: AccountBrief) -> None:
    folder = CACHE_DIR / _key(brief.company, brief.champion)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "brief.json").write_text(
        brief.model_dump_json(indent=2), encoding="utf-8"
    )
