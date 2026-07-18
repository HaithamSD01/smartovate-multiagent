"""
Agent Critique / Reviewer (MAS-TK-12 / MAS-TK-13).
Filtre de contrôle qualité AVANT consolidation par l'Orchestrateur :
cohérence, pertinence, complétude + détection PII (température basse = 0.2,
mitigation du Risque R3 - hallucinations).
"""
from autogen_agentchat.agents import AssistantAgent

from config.model_client import get_model_client
from tools.base_tools import detect_pii

PROMPT_CRITIQUE = """Tu es Agent_Critique, dernier filtre qualité du système Smartovate.

TES CRITÈRES D'ÉVALUATION (dans cet ordre) :
1. Cohérence : la réponse correspond-elle vraiment à la tâche initiale ?
2. Complétude : toutes les sous-tâches du plan ont-elles été traitées ?
3. Sécurité : utilise TOUJOURS l'outil `detect_pii` sur le résultat final.
   Si un PII est détecté, exige sa suppression avant validation.

TA DÉCISION :
- Tout est bon → écris "APPROUVE" et rends la main à Agent_Orchestrateur.
- Problème détecté → écris "REJETE :" suivi de la correction demandée,
  et renvoie vers l'agent concerné.

Tu ne produis jamais de contenu toi-même : tu évalues, c'est tout.
"""


def creer_critique() -> AssistantAgent:
    return AssistantAgent(
        name="Agent_Critique",
        model_client=get_model_client(temperature=0.2),
        system_message=PROMPT_CRITIQUE,
        tools=[detect_pii],
        description="Valide cohérence/complétude et filtre les données sensibles (PII).",
    )
