"""
Assemblage du GroupChat (MAS-TK-08).

Pattern retenu : SelectorGroupChat d'AutoGen v0.4 — le LLM choisit
automatiquement le prochain agent à parler (voir diagramme de séquence n°4).

Conditions de terminaison (CDC §2.3 - F3, Risque R1) :
  - le mot-clé TERMINATE écrit par l'Orchestrateur, OU
  - max_turns = 15 tours (watchdog anti boucle infinie).
"""
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat

from agents.critique import creer_critique
from agents.orchestrateur import creer_orchestrateur
from agents.specialiste import creer_codeur, creer_reviseur
from config.model_client import get_model_client
from config.settings import settings


def creer_equipe() -> SelectorGroupChat:
    orchestrateur = creer_orchestrateur()
    codeur = creer_codeur()
    reviseur = creer_reviseur()
    critique = creer_critique()

    terminaison = (
        TextMentionTermination("TERMINATE")
        | MaxMessageTermination(max_messages=settings.max_turns)
    )

    return SelectorGroupChat(
        participants=[orchestrateur, codeur, reviseur, critique],
        model_client=get_model_client(),   # le sélecteur de locuteur utilise aussi GPT-4o
        termination_condition=terminaison,
        allow_repeated_speaker=False,
    )
