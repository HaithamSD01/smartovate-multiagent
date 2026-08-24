"""
Tests unitaires de l'API REST (api/main.py).
"""
import sys
import types
from unittest.mock import AsyncMock, MagicMock

_fake_redis_module = types.ModuleType("redis")
_fake_redis_module.Redis = MagicMock()
sys.modules.setdefault("redis", _fake_redis_module)

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import api.main as api_module
from api.main import app, verifier_api_key
from config.settings import settings

client = TestClient(app)


def test_health_retourne_ok():
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "OK", "service": "smartovate-mas"}


def test_verifier_api_key_accepte_la_bonne_cle(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    verifier_api_key(x_api_key="bonne-cle")

def test_verifier_api_key_refuse_une_mauvaise_cle(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    with pytest.raises(HTTPException) as exc_info:
        verifier_api_key(x_api_key="mauvaise-cle")
    assert exc_info.value.status_code == 401

def test_endpoint_protege_refuse_sans_cle(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    reponse = client.get("/tasks/inexistant")
    assert reponse.status_code == 401


def test_consulter_tache_inconnue_retourne_404(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    monkeypatch.setattr(api_module.session_memory, "get", lambda *a, **k: None)

    reponse = client.get("/tasks/inconnue", headers={"X-API-Key": "bonne-cle"})

    assert reponse.status_code == 404

def test_consulter_tache_existante_retourne_son_etat(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    valeurs = {"statut": "TERMINE", "tache": "Fibonacci", "messages": [], "reponse": "34"}
    monkeypatch.setattr(
        api_module.session_memory, "get",
        lambda task_id, cle, defaut=None: valeurs.get(cle, defaut),
    )

    reponse = client.get("/tasks/existante", headers={"X-API-Key": "bonne-cle"})

    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "TERMINE"
    assert reponse.json()["reponse"] == "34"


def test_soumettre_tache_retourne_200_en_attente(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    monkeypatch.setattr(api_module, "executer_tache", AsyncMock())

    reponse = client.post(
        "/tasks",
        json={"task": "Écris une fonction Python."},
        headers={"X-API-Key": "bonne-cle"},
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "EN_ATTENTE"
    assert "task_id" in corps

def test_soumettre_tache_rejette_une_tache_trop_courte(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    reponse = client.post("/tasks", json={"task": "abc"}, headers={"X-API-Key": "bonne-cle"})
    assert reponse.status_code == 422


def test_exporter_conversation_introuvable_retourne_404(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    monkeypatch.setattr(api_module, "exporter_conversation", lambda tid: None)

    reponse = client.get("/conversations/inconnue/export", headers={"X-API-Key": "bonne-cle"})

    assert reponse.status_code == 404

def test_exporter_conversation_existante_retourne_le_document(monkeypatch):
    monkeypatch.setattr(settings, "api_key_value", "bonne-cle")
    doc = {"session_id": "s1", "type": "conversation", "tache": "x"}
    monkeypatch.setattr(api_module, "exporter_conversation", lambda tid: doc)

    reponse = client.get("/conversations/s1/export", headers={"X-API-Key": "bonne-cle"})

    assert reponse.status_code == 200
    assert reponse.json() == doc


@pytest.mark.asyncio
async def test_executer_tache_cas_nominal(monkeypatch):
    """L'équipe produit 2 messages puis un TaskResult final (ignoré) — le statut
    doit passer à TERMINE et la conversation être journalisée."""
    # session_memory est un singleton partagé ; on force le mode local (dict + vrai
    # JSON) pour ce test, sinon le faux client Redis global renvoie des MagicMock
    # à la place de chaînes JSON et json.loads() plante.
    monkeypatch.setattr(api_module.session_memory, "_redis", None)

    class FauxTaskResult:
        pass

    class FauxMessage:
        def __init__(self, source, content):
            self.source = source
            self.content = content

    async def faux_run_stream(task):
        yield FauxMessage("Agent_Orchestrateur", "Plan établi.")
        yield FauxMessage("Agent_Codeur", "def fib(): ...")
        yield FauxTaskResult()

    monkeypatch.setattr(api_module, "TaskResult", FauxTaskResult)
    mock_equipe = MagicMock()
    mock_equipe.run_stream = faux_run_stream
    monkeypatch.setattr(api_module, "creer_equipe", lambda: mock_equipe)
    mock_log_conversation = MagicMock()
    monkeypatch.setattr(api_module, "log_conversation", mock_log_conversation)

    await api_module.executer_tache("task-1", "Écris Fibonacci")

    assert api_module.session_memory.get("task-1", "statut") == "TERMINE"
    assert api_module.session_memory.get("task-1", "reponse") == "def fib(): ..."
    mock_log_conversation.assert_called_once()

@pytest.mark.asyncio
async def test_executer_tache_cas_erreur(monkeypatch):
    """Si l'équipe lève une exception, le statut doit passer à ERREUR sans jamais
    propager l'exception (l'API doit rester disponible pour les autres tâches)."""
    monkeypatch.setattr(api_module.session_memory, "_redis", None)

    async def faux_run_stream_qui_echoue(task):
        raise RuntimeError("Panne Azure OpenAI")
        yield

    mock_equipe = MagicMock()
    mock_equipe.run_stream = faux_run_stream_qui_echoue
    monkeypatch.setattr(api_module, "creer_equipe", lambda: mock_equipe)

    await api_module.executer_tache("task-2", "Tâche qui va échouer")

    assert api_module.session_memory.get("task-2", "statut") == "ERREUR"
    assert "Panne Azure OpenAI" in api_module.session_memory.get("task-2", "reponse")
