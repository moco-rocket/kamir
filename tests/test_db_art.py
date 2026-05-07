import sqlite3
from pathlib import Path

import pytest

from kamir.db.art import art_stats, fetch_and_store_art, load_art
from kamir.db.write import create_kamir_db, insert_cards
from kamir.domain import Card
from kamir.printer.render import RasterImage


def _card(**overrides) -> Card:
    base = dict(
        name="Grizzly Bears",
        mana_value=2,
        mana_cost="{1}{G}",
        type_line="Creature - Bear",
        oracle_text="",
        power="2",
        toughness="2",
        expansion="2ED",
        collector_number="178",
        layout="normal",
    )
    return Card(**{**base, **overrides})


def _fake_art() -> RasterImage:
    # 192×72: WIDTH_DOTS//2=96 effective width, 626×457 source → round(96*457/626/8)*8=72
    return RasterImage(data=bytes(24 * 72), width_bytes=24, height=72)


@pytest.fixture
def db_path(tmp_path) -> Path:
    path = tmp_path / "kamir_cardpool.sqlite"
    conn = create_kamir_db(path)
    insert_cards(conn, [_card()])
    conn.close()
    return path


@pytest.fixture
def old_schema_db_path(tmp_path) -> Path:
    """DB built without the art_raster column (simulates pre-art-feature schema)."""
    path = tmp_path / "old_kamir_cardpool.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE cards (
            name TEXT PRIMARY KEY, mana_value INTEGER, mana_cost TEXT,
            type_line TEXT, oracle_text TEXT, expansion TEXT,
            power TEXT, toughness TEXT, layout TEXT, collector_number TEXT
        )
    """)
    conn.execute(
        "INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("Grizzly Bears", 2, "{1}{G}", "Creature - Bear", "", "2ED", "2", "2", "normal", "178"),
    )
    conn.commit()
    conn.close()
    return path


def _mock_fetch(mocker, art=None):
    """Patch both batch functions; art=None simulates download failure."""
    url = "https://example.com/art.jpg"
    mocker.patch(
        "kamir.db.art.batch_fetch_art_crop_urls",
        return_value={"Grizzly Bears": url} if art is not None else {},
    )
    mocker.patch("kamir.db.art.fetch_art_from_url", return_value=art)


class TestLoadArt:
    def test_returns_none_when_no_art(self, db_path):
        assert load_art(db_path, _card()) is None

    def test_returns_raster_after_store(self, db_path, mocker):
        _mock_fetch(mocker, art=_fake_art())
        fetch_and_store_art(db_path, [_card()])
        result = load_art(db_path, _card())
        assert isinstance(result, RasterImage)
        assert len(result.data) == 24 * 72

    def test_returns_none_for_unknown_card(self, db_path):
        unknown = _card(name="Unknown Card")
        assert load_art(db_path, unknown) is None

    def test_returns_none_for_old_schema(self, old_schema_db_path):
        # Old DBs lack art_raster — should not crash; fall back to printing without art.
        assert load_art(old_schema_db_path, _card()) is None


class TestFetchAndStoreArt:
    def test_stores_art_when_fetch_succeeds(self, db_path, mocker):
        _mock_fetch(mocker, art=_fake_art())
        fetch_and_store_art(db_path, [_card()])
        assert load_art(db_path, _card()) is not None

    def test_skips_when_art_already_stored(self, db_path, mocker):
        mock_batch = mocker.patch(
            "kamir.db.art.batch_fetch_art_crop_urls",
            return_value={"Grizzly Bears": "https://example.com/art.jpg"},
        )
        mocker.patch("kamir.db.art.fetch_art_from_url", return_value=_fake_art())
        fetch_and_store_art(db_path, [_card()])
        fetch_and_store_art(db_path, [_card()])  # second call should skip
        assert mock_batch.call_count == 1

    def test_handles_fetch_failure_gracefully(self, db_path, mocker):
        _mock_fetch(mocker, art=None)
        fetch_and_store_art(db_path, [_card()])  # should not raise
        assert load_art(db_path, _card()) is None

    def test_idempotent_on_empty_card_list(self, db_path, mocker):
        mock_batch = mocker.patch("kamir.db.art.batch_fetch_art_crop_urls", return_value={})
        mocker.patch("kamir.db.art.fetch_art_from_url", return_value=_fake_art())
        fetch_and_store_art(db_path, [])
        assert mock_batch.call_count == 0


class TestArtStats:
    def test_returns_none_when_db_missing(self, tmp_path):
        assert art_stats(tmp_path / "nonexistent.sqlite") is None

    def test_returns_zero_art_for_fresh_db(self, db_path):
        total, with_art = art_stats(db_path)
        assert total == 1
        assert with_art == 0

    def test_counts_stored_art(self, db_path, mocker):
        _mock_fetch(mocker, art=_fake_art())
        fetch_and_store_art(db_path, [_card()])
        total, with_art = art_stats(db_path)
        assert total == 1
        assert with_art == 1

    def test_returns_none_for_old_schema(self, old_schema_db_path):
        assert art_stats(old_schema_db_path) is None
