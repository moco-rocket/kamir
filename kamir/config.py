import tomllib
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def load(path: Path | None = None) -> dict:
    config_path = path or (_ROOT / "config.toml")
    with open(config_path, "rb") as f:
        return tomllib.load(f)
