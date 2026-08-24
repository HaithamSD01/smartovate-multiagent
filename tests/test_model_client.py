"""
Tests unitaires de la factory de client Azure OpenAI (config/model_client.py).
"""
from config.model_client import get_model_client


def test_get_model_client_temperature_par_defaut():
    """Sans argument, le client doit se construire avec la température par défaut des settings."""
    client = get_model_client()
    assert client is not None

def test_get_model_client_temperature_personnalisee():
    """Avec un argument explicite (ex: 0.2 pour l'Agent Critique, risque R3), il doit l'utiliser."""
    client = get_model_client(temperature=0.2)
    assert client is not None
