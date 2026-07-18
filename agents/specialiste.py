"""
Agents Spécialistes (MAS-TK-09 / MAS-TK-10).
Chaque spécialiste a : un prompt système distinct + des outils limités
à son périmètre (CDC §2.1 - F1).
"""
from autogen_agentchat.agents import AssistantAgent

from config.model_client import get_model_client
from tools.base_tools import calculer, run_python_snippet

PROMPT_CODEUR = """Tu es Agent_Codeur, spécialiste en développement Python chez Smartovate.
- Tu reçois des sous-tâches de l'Agent_Orchestrateur.
- Tu écris du code Python clair, typé et commenté.
- Tu peux utiliser tes outils : `calculer` (arithmétique) et
  `run_python_snippet` (exécution de démonstration).
- Une fois ton code écrit, demande explicitement une revue à Agent_Reviseur.
- Domaine limité : tu ne fais QUE du code. Pas de validation qualité (rôle du Critique).
"""

PROMPT_REVISEUR = """Tu es Agent_Reviseur, spécialiste en revue de code chez Smartovate.
- Tu analyses le code produit par Agent_Codeur : bugs, sécurité, lisibilité, PEP 8.
- Si tu trouves des problèmes : liste-les précisément et renvoie à Agent_Codeur.
- Si le code est correct : écris "CODE VALIDE" et transmets à Agent_Critique.
- Sois exigeant mais bref (2 allers-retours maximum avec le Codeur).
"""


def creer_codeur() -> AssistantAgent:
    return AssistantAgent(
        name="Agent_Codeur",
        model_client=get_model_client(temperature=0.3),
        system_message=PROMPT_CODEUR,
        tools=[calculer, run_python_snippet],
        description="Écrit du code Python et utilise des outils de calcul/exécution.",
    )


def creer_reviseur() -> AssistantAgent:
    return AssistantAgent(
        name="Agent_Reviseur",
        model_client=get_model_client(temperature=0.2),
        system_message=PROMPT_REVISEUR,
        description="Relit le code du Codeur et exige des corrections si nécessaire.",
    )
