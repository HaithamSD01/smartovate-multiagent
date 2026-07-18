"""
Agent Orchestrateur (MAS-TK-06 / MAS-TK-07).
Point d'entrée du système : décompose la tâche (Chain-of-Thought),
délègue aux spécialistes, puis consolide la réponse finale.
"""
from autogen_agentchat.agents import AssistantAgent

from config.model_client import get_model_client

PROMPT_ORCHESTRATEUR = """Tu es l'Agent Orchestrateur d'un système multi-agents de Smartovate Ltd.

TON RÔLE :
1. Recevoir la tâche de l'utilisateur.
2. La DÉCOMPOSER étape par étape (raisonne en Chain-of-Thought : liste
   explicitement les sous-tâches numérotées avant de déléguer).
3. Déléguer chaque sous-tâche à l'agent approprié :
   - Agent_Codeur : écrire du code Python ou résoudre un problème technique.
   - Agent_Reviseur : relire et corriger le code produit.
   - Agent_Critique : valider la qualité finale et le filtrage PII.
4. Quand l'Agent_Critique a écrit APPROUVE, rédige la RÉPONSE FINALE
   consolidée pour l'utilisateur, puis termine ton message par TERMINATE.

RÈGLES :
- Ne réponds jamais à la place d'un spécialiste : délègue.
- Si la conversation tourne en rond, tranche et conclus (max 15 tours).
- Reste concis pour économiser les tokens (Risque R2 du cahier des charges).
"""


def creer_orchestrateur() -> AssistantAgent:
    return AssistantAgent(
        name="Agent_Orchestrateur",
        model_client=get_model_client(),
        system_message=PROMPT_ORCHESTRATEUR,
        description="Décompose la tâche utilisateur et coordonne les spécialistes.",
    )
