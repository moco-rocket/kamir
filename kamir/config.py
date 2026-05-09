import os
import tomllib
from pathlib import Path


def find(path: Path | None = None) -> Path:
    """Resolve config path: explicit arg > KAMIR_CONFIG env var > CWD/config.toml."""
    if path is not None:
        return path
    env = os.environ.get("KAMIR_CONFIG")
    if env:
        return Path(env)
    return Path.cwd() / "config.toml"


def load(path: Path | None = None) -> dict:
    config_path = find(path)
    with open(config_path, "rb") as f:
        return tomllib.load(f)
