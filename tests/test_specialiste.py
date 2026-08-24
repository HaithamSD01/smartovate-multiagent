"""
Tests unitaires des Agents Spécialistes (agents/specialiste.py).
"""
from unittest.mock import MagicMock

import agents.specialiste as specialiste_module
from agents.specialiste import creer_codeur, creer_reviseur, PROMPT_CODEUR, PROMPT_REVISEUR
from tools.base_tools import calculer, run_python_snippet


# --- Agent_Codeur ------------------------------------------------------------
def test_creer_codeur_configure_l_agent_correctement(monkeypatch):
    """Le Codeur doit être créé avec temperature=0.3 et ses deux outils."""
    mock_client = MagicMock()
    mock_get_model_client = MagicMock(return_value=mock_client)
    mock_assistant_agent = MagicMock()
    monkeypatch.setattr(specialiste_module, "get_model_client", mock_get_model_client)
    monkeypatch.setattr(specialiste_module, "AssistantAgent", mock_assistant_agent)

    creer_codeur()

    mock_get_model_client.assert_called_once_with(temperature=0.3)
    mock_assistant_agent.assert_called_once_with(
        name="Agent_Codeur",
        model_client=mock_client,
        system_message=PROMPT_CODEUR,
        tools=[calculer, run_python_snippet],
        description="Écrit du code Python et utilise des outils de calcul/exécution.",
    )

def test_creer_codeur_retourne_l_instance_creee(monkeypatch):
    instance_attendue = MagicMock()
    monkeypatch.setattr(specialiste_module, "get_model_client", lambda temperature=None: MagicMock())
    monkeypatch.setattr(specialiste_module, "AssistantAgent", MagicMock(return_value=instance_attendue))

    resultat = creer_codeur()

    assert resultat is instance_attendue


# --- Agent_Reviseur -----------------------------------------------------------
def test_creer_reviseur_configure_l_agent_correctement(monkeypatch):
    """Le Réviseur doit être créé avec temperature=0.2 (mitigation risque R3, hallucinations)
    et sans outils propres."""
    mock_client = MagicMock()
    mock_get_model_client = MagicMock(return_value=mock_client)
    mock_assistant_agent = MagicMock()
    monkeypatch.setattr(specialiste_module, "get_model_client", mock_get_model_client)
    monkeypatch.setattr(specialiste_module, "AssistantAgent", mock_assistant_agent)

    creer_reviseur()

    mock_get_model_client.assert_called_once_with(temperature=0.2)
    mock_assistant_agent.assert_called_once_with(
        name="Agent_Reviseur",
        model_client=mock_client,
        system_message=PROMPT_REVISEUR,
        description="Relit le code du Codeur et exige des corrections si nécessaire.",
    )

def test_creer_reviseur_retourne_l_instance_creee(monkeypatch):
    instance_attendue = MagicMock()
    monkeypatch.setattr(specialiste_module, "get_model_client", lambda temperature=None: MagicMock())
    monkeypatch.setattr(specialiste_module, "AssistantAgent", MagicMock(return_value=instance_attendue))

    resultat = creer_reviseur()

    assert resultat is instance_attendue


# --- Prompts -------------------------------------------------------------------
def test_prompt_reviseur_contient_code_valide():
    """Le mot-clé de validation attendu par le protocole entre agents."""
    assert "CODE VALIDE" in PROMPT_REVISEUR
