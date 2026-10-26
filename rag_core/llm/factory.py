"""Factory du client LLM : choisit l'implémentation à partir des Settings."""

from rag_core.llm.base import LLMClient
from rag_core.llm.openai_compatible import OpenAICompatibleLLM
from rag_core.settings import Settings


class LLMFactory:
    """Crée le client LLM concret configuré par `Settings`.

    Toute la config (URL, clé, modèle, température) vient des Settings :
    aucune valeur en dur ici.
    """

    @staticmethod
    def create(settings: Settings) -> LLMClient:
        """Retourne un LLMClient prêt à l'emploi."""
        return OpenAICompatibleLLM(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )
