import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Pool:
    name: str
    path: Path
    mtgjson_db: Path
    sets: list[str] | str  # "*" or list of set codes


@dataclass
class RuntimeConfig:
    log_file: Path
    auto_print: bool
    printer_device: str
    default_pool: str
    gpio: dict = field(default_factory=dict)


@dataclass
class Config:
    runtime: RuntimeConfig
    pools: list[Pool]

    def get_pool(self, name: str) -> Pool | None:
        return next((p for p in self.pools if p.name == name), None)


def find(path: Path | None = None) -> Path:
    """Resolve config path: explicit arg > KAMIR_CONFIG env var > CWD/config.toml."""
    if path is not None:
        return path
    env = os.environ.get("KAMIR_CONFIG")
    if env:
        return Path(env)
    return Path.cwd() / "config.toml"


def load(path: Path | None = None) -> Config:
    config_path = find(path)
    root = config_path.parent.resolve()
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    rt = raw["runtime"]
    runtime = RuntimeConfig(
        log_file=root / rt["log_file"],
        auto_print=rt.get("auto_print", True),
        printer_device=rt.get("printer", {}).get("device", "/dev/usb/lp0"),
        default_pool=rt["default_pool"],
        gpio=rt.get("gpio", {}),
    )

    pools = [
        Pool(
            name=p["name"],
            path=root / p["path"],
            mtgjson_db=root / p["mtgjson_db"],
            sets=p["sets"],
        )
        for p in raw.get("pool", [])
    ]

    return Config(runtime=runtime, pools=pools)
