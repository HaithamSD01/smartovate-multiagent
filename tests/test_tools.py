"""
Tests unitaires des outils (CDC §2.2 : "les outils doivent être testés
unitairement"). Lancer :  pytest tests/ -v
"""
import time

import pytest

from config.settings import settings
from tools.base_tools import calculer, detect_pii, outil_securise, run_python_snippet


# --- calculer ---------------------------------------------------------------
def test_calculer_simple():
    assert calculer("2 + 3 * 4") == "14"

def test_calculer_refuse_caracteres_interdits():
    assert "refusée" in calculer("__import__('os')")

def test_calculer_erreur_division_par_zero():
    assert calculer("5/0").startswith("Erreur de calcul :")


# --- detect_pii -------------------------------------------------------------
def test_pii_email_detecte():
    assert "email" in detect_pii("Contactez haitham@smartovate.com svp")

def test_pii_texte_propre():
    assert detect_pii("Bonjour, voici le rapport final.") == "AUCUN_PII"


# --- run_python_snippet -----------------------------------------------------
def test_snippet_fibonacci():
    code = (
        "a, b = 0, 1\n"
        "for _ in range(9):\n"
        "    a, b = b, a + b\n"
        "resultat = a\n"
    )
    assert run_python_snippet(code) == "34"

def test_snippet_refuse_code_dangereux():
    assert "refusé" in run_python_snippet("import os\nresultat = os.listdir('.')")

def test_snippet_erreur_execution():
    assert run_python_snippet("resultat = 1/0").startswith("Erreur d'exécution :")


# --- outil_securise (décorateur : timeout + retry + log) --------------------
def test_outil_securise_timeout(monkeypatch):
    monkeypatch.setattr(settings, "tool_timeout_seconds", 0.05)
    monkeypatch.setattr(settings, "tool_max_retries", 1)

    @outil_securise
    def outil_lent():
        time.sleep(1)
        return "trop tard"

    with pytest.raises(TimeoutError):
        outil_lent()

def test_outil_securise_propage_exception(monkeypatch):
    monkeypatch.setattr(settings, "tool_max_retries", 1)

    @outil_securise
    def outil_qui_echoue():
        raise ValueError("erreur volontaire")

    with pytest.raises(ValueError):
        outil_qui_echoue()
