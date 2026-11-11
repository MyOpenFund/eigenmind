"""QDRANT_API_KEY: read from env (blank = no key), passed to every QdrantClient."""
from __future__ import annotations

import pytest

from eigenmind import config
from eigenmind.vectordb import store as store_mod
from eigenmind.vectordb.store import QdrantStore


class _RecordingClient:
    calls: list[dict] = []

    def __init__(self, **kwargs):
        _RecordingClient.calls.append(kwargs)

    def get_collections(self):
        return None


@pytest.fixture
def rec(monkeypatch):
    _RecordingClient.calls = []
    monkeypatch.setattr(store_mod, "QdrantClient", _RecordingClient)
    return _RecordingClient


def test_api_key_unset_is_none(monkeypatch):
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    assert config.qdrant_api_key() is None


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_api_key_blank_is_none(monkeypatch, raw):
    monkeypatch.setenv("QDRANT_API_KEY", raw)
    assert config.qdrant_api_key() is None


def test_api_key_is_stripped(monkeypatch):
    monkeypatch.setenv("QDRANT_API_KEY", "  k1  ")
    assert config.qdrant_api_key() == "k1"


def test_store_passes_the_env_key(monkeypatch, rec):
    monkeypatch.setenv("QDRANT_API_KEY", "k1")
    QdrantStore(host="h", port=1)
    assert rec.calls[-1] == {"host": "h", "port": 1, "timeout": 60, "api_key": "k1"}


def test_store_without_key_passes_none(monkeypatch, rec):
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    QdrantStore(host="h", port=1)
    assert rec.calls[-1] == {"host": "h", "port": 1, "timeout": 60, "api_key": None}


def test_explicit_key_wins_over_env(monkeypatch, rec):
    monkeypatch.setenv("QDRANT_API_KEY", "from-env")
    QdrantStore(host="h", port=1, api_key="explicit")
    assert rec.calls[-1]["api_key"] == "explicit"


def test_blank_explicit_key_falls_back_to_env(monkeypatch, rec):
    monkeypatch.setenv("QDRANT_API_KEY", "from-env")
    QdrantStore(host="h", port=1, api_key="   ")
    assert rec.calls[-1]["api_key"] == "from-env"


def test_is_reachable_passes_the_key(monkeypatch, rec):
    monkeypatch.setenv("QDRANT_API_KEY", "k1")
    assert QdrantStore.is_reachable("h", 1) is True
    assert rec.calls[-1] == {"host": "h", "port": 1, "timeout": 3, "api_key": "k1"}
