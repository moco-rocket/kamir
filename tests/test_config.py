from pathlib import Path

import pytest

import kamir.config as cfg_mod


@pytest.fixture
def config_file(tmp_path) -> Path:
    p = tmp_path / "config.toml"
    p.write_text('[paths]\nkamir_db = "kamir.sqlite"\n')
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


def test_load_reads_explicit_path(config_file):
    result = cfg_mod.load(config_file)
    assert result["paths"]["kamir_db"] == "kamir.sqlite"


def test_load_reads_env_var(config_file, monkeypatch, tmp_path):
    monkeypatch.setenv("KAMIR_CONFIG", str(config_file))
    monkeypatch.chdir(tmp_path)
    result = cfg_mod.load()
    assert result["paths"]["kamir_db"] == "kamir.sqlite"


def test_load_reads_cwd_config(monkeypatch, tmp_path):
    (tmp_path / "config.toml").write_text('[paths]\nkamir_db = "from_cwd.sqlite"\n')
    monkeypatch.delenv("KAMIR_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    result = cfg_mod.load()
    assert result["paths"]["kamir_db"] == "from_cwd.sqlite"
