"""
Configuration centralisée du projet (Cahier des Charges §2.3 - Sécurité).
Toutes les clés sont lues depuis le fichier .env — JAMAIS en dur dans le code.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Azure OpenAI (MAS-TK-01) ---
    azure_openai_endpoint: str = "https://VOTRE-RESSOURCE.openai.azure.com/"
    azure_openai_api_key: str = "CHANGE_ME"
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-06-01"

    # --- Comportement des agents (CDC §2.3 - F3 Terminaison) ---
    max_turns: int = 15          # défaut 15, max 30 selon le CDC
    temperature: float = 0.2     # basse pour limiter les hallucinations (Risque R3)
    tool_timeout_seconds: int = 30   # CDC §2.2 - F2
    tool_max_retries: int = 3        # retry exponentiel (max 3 tentatives)

    # --- Redis : mémoire de session partagée (MAS-TK-05 / MAS-TK-14) ---
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 3600    # la session expire après 1h

    # --- Azure Cosmos DB : persistance long-terme (MAS-TK-04 / MAS-TK-15) ---
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "smartovate_mas"
    cosmos_container: str = "conversations"

    # --- API ---
    api_key_header: str = "X-API-Key"
    api_key_value: str = "dev-local-key"   # à remplacer en production (Azure AD)


settings = Settings()
