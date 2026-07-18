"""
Mémoire COURT-TERME partagée entre agents (CDC §2.4 - F4).

Rôle de Redis dans ce projet :
  → pendant UNE session (une tâche utilisateur), les agents ont besoin de
    partager un état global : la tâche initiale, le plan de l'orchestrateur,
    le nombre de tours consommés, les résultats intermédiaires.
  → Redis est un cache clé/valeur en RAM : lecture/écriture quasi instantanée.
  → Chaque clé expire automatiquement (TTL) : c'est bien une mémoire de SESSION,
    pas une archive. L'archive, c'est Cosmos DB (voir cosmos_logger.py).

Si Redis n'est pas installé/lancé, la classe bascule sur un simple
dictionnaire Python : le prototype reste utilisable en local.
"""
from __future__ import annotations

import json
import logging

from config.settings import settings

logger = logging.getLogger("smartovate.memory")


class SessionMemory:
    def __init__(self) -> None:
        self._fallback: dict[str, str] = {}
        self._redis = None
        try:
            import redis  # import local pour ne pas exiger Redis en dev

            self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            self._redis.ping()
            logger.info("Redis connecté : mémoire de session distribuée active.")
        except Exception as exc:  # Redis absent → mode dégradé local
            self._redis = None
            logger.warning("Redis indisponible (%s) → mémoire locale en RAM.", exc)

    # -- API simple : set / get / append d'un état de session -------------
    def set(self, session_id: str, cle: str, valeur) -> None:
        k = f"session:{session_id}:{cle}"
        v = json.dumps(valeur, ensure_ascii=False)
        if self._redis:
            self._redis.set(k, v, ex=settings.redis_ttl_seconds)
        else:
            self._fallback[k] = v

    def get(self, session_id: str, cle: str, defaut=None):
        k = f"session:{session_id}:{cle}"
        v = self._redis.get(k) if self._redis else self._fallback.get(k)
        return json.loads(v) if v is not None else defaut

    def incr_tours(self, session_id: str) -> int:
        """Compteur de tours de conversation (watchdog anti boucle infinie, Risque R1)."""
        k = f"session:{session_id}:tours"
        if self._redis:
            n = self._redis.incr(k)
            self._redis.expire(k, settings.redis_ttl_seconds)
            return int(n)
        n = int(self._fallback.get(k, "0")) + 1
        self._fallback[k] = str(n)
        return n


# Singleton utilisé partout dans l'application
session_memory = SessionMemory()
