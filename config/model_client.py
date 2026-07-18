"""
Factory du client de modèle Azure OpenAI (AutoGen v0.4+).
Tous les agents partagent la même façon de construire leur client.
"""
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

from config.settings import settings


def get_model_client(temperature: float | None = None) -> AzureOpenAIChatCompletionClient:
    """Retourne un client GPT-4o hébergé sur Azure OpenAI.

    Args:
        temperature: permet de surcharger la température par agent
                     (ex: 0.2 pour le Critique — Risque R3 du CDC).
    """
    return AzureOpenAIChatCompletionClient(
        azure_deployment=settings.azure_openai_deployment,
        model="gpt-4o-2024-11-20",
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        temperature=temperature if temperature is not None else settings.temperature,
    )
