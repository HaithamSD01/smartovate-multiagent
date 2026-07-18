"""
Outils des agents spécialistes (CDC §2.2 - F2 Gestion des outils).

Règles imposées par le cahier des charges :
  - timeout de 30 s maximum par appel d'outil externe ;
  - retry exponentiel, 3 tentatives maximum (tenacity) ;
  - chaque appel est loggé (input, output, durée, statut) → Cosmos DB.

En AutoGen v0.4, un outil est simplement une fonction Python typée et
documentée que l'on passe à l'agent via `tools=[...]`.
"""
from __future__ import annotations

import concurrent.futures
import functools
import logging
import re
import time
from typing import Callable

from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from memory.cosmos_logger import log_tool_call

logger = logging.getLogger("smartovate.tools")


# ---------------------------------------------------------------------------
# Décorateur maison : timeout 30s + retry exponentiel + log Cosmos DB
# (correspond au diagramme d'activités n°7 de la présentation UML)
# ---------------------------------------------------------------------------
def outil_securise(func: Callable) -> Callable:
    @retry(
        stop=stop_after_attempt(settings.tool_max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        debut = time.time()
        statut = "OK"
        resultat = None
        try:
            # Exécution dans un thread pour pouvoir imposer le timeout de 30 s
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(func, *args, **kwargs)
                resultat = future.result(timeout=settings.tool_timeout_seconds)
            return resultat
        except concurrent.futures.TimeoutError:
            statut = "TIMEOUT"
            raise TimeoutError(
                f"L'outil '{func.__name__}' a dépassé {settings.tool_timeout_seconds}s."
            )
        except Exception:
            statut = "ERREUR"
            raise
        finally:
            duree = round(time.time() - debut, 3)
            # Auditabilité (MAS-TK-15) — ne bloque jamais si Cosmos indisponible
            log_tool_call(
                outil=func.__name__,
                entree={"args": str(args), "kwargs": str(kwargs)},
                sortie=str(resultat)[:500],
                duree_s=duree,
                statut=statut,
            )
    return wrapper


# ---------------------------------------------------------------------------
# Outils du domaine
# ---------------------------------------------------------------------------
@outil_securise
def calculer(expression: str) -> str:
    """Évalue une expression mathématique simple (ex: '2 + 3 * 4').

    Args:
        expression: expression arithmétique en Python (chiffres et opérateurs).

    Returns:
        Le résultat sous forme de chaîne, ou un message d'erreur.
    """
    # Liste blanche stricte : chiffres, opérateurs, parenthèses, point, espaces
    if not re.fullmatch(r"[0-9+\-*/().% ]+", expression):
        return "Expression refusée : seuls les caractères arithmétiques sont autorisés."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307 (whitelist ci-dessus)
    except Exception as exc:
        return f"Erreur de calcul : {exc}"


@outil_securise
def detect_pii(texte: str) -> str:
    """Détecte des données personnelles (PII) dans un texte : emails, téléphones, n° de carte.

    Args:
        texte: le texte à analyser.

    Returns:
        'AUCUN_PII' si rien n'est détecté, sinon la liste des types trouvés.
    """
    motifs = {
        "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "telephone": r"(\+?\d{1,3}[\s.-]?)?(\d{2,3}[\s.-]?){3,4}\d{2,3}",
        "carte_bancaire": r"\b(?:\d[ -]?){13,16}\b",
    }
    trouves = [nom for nom, motif in motifs.items() if re.search(motif, texte)]
    return "AUCUN_PII" if not trouves else f"PII détecté : {', '.join(trouves)}"


@outil_securise
def run_python_snippet(code: str) -> str:
    """Exécute un court script Python de démonstration et retourne sa sortie.

    ⚠️ DÉMO UNIQUEMENT (Bug 3 du CDC) : en production, remplacer par une
    exécution isolée dans Docker (use_docker=True).

    Args:
        code: le code Python à exécuter.

    Returns:
        La valeur de la variable 'resultat' définie par le script, ou un message.
    """
    interdits = ["import os", "import sys", "subprocess", "open(", "__import__", "eval(", "exec("]
    if any(mot in code for mot in interdits):
        return "Code refusé : instruction potentiellement dangereuse détectée."
    scope: dict = {}
    try:
        exec(code, {"__builtins__": {"range": range, "len": len, "print": print}}, scope)  # noqa: S102
        return str(scope.get("resultat", "Exécuté (définissez une variable 'resultat' pour récupérer une valeur)."))
    except Exception as exc:
        return f"Erreur d'exécution : {exc}"
