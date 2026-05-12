from pathlib import Path

import pytest

import kamir.config as cfg_mod
from kamir.config import Config, Pool, RuntimeConfig

_MINIMAL_TOML = """\
[runtime]
default_pool = "test"
log_file = "logs/kamir.log"

[runtime.printer]
device = "/dev/usb/lp0"

[[pool]]
name = "test"
path = "data/db/kamir_test.sqlite"
mtgjson_db = "data/db/AllPrintings.sqlite"
sets = ["2ED"]
"""


@pytest.fixture
def config_file(tmp_path) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(_MINIMAL_TOML)
    return p


def test_find_explicit_path_takes_priority(config_file, monkeypatch, tmp_path):
    monkeypatch.setenv("KAMIR_CONFIG", str(tmp_path / "env.toml"))
    monkeypatch.chdir(tmp_path)
    assert cfg_mod.find(config_file) == config_file


def test_find_env_var_used_when_no_explicit_path(config_file, monkeypatch, tmp_path):
    monkeypatch.setenv("KAMIR_CONFIG", str(config_file))
    monkeypatch.chdir(tmp_path)
    assert cfg_mod.find(None) == config_file


def test_find_falls_back_to_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("KAMIR_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cfg_mod.find(None) == tmp_path / "config.toml"


def test_load_returns_config(config_file):
    assert isinstance(cfg_mod.load(config_file), Config)


def test_load_runtime_default_pool(config_file):
    assert cfg_mod.load(config_file).runtime.default_pool == "test"


def test_load_runtime_auto_print_default_true(config_file):
    assert cfg_mod.load(config_file).runtime.auto_print is True


def test_load_runtime_printer_device(config_file):
    assert cfg_mod.load(config_file).runtime.printer_device == "/dev/usb/lp0"


def test_load_runtime_log_file_is_absolute(config_file, tmp_path):
    log_file = cfg_mod.load(config_file).runtime.log_file
    assert log_file.is_absolute()
    assert log_file == tmp_path / "logs/kamir.log"


def test_load_pool_count(config_file):
    assert len(cfg_mod.load(config_file).pools) == 1


def test_load_pool_name(config_file):
    assert cfg_mod.load(config_file).pools[0].name == "test"


def test_load_pool_path_is_absolute(config_file, tmp_path):
    pool = cfg_mod.load(config_file).pools[0]
    assert pool.path == tmp_path / "data/db/kamir_test.sqlite"


def test_load_pool_mtgjson_db_is_absolute(config_file, tmp_path):
    pool = cfg_mod.load(config_file).pools[0]
    assert pool.mtgjson_db == tmp_path / "data/db/AllPrintings.sqlite"


def test_load_pool_sets(config_file):
    assert cfg_mod.load(config_file).pools[0].sets == ["2ED"]


def test_get_pool_returns_pool_by_name(config_file):
    config = cfg_mod.load(config_file)
    pool = config.get_pool("test")
    assert pool is not None and pool.name == "test"


def test_get_pool_returns_none_for_missing(config_file):
    assert cfg_mod.load(config_file).get_pool("nonexistent") is None


def test_load_auto_print_explicit_false(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('[runtime]\ndefault_pool = "x"\nlog_file = "l.log"\nauto_print = false\n')
    assert cfg_mod.load(p).runtime.auto_print is False


def test_load_wildcard_sets_string(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(
        '[runtime]\ndefault_pool = "all"\nlog_file = "l.log"\n'
        '[[pool]]\nname = "all"\npath = "a.sqlite"\nmtgjson_db = "b.sqlite"\nsets = "*"\n'
    )
    assert cfg_mod.load(p).pools[0].sets == "*"


def test_load_multiple_pools(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(
        '[runtime]\ndefault_pool = "a"\nlog_file = "l.log"\n'
        '[[pool]]\nname = "a"\npath = "a.sqlite"\nmtgjson_db = "b.sqlite"\nsets = ["2ED"]\n'
        '[[pool]]\nname = "b"\npath = "b.sqlite"\nmtgjson_db = "b.sqlite"\nsets = "*"\n'
    )
    config = cfg_mod.load(p)
    assert len(config.pools) == 2
    assert config.get_pool("a") is not None
    assert config.get_pool("b") is not None


def test_load_reads_env_var(config_file, monkeypatch, tmp_path):
    monkeypatch.setenv("KAMIR_CONFIG", str(config_file))
    monkeypatch.chdir(tmp_path)
    assert cfg_mod.load().runtime.default_pool == "test"


def test_load_reads_cwd_config(monkeypatch, tmp_path):
    (tmp_path / "config.toml").write_text(
        '[runtime]\ndefault_pool = "cwd"\nlog_file = "l.log"\n'
    )
    monkeypatch.delenv("KAMIR_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cfg_mod.load().runtime.default_pool == "cwd"
