"""
Tests unitaires de la mémoire de session Redis (memory/redis_memory.py).
"""
import sys
import types
from unittest.mock import MagicMock

# Le module construit un singleton dès son import (session_memory = SessionMemory()
# en bas du fichier). Sans ce stub, ce premier import ferait un vrai appel réseau
# vers l'instance Azure Redis Enterprise configurée dans .env.
_fake_redis_module = types.ModuleType("redis")
_fake_redis_module.Redis = MagicMock()
sys.modules.setdefault("redis", _fake_redis_module)

from config.settings import settings
from memory.redis_memory import SessionMemory  # noqa: E402 (import après le stub volontaire)


def _redis_connecte():
    """Fabrique un faux module redis dont la connexion réussit (mode distribué)."""
    module = types.ModuleType("redis")
    mock_client = MagicMock()
    module.Redis = MagicMock()
    module.Redis.from_url = MagicMock(return_value=mock_client)
    return module, mock_client

def _redis_indisponible():
    """Fabrique un faux module redis dont ping() échoue (mode dégradé local)."""
    module = types.ModuleType("redis")
    mock_client = MagicMock()
    mock_client.ping.side_effect = ConnectionError("Redis injoignable")
    module.Redis = MagicMock()
    module.Redis.from_url = MagicMock(return_value=mock_client)
    return module


# --- __init__ : mode distribué vs mode dégradé -------------------------------
def test_init_bascule_en_mode_local_si_redis_indisponible(monkeypatch):
    """Si ping() échoue, la classe doit basculer sur le dictionnaire local
    sans lever d'exception (le prototype doit rester utilisable, cf. docstring)."""
    monkeypatch.setitem(sys.modules, "redis", _redis_indisponible())

    memoire = SessionMemory()

    assert memoire._redis is None

def test_init_utilise_redis_si_connexion_reussie(monkeypatch):
    """Si ping() réussit, la classe doit garder le client Redis connecté."""
    module, mock_client = _redis_connecte()
    monkeypatch.setitem(sys.modules, "redis", module)

    memoire = SessionMemory()

    assert memoire._redis is mock_client
    mock_client.ping.assert_called_once()


# --- set/get : mode dégradé (dictionnaire local) -----------------------------
def test_set_get_mode_local():
    """En mode dégradé, set() puis get() doivent fonctionner via le dict interne."""
    memoire = SessionMemory.__new__(SessionMemory)  # contourne __init__, déjà testé ci-dessus
    memoire._fallback = {}
    memoire._redis = None

    memoire.set("session-1", "plan", {"etapes": [1, 2, 3]})

    assert memoire.get("session-1", "plan") == {"etapes": [1, 2, 3]}

def test_get_mode_local_retourne_le_defaut_si_absent():
    memoire = SessionMemory.__new__(SessionMemory)
    memoire._fallback = {}
    memoire._redis = None

    assert memoire.get("session-1", "inexistant", defaut="valeur_par_defaut") == "valeur_par_defaut"


# --- set/get : mode distribué (Redis mocké) ----------------------------------
def test_set_mode_redis_appelle_set_avec_ttl():
    """set() doit appeler redis.set() avec le TTL configuré (mémoire de SESSION,
    pas une archive — cf. docstring du module)."""
    mock_client = MagicMock()
    memoire = SessionMemory.__new__(SessionMemory)
    memoire._fallback = {}
    memoire._redis = mock_client

    memoire.set("session-1", "plan", {"etapes": [1]})

    mock_client.set.assert_called_once()
    args, kwargs = mock_client.set.call_args
    assert args[0] == "session:session-1:plan"
    assert kwargs["ex"] == settings.redis_ttl_seconds

def test_get_mode_redis_lit_depuis_le_client():
    mock_client = MagicMock()
    mock_client.get.return_value = '{"etapes": [1, 2]}'
    memoire = SessionMemory.__new__(SessionMemory)
    memoire._fallback = {}
    memoire._redis = mock_client

    resultat = memoire.get("session-1", "plan")

    mock_client.get.assert_called_once_with("session:session-1:plan")
    assert resultat == {"etapes": [1, 2]}


# --- incr_tours : watchdog anti boucle infinie (risque R1) -------------------
def test_incr_tours_mode_local_incremente_depuis_zero():
    memoire = SessionMemory.__new__(SessionMemory)
    memoire._fallback = {}
    memoire._redis = None

    assert memoire.incr_tours("session-1") == 1
    assert memoire.incr_tours("session-1") == 2

def test_incr_tours_mode_redis_utilise_incr_et_pose_un_ttl():
    mock_client = MagicMock()
    mock_client.incr.return_value = 5
    memoire = SessionMemory.__new__(SessionMemory)
    memoire._fallback = {}
    memoire._redis = mock_client

    resultat = memoire.incr_tours("session-1")

    mock_client.incr.assert_called_once_with("session:session-1:tours")
    mock_client.expire.assert_called_once_with("session:session-1:tours", settings.redis_ttl_seconds)
    assert resultat == 5
