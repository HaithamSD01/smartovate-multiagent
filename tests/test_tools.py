"""
Tests unitaires des outils (CDC §2.2 : "les outils doivent être testés
unitairement"). Lancer :  pytest tests/ -v
"""
from tools.base_tools import calculer, detect_pii, run_python_snippet


# --- calculer ---------------------------------------------------------------
def test_calculer_simple():
    assert calculer("2 + 3 * 4") == "14"

def test_calculer_refuse_caracteres_interdits():
    assert "refusée" in calculer("__import__('os')")


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
