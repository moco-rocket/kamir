import sqlite3
import pytest


def _make_card(**overrides) -> dict:
    base = {
        "name": "Grizzly Bears",
        "faceName": None,
        "asciiName": None,
        "manaValue": 2,
        "manaCost": "{1}{G}",
        "type": "Creature - Bear",
        "types": "Creature",
        "text": "No abilities.",
        "setCode": "2ED",
        "power": "2",
        "toughness": "2",
        "layout": "normal",
        "number": "178",
        "side": None,
        "isFunny": 0,
        "isReprint": 0,
        "baseSetSize": 302,
        "releaseDate": "1993-01-01",
        "set_row_id": 1,
    }
    return {**base, **overrides}


@pytest.fixture
def sample_card():
    return _make_card()


@pytest.fixture
def make_card():
    return _make_card


@pytest.fixture
def in_memory_db():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()
