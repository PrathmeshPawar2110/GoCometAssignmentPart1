"""
Shared LLM client for Validator, Router, and Query.

Builds an AsyncAzureOpenAI or AsyncOpenAI instance at import time using the
same settings that drive the Extractor, so one .env controls everything.
"""

from openai import AsyncAzureOpenAI, AsyncOpenAI

from src.config import settings

if settings.use_azure_openai:
    llm_client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

    def get_model(_setting_val: str) -> str:
        """Return the Azure deployment name regardless of the setting value."""
        return settings.azure_openai_deployment or _setting_val

else:
    if not settings.openai_api_key:
        raise ValueError(
            "Set OPENAI_API_KEY for standard OpenAI, "
            "or AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY for Azure OpenAI."
        )
    llm_client = AsyncOpenAI(api_key=settings.openai_api_key)

    def get_model(setting_val: str) -> str:
        return setting_val
