"""
API REST d'exposition (MAS-TK-16 / MAS-TK-17).

Endpoints du cahier des charges :
  POST /tasks                      → soumettre une tâche (US-01)
  GET  /tasks/{id}                 → consulter l'état / le résultat
  GET  /conversations/{id}/export  → export JSON de l'historique (US-04)

Sécurité minimale du prototype : API Key dans l'en-tête X-API-Key
(à remplacer par Azure AD en production — CDC §2.3).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from agents.team import creer_equipe
from config.settings import settings
from memory.cosmos_logger import exporter_conversation, log_conversation
from memory.redis_memory import session_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartovate.api")

app = FastAPI(
    title="Smartovate Multi-Agent System",
    description="PoC AutoGen v0.4 + Azure OpenAI — stage Haitham Dhaimi (2026)",
    version="0.2.0",
)


# ---------------------------------------------------------------------------
# Authentification (MAS-TK-17)
# ---------------------------------------------------------------------------
def verifier_api_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != settings.api_key_value:
        raise HTTPException(status_code=401, detail="API Key invalide ou absente.")


# ---------------------------------------------------------------------------
# Schémas Pydantic
# ---------------------------------------------------------------------------
class TaskRequest(BaseModel):
    task: str = Field(..., min_length=5, description="Tâche en langage naturel.")


class TaskResponse(BaseModel):
    task_id: str
    statut: str
    message: str


# ---------------------------------------------------------------------------
# Exécution asynchrone de l'équipe multi-agents
# ---------------------------------------------------------------------------
async def executer_tache(task_id: str, tache: str) -> None:
    session_memory.set(task_id, "statut", "EN_COURS")   # état partagé via Redis
    session_memory.set(task_id, "tache", tache)
    try:
        equipe = creer_equipe()
        resultat = await equipe.run(task=tache)

        messages = [
            {"source": getattr(m, "source", "?"), "contenu": str(getattr(m, "content", m))}
            for m in resultat.messages
        ]
        reponse_finale = messages[-1]["contenu"] if messages else ""

        session_memory.set(task_id, "statut", "TERMINE")
        session_memory.set(task_id, "reponse", reponse_finale)
        log_conversation(task_id, tache, messages, reponse_finale)  # → Cosmos DB
    except Exception as exc:
        logger.exception("Échec de la tâche %s", task_id)
        session_memory.set(task_id, "statut", "ERREUR")
        session_memory.set(task_id, "reponse", str(exc))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/tasks", response_model=TaskResponse, dependencies=[Depends(verifier_api_key)])
async def soumettre_tache(req: TaskRequest, background: BackgroundTasks) -> TaskResponse:
    task_id = str(uuid.uuid4())
    background.add_task(executer_tache, task_id, req.task)
    return TaskResponse(
        task_id=task_id,
        statut="EN_ATTENTE",
        message=f"Tâche acceptée. Suivez-la via GET /tasks/{task_id}",
    )


@app.get("/tasks/{task_id}", dependencies=[Depends(verifier_api_key)])
async def consulter_tache(task_id: str) -> dict:
    statut = session_memory.get(task_id, "statut")
    if statut is None:
        raise HTTPException(status_code=404, detail="Tâche inconnue (ou session expirée).")
    return {
        "task_id": task_id,
        "statut": statut,
        "tache": session_memory.get(task_id, "tache"),
        "reponse": session_memory.get(task_id, "reponse"),
    }


@app.get("/conversations/{task_id}/export", dependencies=[Depends(verifier_api_key)])
async def exporter(task_id: str) -> dict:
    doc = exporter_conversation(task_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    return doc


@app.get("/health")
async def health() -> dict:
    return {"statut": "OK", "service": "smartovate-mas"}
