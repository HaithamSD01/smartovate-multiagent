"""
US 1.1 — Valider la connexion à Azure OpenAI.
Lancer :  python -m tests.test_connection
"""
import asyncio

from autogen_core.models import UserMessage

from config.model_client import get_model_client


async def main() -> None:
    client = get_model_client()
    reponse = await client.create(
        [UserMessage(content="Réponds uniquement : CONNEXION_OK", source="user")]
    )
    print("Réponse du modèle :", reponse.content)
    assert "CONNEXION_OK" in str(reponse.content)
    print("✅ Connexion Azure OpenAI validée.")


if __name__ == "__main__":
    asyncio.run(main())
