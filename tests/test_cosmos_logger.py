"""
Tests unitaires de la persistance Cosmos DB / journal local (memory/cosmos_logger.py).
"""
import json
from unittest.mock import MagicMock

import pytest

import memory.cosmos_logger as cosmos_module
from config.settings import settings
from memory.cosmos_logger import (
    _ecrire,
    _get_container,
    exporter_conversation,
    log_conversation,
    log_tool_call,
)


@pytest.fixture(autouse=True)
def isole_cosmos(tmp_path, monkeypatch):
    """Réinitialise le cache global _container et redirige le journal local vers
    un dossier temporaire, pour ne jamais toucher les vraies ressources Azure."""
    monkeypatch.setattr(cosmos_module, "_container", None)
    monkeypatch.setattr(cosmos_module, "_FICHIER_LOCAL", tmp_path / "conversations.jsonl")
    yield


# --- _get_container : absence de credentials (ligne 36) ----------------------
def test_get_container_retourne_none_si_credentials_absentes(monkeypatch):
    monkeypatch.setattr(settings, "cosmos_endpoint", "")
    monkeypatch.setattr(settings, "cosmos_key", "")

    assert _get_container() is None


# --- _get_container : échec de connexion (lignes 48-50) ----------------------
def test_get_container_retourne_none_si_connexion_echoue(monkeypatch):
    monkeypatch.setattr(settings, "cosmos_endpoint", "https://faux-endpoint.documents.azure.com")
    monkeypatch.setattr(settings, "cosmos_key", "fausse-cle")
    monkeypatch.setattr("azure.cosmos.CosmosClient", MagicMock(side_effect=ConnectionError("injoignable")))

    assert _get_container() is None


# --- _get_container : connexion réussie + mise en cache -----------------------
def test_get_container_retourne_le_container_si_connexion_reussie(monkeypatch):
    monkeypatch.setattr(settings, "cosmos_endpoint", "https://faux-endpoint.documents.azure.com")
    monkeypatch.setattr(settings, "cosmos_key", "fausse-cle")
    mock_container = MagicMock()
    mock_db = MagicMock()
    mock_db.create_container_if_not_exists.return_value = mock_container
    mock_client_instance = MagicMock()
    mock_client_instance.create_database_if_not_exists.return_value = mock_db
    monkeypatch.setattr("azure.cosmos.CosmosClient", MagicMock(return_value=mock_client_instance))

    assert _get_container() is mock_container

def test_get_container_reutilise_le_cache(monkeypatch):
    """Un deuxième appel ne doit pas reconstruire de client (cache global)."""
    monkeypatch.setattr(settings, "cosmos_endpoint", "https://faux-endpoint.documents.azure.com")
    monkeypatch.setattr(settings, "cosmos_key", "fausse-cle")
    mock_db = MagicMock()
    mock_db.create_container_if_not_exists.return_value = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.create_database_if_not_exists.return_value = mock_db
    mock_cosmos_client_cls = MagicMock(return_value=mock_client_instance)
    monkeypatch.setattr("azure.cosmos.CosmosClient", mock_cosmos_client_cls)

    _get_container()
    _get_container()

    mock_cosmos_client_cls.assert_called_once()


# --- _ecrire : pas de container → repli local direct --------------------------
def test_ecrire_sans_container_ecrit_dans_le_fichier_local(monkeypatch):
    monkeypatch.setattr(settings, "cosmos_endpoint", "")
    monkeypatch.setattr(settings, "cosmos_key", "")

    _ecrire({"type": "test", "session_id": "s1"})

    document = json.loads(cosmos_module._FICHIER_LOCAL.read_text(encoding="utf-8").splitlines()[0])
    assert document["session_id"] == "s1"
    assert "id" in document
    assert "horodatage" in document


# --- _ecrire : échec d'écriture Cosmos → repli local (lignes 61-65) ----------
def test_ecrire_repli_local_si_upsert_echoue(monkeypatch):
    mock_container = MagicMock()
    mock_container.upsert_item.side_effect = Exception("Cosmos indisponible")
    monkeypatch.setattr(cosmos_module, "_get_container", lambda: mock_container)

    _ecrire({"type": "test", "session_id": "s2"})

    mock_container.upsert_item.assert_called_once()
    document = json.loads(cosmos_module._FICHIER_LOCAL.read_text(encoding="utf-8").splitlines()[0])
    assert document["session_id"] == "s2"

def test_ecrire_reussit_avec_cosmos_sans_repli(monkeypatch):
    """Cas nominal : l'écriture Cosmos réussit, aucun repli local ne doit avoir lieu."""
    mock_container = MagicMock()
    monkeypatch.setattr(cosmos_module, "_get_container", lambda: mock_container)

    _ecrire({"type": "test", "session_id": "s3"})

    mock_container.upsert_item.assert_called_once()
    assert not cosmos_module._FICHIER_LOCAL.exists()


# --- log_conversation (ligne 86) ----------------------------------------------
def test_log_conversation_appelle_ecrire_avec_les_bons_champs(monkeypatch):
    mock_ecrire = MagicMock()
    monkeypatch.setattr(cosmos_module, "_ecrire", mock_ecrire)

    log_conversation("session-42", "Écris Fibonacci", [{"role": "user", "content": "..."}], "34")

    mock_ecrire.assert_called_once_with({
        "type": "conversation",
        "session_id": "session-42",
        "tache": "Écris Fibonacci",
        "messages": [{"role": "user", "content": "..."}],
        "reponse_finale": "34",
    })

def test_log_tool_call_appelle_ecrire_avec_les_bons_champs(monkeypatch):
    mock_ecrire = MagicMock()
    monkeypatch.setattr(cosmos_module, "_ecrire", mock_ecrire)

    log_tool_call("calculer", {"expression": "2+2"}, "4", 0.01, "OK")

    mock_ecrire.assert_called_once_with({
        "type": "tool_call",
        "session_id": "outillage",
        "outil": "calculer",
        "entree": {"expression": "2+2"},
        "sortie": "4",
        "duree_s": 0.01,
        "statut": "OK",
    })


# --- exporter_conversation : via Cosmos (lignes 97-105) ----------------------
def test_exporter_conversation_trouve_via_cosmos(monkeypatch):
    mock_container = MagicMock()
    mock_container.query_items.return_value = [{"session_id": "session-1", "type": "conversation"}]
    monkeypatch.setattr(cosmos_module, "_get_container", lambda: mock_container)

    assert exporter_conversation("session-1") == {"session_id": "session-1", "type": "conversation"}

def test_exporter_conversation_absente_via_cosmos(monkeypatch):
    mock_container = MagicMock()
    mock_container.query_items.return_value = []
    monkeypatch.setattr(cosmos_module, "_get_container", lambda: mock_container)

    assert exporter_conversation("session-inconnue") is None


# --- exporter_conversation : repli local (lignes 106-112) --------------------
def test_exporter_conversation_trouve_dans_le_fichier_local(monkeypatch):
    monkeypatch.setattr(cosmos_module, "_get_container", lambda: None)
    doc = {"session_id": "session-9", "type": "conversation", "tache": "x"}
    cosmos_module._FICHIER_LOCAL.parent.mkdir(exist_ok=True)
    cosmos_module._FICHIER_LOCAL.write_text(json.dumps(doc) + "\n", encoding="utf-8")

    assert exporter_conversation("session-9") == doc

def test_exporter_conversation_absente_du_fichier_local(monkeypatch):
    monkeypatch.setattr(cosmos_module, "_get_container", lambda: None)
    assert exporter_conversation("session-inconnue") is None

def test_exporter_conversation_ignore_les_lignes_d_autres_sessions(monkeypatch):
    monkeypatch.setattr(cosmos_module, "_get_container", lambda: None)
    cosmos_module._FICHIER_LOCAL.parent.mkdir(exist_ok=True)
    autre_doc = {"session_id": "autre-session", "type": "conversation"}
    cosmos_module._FICHIER_LOCAL.write_text(json.dumps(autre_doc) + "\n", encoding="utf-8")

    assert exporter_conversation("session-9") is None
