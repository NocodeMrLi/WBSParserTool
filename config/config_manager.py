import json
import os
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "WBSParserTool"


@dataclass
class ApiConfig:
    base_url: str = ""
    api_key: str = ""
    model: str = ""

    @property
    def is_complete(self) -> bool:
        return bool(self.base_url.strip() and self.api_key.strip() and self.model.strip())


def get_config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_NAME


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


def load_api_config() -> ApiConfig:
    path = get_config_path()
    if not path.exists():
        return ApiConfig()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ApiConfig()

    return ApiConfig(
        base_url=str(data.get("base_url", "")),
        api_key=str(data.get("api_key", "")),
        model=str(data.get("model", "")),
    )


def save_api_config(config: ApiConfig) -> None:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    get_config_path().write_text(
        json.dumps(
            {
                "base_url": config.base_url.strip(),
                "api_key": config.api_key.strip(),
                "model": config.model.strip(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
