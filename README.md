# Système Multi-Agents — Smartovate Ltd

PoC d'automatisation de workflows cognitifs basé sur **Microsoft AutoGen v0.4+** et
**Azure OpenAI (GPT-4o)**, réalisé dans le cadre du stage de Haitham Dhaimi
(SUPTECH-SANTE, Juillet–Août 2026, encadrant : M. Abdelkhalik Bakkari).

## Architecture

Topologie **hub-and-spoke** :

```
Utilisateur --> API FastAPI (/tasks) --> Agent_Orchestrateur
                                              |
                                    délègue via SelectorGroupChat
                                              |
                            +---------------------------------+
                            |                                 |
                       Agent_Codeur  <----------->     Agent_Reviseur
                            |                                 |
                            +---------------------------------+
                                              |
                                       Agent_Critique
                                (validation + filtrage PII)
                                              |
                                    réponse consolidée
```

## Structure du projet

```
smartovate-multiagent/
├── agents/
│   ├── orchestrateur.py   # Décomposition + délégation
│   ├── specialiste.py     # Agent_Codeur, Agent_Reviseur
│   ├── critique.py        # Contrôle qualité + PII
│   └── team.py            # Assemblage du SelectorGroupChat
├── tools/
│   └── base_tools.py      # Outils @autogen.tool (timeout 30s + retry)
├── memory/
│   ├── redis_memory.py    # Mémoire de session (repli local si Azure absent)
│   └── cosmos_logger.py   # Logs d'audit (repli local : logs/conversations.jsonl)
├── config/
│   ├── settings.py        # Config centralisée (pydantic-settings)
│   └── model_client.py    # Factory clients Azure OpenAI
├── api/
│   └── main.py            # FastAPI - POST /tasks
├── tests/
│   ├── test_connection.py # Validation connexion Azure OpenAI (US 1.1)
│   └── test_tools.py      # Tests unitaires des outils
├── .env.example
├── requirements.txt
└── README.md
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis renseigner vos clés Azure OpenAI / Cosmos / Redis
```

## Validation de la connexion Azure OpenAI (US 1.1)

```bash
python -m tests.test_connection
```

## Lancer l'API

```bash
uvicorn api.main:app --reload
```

Puis tester :

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"task": "Écris une fonction Python qui calcule la suite de Fibonacci."}'
```

## Tests unitaires

```bash
pytest tests/ -v
```

## Points d'attention sécurité (à traiter avant mise en production)

- `tools.base_tools.run_python_snippet` utilise un `exec` restreint à des fins de
  démonstration. **Doit être remplacé** par une exécution Docker isolée
  (`use_docker=True`) avant toute utilisation réelle — cf. Bug 3 du cahier des charges.
- `tools.base_tools.detect_pii` est une détection regex basique. À renforcer avec
  Azure AI Language (PII Detection) en production.

## Prochaines étapes (Sprint 3)

- Intégration mémoire Redis (session) et Cosmos DB (audit/logs).
- Couverture de tests unitaires ≥ 80 %.
- Interface Streamlit (US 3.2).
