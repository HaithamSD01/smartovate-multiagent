# Système Multi-Agents — Smartovate Ltd

**Automatisation de workflows cognitifs par IA générative, du prototype au déploiement cloud.**

![Python](https://img.shields.io/badge/Python-3.14-blue)
![AutoGen](https://img.shields.io/badge/Microsoft-AutoGen%20v0.4+-0078D4)
![Azure](https://img.shields.io/badge/Azure-Container%20Apps-0078D4)
![Coverage](https://img.shields.io/badge/couverture%20tests-100%25-brightgreen)
![Licence](https://img.shields.io/badge/licence-en%20attente-lightgrey)

---

## Vue d'ensemble

Un système multi-agents où quatre agents IA collaborent pour traiter une
tâche de bout en bout : décomposition, production, revue et validation —
plutôt qu'un modèle unique qui produit et vérifie son propre travail.

Construit avec **Microsoft AutoGen v0.4+** et **Azure OpenAI (GPT-4o)**,
exposé via une API REST et déployé en production sur **Azure Container
Apps**.

Projet réalisé en autonomie complète — cahier des charges, architecture,
développement, tests, sécurité, déploiement — dans le cadre d'un stage chez
[Smartovate Ltd](https://smartovate.com), partenaire Microsoft spécialisé
en IA et cloud computing.

---

## Architecture

Topologie **hub-and-spoke** : un agent central décompose et délègue, deux
agents spécialisés produisent et relisent, un agent de contrôle valide
avant livraison.

```
Utilisateur --> API FastAPI (/tasks) --> Agent Orchestrateur
                                               |
                                    délègue via SelectorGroupChat
                                               |
                        +----------------------------------------+
                        |                                        |
                  Agent Codeur  <-------------------->  Agent Réviseur
                        |                                        |
                        +----------------------------------------+
                                               |
                                        Agent Critique
                                (validation + filtrage PII)
                                               |
                                       réponse consolidée
```

La sélection du prochain agent à intervenir est dynamique (le modèle
choisit qui parle ensuite). Deux garde-fous protègent contre les boucles
infinies : un mot-clé de terminaison explicite et un plafond de messages.

---

## Résultats

| Indicateur | Valeur |
|---|---|
| Backlog du cahier des charges | 18/18 tâches livrées |
| Sprints | 4/4 clôturés en avance sur le planning |
| Couverture de tests unitaires | **100 %** (269/269 lignes, 63 tests) — objectif fixé : 80 % |
| Taux de succès (jeu de tâches de référence) | 15/15 exécutions |
| Latence médiane en production | 47,3 s (seuil requis : < 60 s) |

Le protocole de mesure complet, les résultats détaillés par tâche et la
méthodologie de test sont documentés dans le rapport de stage joint au
dépôt.

---

## Stack technique

| Domaine | Technologies |
|---|---|
| Orchestration multi-agents | Microsoft AutoGen v0.4+ (`SelectorGroupChat`) |
| Modèle de langage | Azure OpenAI GPT-4o |
| API | FastAPI, Uvicorn, authentification par clé |
| Mémoire de session | Azure Managed Redis (Enterprise, TLS) |
| Persistance longue durée | Azure Cosmos DB (NoSQL, serverless) |
| Interface de suivi | Streamlit |
| Conteneurisation | Docker, Azure Container Registry |
| Déploiement | Azure Container Apps |
| Tests | pytest, pytest-cov |
| Suivi de projet | Jira (backlog EPICs / Stories / Tasks) |

---

## Démarrage rapide

```bash
# 1. Cloner le dépôt
git clone https://github.com/HaithamSD01/smartovate-multiagent.git
cd smartovate-multiagent

# 2. Créer l'environnement virtuel et installer les dépendances
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
copy .env.example .env      # puis renseigner les valeurs réelles

# 4. Lancer l'API
uvicorn api.main:app --reload --port 8000

# 5. (optionnel) Lancer l'interface de suivi, dans un second terminal
streamlit run streamlit_app.py
```

L'API est alors disponible sur `http://localhost:8000/docs` (documentation
Swagger générée automatiquement).

> Le fichier `.env` n'est jamais versionné. Toutes les clés (Azure OpenAI,
> Cosmos DB, Redis, clé d'API applicative) doivent être renseignées
> localement à partir de `.env.example`.

---

## API

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/tasks` | Soumet une tâche en langage naturel |
| `GET` | `/tasks/{id}` | Consulte l'état et le résultat d'une tâche |
| `GET` | `/conversations/{id}/export` | Exporte l'historique complet au format JSON |
| `GET` | `/health` | Contrôle de santé du service |

Toutes les routes métier sont protégées par une clé d'API transmise dans
l'en-tête `X-API-Key`.

---

## Tests et qualité

```bash
pytest --cov --cov-report=term-missing
```

Le périmètre de mesure de la couverture est figé dans `.coveragerc` :
`agents/`, `tools/`, `config/`, `memory/` et `api/`, soit 269 lignes. En
sont explicitement exclus l'interface Streamlit (hors périmètre du cahier
des charges) et le script de validation manuelle de la connexion, qui
constitue une preuve documentée plutôt qu'un module à couvrir.

---

## Structure du projet

```
smartovate-multiagent/
├── agents/          # Orchestrateur, Codeur, Réviseur, Critique
├── api/             # Exposition FastAPI
├── config/          # Configuration (pydantic-settings)
├── memory/          # Couches Redis (session) et Cosmos DB (persistance)
├── tools/           # Outils sécurisés (timeout, retry, journalisation)
├── tests/           # Suite pytest (63 tests) + script de benchmark
├── streamlit_app.py # Interface de suivi en temps réel
├── Dockerfile
└── .coveragerc      # Périmètre de mesure de couverture, figé et versionné
```

---

## Limites connues et pistes d'amélioration

Documentées en détail dans le rapport de stage, dont voici la synthèse :

- **Exécution de code en mode démonstration.** La version prévue pour la
  production (isolation via Docker) est incompatible avec Azure Container
  Apps, qui ne supporte pas le Docker-in-Docker. Solution identifiée :
  [Azure Container Apps Dynamic
  Sessions](https://learn.microsoft.com/azure/container-apps/sessions).
- **Contrôle de santé statique.** `/health` confirme que le service répond
  mais ne vérifie pas encore l'état réel des dépendances (Cosmos DB, Redis,
  Azure OpenAI).
- **Observabilité limitée.** Pas de vue centralisée du parcours d'une tâche
  à travers les quatre agents — utile pour le diagnostic et pour affiner
  la mesure de performance.
- **Écarts assumés vis-à-vis du cahier des charges initial** (agent
  Human-in-the-Loop, certains patrons de topologie) : justifiés section par
  section dans le rapport plutôt que passés sous silence.

---

## Contexte du projet

Projet réalisé par **Haitham Dhaimi**, étudiant en 1ʳᵉ année de cycle
ingénieur (Génie digital et Intelligence artificielle en santé) à
**SUPTECH-SANTÉ** / **Université Internationale Bleue**, dans le cadre d'un
stage chez **Smartovate Ltd** (juillet–août 2026), sous l'encadrement du
Dr. Abdelkhalek Bakkari.

Le rapport de stage complet, incluant la méthodologie détaillée, l'ensemble
des incidents rencontrés et leur résolution, et la traçabilité complète
entre le cahier des charges et le code produit, est disponible dans ce
dépôt.

---

## Licence

En cours de définition avec l'entreprise d'accueil.
