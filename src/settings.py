from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv


DEFAULT_ENV_FILE = Path(__file__).parents[1] / ".env"

@dataclass(frozen=True)
class AppSettings:
    openai_api_key: str
    openai_model: str
    admin_user_id: str
    admin_password: str

    @property
    def missing_required(self) -> tuple[str, ...]:
        required = {
            "OPENAI_API_KEY": self.openai_api_key,
            "LEARNCRAFT_ADMIN_USER": self.admin_user_id,
            "LEARNCRAFT_ADMIN_PASSWORD": self.admin_password,
        }
        return tuple(name for name, value in required.items() if not value)


def load_settings(
    environ: Mapping[str, str] | None = None,
    env_file: str | Path | None = None,
) -> AppSettings:
    if environ is None:
        load_dotenv(dotenv_path=env_file or DEFAULT_ENV_FILE,override=False)
        source: Mapping[str,str]=os.environ
    else:
        source=environ
    return AppSettings(
        openai_api_key=source.get("OPENAI_API_KEY", "").strip(),
        openai_model=source.get("OPENAI_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna",
        admin_user_id=source.get("LEARNCRAFT_ADMIN_USER", "").strip(),
        admin_password=source.get("LEARNCRAFT_ADMIN_PASSWORD", ""),
    )


def credentials_match(user_id: str, password: str, settings: AppSettings) -> bool:
    user_matches = hmac.compare_digest(str(user_id), settings.admin_user_id)
    password_matches = hmac.compare_digest(str(password), settings.admin_password)
    return user_matches & password_matches
