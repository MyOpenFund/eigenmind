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
    monkeypatch.delenv("QDRANT_HTTPS", raising=False)
    QdrantStore(host="h", port=1)
    assert rec.calls[-1] == {"host": "h", "port": 1, "timeout": 60, "api_key": "k1", "https": False}


def test_store_without_key_passes_none(monkeypatch, rec):
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    monkeypatch.delenv("QDRANT_HTTPS", raising=False)
    QdrantStore(host="h", port=1)
    assert rec.calls[-1] == {"host": "h", "port": 1, "timeout": 60, "api_key": None, "https": False}


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
    monkeypatch.delenv("QDRANT_HTTPS", raising=False)
    assert QdrantStore.is_reachable("h", 1) is True
    assert rec.calls[-1] == {"host": "h", "port": 1, "timeout": 3, "api_key": "k1", "https": False}


@pytest.mark.parametrize("raw", [None, "", "  ", "0", "false", "False", "no", "off"])
def test_https_defaults_to_false(monkeypatch, raw):
    if raw is None:
        monkeypatch.delenv("QDRANT_HTTPS", raising=False)
    else:
        monkeypatch.setenv("QDRANT_HTTPS", raw)
    assert config.qdrant_https() is False


@pytest.mark.parametrize("raw", ["1", "true", " TRUE ", "yes", "on"])
def test_https_true_values(monkeypatch, raw):
    monkeypatch.setenv("QDRANT_HTTPS", raw)
    assert config.qdrant_https() is True


def test_https_rejects_garbage(monkeypatch):
    monkeypatch.setenv("QDRANT_HTTPS", "maybe")
    with pytest.raises(ValueError, match="QDRANT_HTTPS='maybe' is not a boolean"):
        config.qdrant_https()


def test_a_key_does_not_switch_the_client_to_tls(monkeypatch, rec):
    """qdrant-client turns https on whenever api_key is set and https is None:
    eigenmind must always pass it explicitly (plain HTTP by default)."""
    monkeypatch.setenv("QDRANT_API_KEY", "k1")
    monkeypatch.delenv("QDRANT_HTTPS", raising=False)
    QdrantStore(host="h", port=1)
    QdrantStore.is_reachable("h", 1)
    assert [c["https"] for c in rec.calls] == [False, False]


def test_https_flag_reaches_the_client(monkeypatch, rec):
    monkeypatch.setenv("QDRANT_HTTPS", "true")
    QdrantStore(host="h", port=1)
    assert rec.calls[-1]["https"] is True


def test_the_real_client_stays_on_http_with_a_key(monkeypatch):
    """Against the real qdrant-client class (no network: construction only)."""
    monkeypatch.setenv("QDRANT_API_KEY", "k1")
    monkeypatch.delenv("QDRANT_HTTPS", raising=False)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # "Api key is used with an insecure connection"
        store = QdrantStore(host="h", port=1)
    assert store.client._client.rest_uri.startswith("http://")
