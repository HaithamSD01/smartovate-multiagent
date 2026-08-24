"""
Tests unitaires de l'assemblage de l'équipe (agents/team.py).
"""
from unittest.mock import MagicMock

import agents.team as team_module
from agents.team import creer_equipe
from config.settings import settings


def test_creer_equipe_assemble_les_quatre_agents(monkeypatch):
    """creer_equipe() doit instancier les 4 agents (topologie hub-and-spoke)
    et les passer dans le bon ordre à SelectorGroupChat."""
    instance_orchestrateur = MagicMock(name="orchestrateur")
    instance_codeur = MagicMock(name="codeur")
    instance_reviseur = MagicMock(name="reviseur")
    instance_critique = MagicMock(name="critique")

    monkeypatch.setattr(team_module, "creer_orchestrateur", MagicMock(return_value=instance_orchestrateur))
    monkeypatch.setattr(team_module, "creer_codeur", MagicMock(return_value=instance_codeur))
    monkeypatch.setattr(team_module, "creer_reviseur", MagicMock(return_value=instance_reviseur))
    monkeypatch.setattr(team_module, "creer_critique", MagicMock(return_value=instance_critique))
    monkeypatch.setattr(team_module, "get_model_client", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(team_module, "TextMentionTermination", MagicMock())
    monkeypatch.setattr(team_module, "MaxMessageTermination", MagicMock())
    mock_selector = MagicMock()
    monkeypatch.setattr(team_module, "SelectorGroupChat", mock_selector)

    creer_equipe()

    args, kwargs = mock_selector.call_args
    assert kwargs["participants"] == [instance_orchestrateur, instance_codeur, instance_reviseur, instance_critique]
    assert kwargs["allow_repeated_speaker"] is False

def test_creer_equipe_terminaison_utilise_le_mot_cle_terminate(monkeypatch):
    """La condition textuelle doit être exactement 'TERMINATE' (protocole entre agents)."""
    for fn in ("creer_orchestrateur", "creer_codeur", "creer_reviseur", "creer_critique"):
        monkeypatch.setattr(team_module, fn, MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(team_module, "get_model_client", MagicMock(return_value=MagicMock()))
    mock_text_term = MagicMock(name="TextMentionTermination")
    monkeypatch.setattr(team_module, "TextMentionTermination", mock_text_term)
    monkeypatch.setattr(team_module, "MaxMessageTermination", MagicMock())
    monkeypatch.setattr(team_module, "SelectorGroupChat", MagicMock())

    creer_equipe()

    mock_text_term.assert_called_once_with("TERMINATE")

def test_creer_equipe_terminaison_utilise_max_turns_des_settings(monkeypatch):
    """Le plafond de messages (watchdog risque R1) doit venir de settings.max_turns,
    pas d'une valeur codée en dur dans team.py."""
    for fn in ("creer_orchestrateur", "creer_codeur", "creer_reviseur", "creer_critique"):
        monkeypatch.setattr(team_module, fn, MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(team_module, "get_model_client", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(team_module, "TextMentionTermination", MagicMock())
    mock_max_term = MagicMock(name="MaxMessageTermination")
    monkeypatch.setattr(team_module, "MaxMessageTermination", mock_max_term)
    monkeypatch.setattr(team_module, "SelectorGroupChat", MagicMock())

    creer_equipe()

    mock_max_term.assert_called_once_with(max_messages=settings.max_turns)

def test_creer_equipe_retourne_l_instance_creee(monkeypatch):
    for fn in ("creer_orchestrateur", "creer_codeur", "creer_reviseur", "creer_critique"):
        monkeypatch.setattr(team_module, fn, MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(team_module, "get_model_client", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(team_module, "TextMentionTermination", MagicMock())
    monkeypatch.setattr(team_module, "MaxMessageTermination", MagicMock())
    instance_attendue = MagicMock()
    monkeypatch.setattr(team_module, "SelectorGroupChat", MagicMock(return_value=instance_attendue))

    resultat = creer_equipe()

    assert resultat is instance_attendue
