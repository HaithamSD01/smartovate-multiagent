"""
Tests unitaires de l'Agent Orchestrateur (agents/orchestrateur.py).
"""
from unittest.mock import MagicMock

import agents.orchestrateur as orchestrateur_module
from agents.orchestrateur import creer_orchestrateur, PROMPT_ORCHESTRATEUR


def test_creer_orchestrateur_configure_l_agent_correctement(monkeypatch):
    """creer_orchestrateur() doit construire l'AssistantAgent avec les bons paramètres,
    sans dépendre du réseau ni de la validation interne d'AutoGen."""
    mock_client = MagicMock()
    mock_assistant_agent = MagicMock()
    monkeypatch.setattr(orchestrateur_module, "get_model_client", lambda: mock_client)
    monkeypatch.setattr(orchestrateur_module, "AssistantAgent", mock_assistant_agent)

    creer_orchestrateur()

    mock_assistant_agent.assert_called_once_with(
        name="Agent_Orchestrateur",
        model_client=mock_client,
        system_message=PROMPT_ORCHESTRATEUR,
        description="Décompose la tâche utilisateur et coordonne les spécialistes.",
    )

def test_creer_orchestrateur_retourne_l_instance_creee(monkeypatch):
    """La fonction doit retourner exactement ce que produit le constructeur AssistantAgent."""
    instance_attendue = MagicMock()
    monkeypatch.setattr(orchestrateur_module, "get_model_client", lambda: MagicMock())
    monkeypatch.setattr(orchestrateur_module, "AssistantAgent", MagicMock(return_value=instance_attendue))

    resultat = creer_orchestrateur()

    assert resultat is instance_attendue

def test_prompt_orchestrateur_contient_terminate():
    """Le prompt système doit contenir TERMINATE (mitigation risque R1, boucles infinies)."""
    assert "TERMINATE" in PROMPT_ORCHESTRATEUR
