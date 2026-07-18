"""
Mémoire LONG-TERME / auditabilité (CDC §2.4 - F4 et §2.2 - F2).

Rôle de Cosmos DB dans ce projet :
  → base NoSQL Azure qui conserve DURABLEMENT :
      1. l'historique complet de chaque conversation (US-04 : export JSON),
      2. le journal de chaque appel d'outil (input, output, durée, statut).
  → contrairement à Redis (volatile, TTL courte), Cosmos garde tout :
    c'est ce qui permet l'audit, l'analyse et le futur fine-tuning.

Mode dégradé : sans compte Cosmos configuré dans .env, tout est écrit dans
logs/conversations.jsonl — le prototype reste testable gratuitement en local.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config.settings import settings

logger = logging.getLogger("smartovate.cosmos")

_FICHIER_LOCAL = Path("logs/conversations.jsonl")
_container = None


def _get_container():
    """Connexion paresseuse au container Cosmos DB (créé si absent)."""
    global _container
    if _container is not None:
        return _container
    if not settings.cosmos_endpoint or not settings.cosmos_key:
        return None
    try:
        from azure.cosmos import CosmosClient, PartitionKey

        client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
        db = client.create_database_if_not_exists(settings.cosmos_database)
        _container = db.create_container_if_not_exists(
            id=settings.cosmos_container,
            partition_key=PartitionKey(path="/session_id"),
        )
        logger.info("Cosmos DB connecté : persistance long-terme active.")
        return _container
    except Exception as exc:
        logger.warning("Cosmos DB indisponible (%s) → journal local JSONL.", exc)
        return None


def _ecrire(document: dict) -> None:
    document.setdefault("id", str(uuid.uuid4()))
    document["horodatage"] = datetime.now(timezone.utc).isoformat()
    container = _get_container()
    if container:
        try:
            container.upsert_item(document)
            return
        except Exception as exc:
            logger.warning("Échec écriture Cosmos (%s) → repli local.", exc)
    _FICHIER_LOCAL.parent.mkdir(exist_ok=True)
    with _FICHIER_LOCAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(document, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------
def log_tool_call(outil: str, entree: dict, sortie: str, duree_s: float, statut: str) -> None:
    """Journalise un appel d'outil (exigence F2 : input, output, durée, statut)."""
    _ecrire({
        "type": "tool_call",
        "session_id": "outillage",
        "outil": outil,
        "entree": entree,
        "sortie": sortie,
        "duree_s": duree_s,
        "statut": statut,
    })


def log_conversation(session_id: str, tache: str, messages: list[dict], reponse_finale: str) -> None:
    """Sauvegarde l'historique complet d'une conversation (US-04)."""
    _ecrire({
        "type": "conversation",
        "session_id": session_id,
        "tache": tache,
        "messages": messages,
        "reponse_finale": reponse_finale,
    })


def exporter_conversation(session_id: str) -> dict | None:
    """GET /conversations/{id}/export — retourne la conversation en JSON (US-04)."""
    container = _get_container()
    if container:
        requete = "SELECT * FROM c WHERE c.session_id = @sid AND c.type = 'conversation'"
        items = list(container.query_items(
            query=requete,
            parameters=[{"name": "@sid", "value": session_id}],
            enable_cross_partition_query=True,
        ))
        return items[0] if items else None
    # Repli local
    if _FICHIER_LOCAL.exists():
        for ligne in _FICHIER_LOCAL.read_text(encoding="utf-8").splitlines():
            doc = json.loads(ligne)
            if doc.get("session_id") == session_id and doc.get("type") == "conversation":
                return doc
    return None
