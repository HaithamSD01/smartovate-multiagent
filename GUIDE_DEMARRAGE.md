# Guide de démarrage rapide — comment tout s'articule

## 1. Les documents Smartovate : qui fait quoi ?

| Document | Rôle | Comment tu l'utilises |
|---|---|---|
| **CDC_Haitham_DHAIMI.docx** (cahier des charges) | Le **contrat** : exigences (F1–F4), backlog Jira (MAS-TK-01 → 18), risques, critères de notation | C'est ta **checklist**. Chaque fichier de ce projet référence en commentaire la tâche MAS-TK qu'il couvre. |
| **Rapport de démarrage** | Livrable Sprint 1 (déjà remis ✅) | Justifie les choix techniques auprès de l'encadrant. |
| **UML_Diagramme.pdf** | La **conception** | Le code suit ces diagrammes : classes (n°2) → `agents/`, séquence (n°4) → `api/main.py`, activités n°7 → `tools/base_tools.py`. |
| **README.md / requirements.txt** | L'état du code | Le point de départ que ce prototype complète. |

En résumé : **CDC = quoi faire**, **UML = comment c'est conçu**, **ce code = la réalisation**, sprint par sprint.

## 2. Redis vs Cosmos DB (la question classique)

- **Redis = mémoire de session (court-terme)** → `memory/redis_memory.py`.
  Pendant qu'une tâche tourne, les agents partagent l'état (statut, tâche,
  compteur de tours). Tout expire après 1h (TTL). Comme un post-it.
- **Cosmos DB = archive (long-terme)** → `memory/cosmos_logger.py`.
  Chaque conversation et chaque appel d'outil y sont conservés pour
  l'audit et l'export JSON (US-04). Comme un classeur d'archives.

👉 **Pas encore de compte Azure ?** Le code bascule tout seul en mode local :
Redis → dictionnaire Python en RAM, Cosmos → fichier `logs/conversations.jsonl`.
Tu peux donc développer et tester GRATUITEMENT dès maintenant.

## 3. Lancer le projet en local

```bash
# 1. Environnement Python
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env             # renseigner tes clés Azure OpenAI

# 3. Valider la connexion Azure (US 1.1)
python -m tests.test_connection

# 4. Tests unitaires (objectif ≥ 80 % au Sprint 3)
pytest tests/ -v

# 5. Lancer l'API
uvicorn api.main:app --reload
# Swagger auto : http://localhost:8000/docs
```

Tester une tâche :
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" -H "X-API-Key: dev-local-key" \
  -d '{"task": "Écris une fonction Python qui calcule la suite de Fibonacci."}'
# → récupère le task_id, puis :
curl http://localhost:8000/tasks/<task_id> -H "X-API-Key: dev-local-key"
```

(Optionnel) Redis local en une commande : `docker run -d -p 6379:6379 redis`

## 4. Workflow GitHub du stage

```bash
git init
git add .
git commit -m "Sprint 2: agents + outils + API FastAPI"
git branch -M main
git remote add origin https://github.com/TON_COMPTE/smartovate-multiagent.git
git push -u origin main
```

Ensuite, une branche par tâche Jira :
```bash
git checkout -b feature/MAS-TK-14-memoire-redis
# ... tu codes ...
git add . && git commit -m "MAS-TK-14: gestionnaire de mémoire partagée Redis"
git push -u origin feature/MAS-TK-14-memoire-redis
# → Pull Request sur GitHub → merge dans main
```

⚠️ Le `.gitignore` exclut `.env` : **jamais de clés Azure sur GitHub** (critère de notation !).

## 5. Où tu en es dans le planning

- ✅ Sprint 1 : rapport de démarrage, UML, structure
- 🔵 Sprint 2 (en cours) : **ce prototype** = Orchestrateur + Codeur/Réviseur + Critique + GroupChat
- ⏭️ Sprint 3 : brancher le vrai Redis/Cosmos Azure, couverture tests ≥ 80 %, interface Streamlit
- ⏭️ Sprint 4 : Docker (fichier déjà fourni), déploiement Azure Container Apps, soutenance
