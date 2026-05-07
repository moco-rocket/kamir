from pathlib import Path

import pytest

from kamir.db.art import fetch_and_store_art, load_art
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
    return RasterImage(data=bytes(48 * 192), width_bytes=48, height=192)


@pytest.fixture
def db_path(tmp_path) -> Path:
    path = tmp_path / "kamir_cardpool.sqlite"
    conn = create_kamir_db(path)
    insert_cards(conn, [_card()])
    conn.close()
    return path


class TestLoadArt:
    def test_returns_none_when_no_art(self, db_path):
        assert load_art(db_path, _card()) is None

    def test_returns_raster_after_store(self, db_path, mocker):
        mocker.patch("kamir.db.art.fetch_art", return_value=_fake_art())
        fetch_and_store_art(db_path, [_card()])
        result = load_art(db_path, _card())
        assert isinstance(result, RasterImage)
        assert len(result.data) == 48 * 192

    def test_returns_none_for_unknown_card(self, db_path):
        unknown = _card(name="Unknown Card")
        assert load_art(db_path, unknown) is None


class TestFetchAndStoreArt:
    def test_stores_art_when_fetch_succeeds(self, db_path, mocker):
        mocker.patch("kamir.db.art.fetch_art", return_value=_fake_art())
        fetch_and_store_art(db_path, [_card()])
        assert load_art(db_path, _card()) is not None

    def test_skips_when_art_already_stored(self, db_path, mocker):
        mock_fetch = mocker.patch("kamir.db.art.fetch_art", return_value=_fake_art())
        fetch_and_store_art(db_path, [_card()])
        fetch_and_store_art(db_path, [_card()])  # second call should skip
        assert mock_fetch.call_count == 1

    def test_handles_fetch_failure_gracefully(self, db_path, mocker):
        mocker.patch("kamir.db.art.fetch_art", return_value=None)
        fetch_and_store_art(db_path, [_card()])  # should not raise
        assert load_art(db_path, _card()) is None

    def test_idempotent_on_empty_card_list(self, db_path, mocker):
        mock_fetch = mocker.patch("kamir.db.art.fetch_art", return_value=_fake_art())
        fetch_and_store_art(db_path, [])
        assert mock_fetch.call_count == 0
