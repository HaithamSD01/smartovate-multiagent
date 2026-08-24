"""
Tests unitaires de l'Agent Critique (agents/critique.py).
"""
from unittest.mock import MagicMock

import agents.critique as critique_module
from agents.critique import creer_critique, PROMPT_CRITIQUE
from tools.base_tools import detect_pii


def test_creer_critique_configure_l_agent_correctement(monkeypatch):
    """Le Critique doit être créé avec temperature=0.2 (mitigation risque R3)
    et l'outil detect_pii (dernier filtre avant consolidation)."""
    mock_client = MagicMock()
    mock_get_model_client = MagicMock(return_value=mock_client)
    mock_assistant_agent = MagicMock()
    monkeypatch.setattr(critique_module, "get_model_client", mock_get_model_client)
    monkeypatch.setattr(critique_module, "AssistantAgent", mock_assistant_agent)

    creer_critique()

    mock_get_model_client.assert_called_once_with(temperature=0.2)
    mock_assistant_agent.assert_called_once_with(
        name="Agent_Critique",
        model_client=mock_client,
        system_message=PROMPT_CRITIQUE,
        tools=[detect_pii],
        description="Valide cohérence/complétude et filtre les données sensibles (PII).",
    )

def test_creer_critique_retourne_l_instance_creee(monkeypatch):
    instance_attendue = MagicMock()
    monkeypatch.setattr(critique_module, "get_model_client", lambda temperature=None: MagicMock())
    monkeypatch.setattr(critique_module, "AssistantAgent", MagicMock(return_value=instance_attendue))

    resultat = creer_critique()

    assert resultat is instance_attendue


# --- Prompt ---------------------------------------------------------------
def test_prompt_critique_contient_approuve():
    assert "APPROUVE" in PROMPT_CRITIQUE

def test_prompt_critique_contient_rejete():
    assert "REJETE" in PROMPT_CRITIQUE

def test_prompt_critique_mentionne_detect_pii():
    """Vérifie que le prompt impose bien l'usage de l'outil de détection PII
    (exigence de sécurité, distincte du simple wiring des tools=[...])."""
    assert "detect_pii" in PROMPT_CRITIQUE
