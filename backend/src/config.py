from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # --- Standard OpenAI (set this OR the Azure block below) ---
    openai_api_key: Optional[str] = None

    # --- Azure OpenAI (takes priority over openai_api_key when set) ---
    # Required for Azure:
    azure_openai_endpoint: Optional[str] = None      # e.g. https://<resource>.openai.azure.com/
    azure_openai_api_key: Optional[str] = None       # Azure resource key
    azure_openai_api_version: str = "2024-08-01-preview"
    # The deployment name you created in Azure OpenAI Studio (e.g. "my-gpt4o")
    azure_openai_deployment: Optional[str] = None

    # Database
    db_path: str = "./nova_trade.db"

    # File storage
    upload_dir: str = "./uploads"

    # Security
    api_secret_key: str = "dev-secret-key"

    # Business config
    rules_dir: str = "./configs/rules"

    # Model selection
    # For Azure OpenAI the model values are ignored — deployment name is used instead.
    extractor_model: str = "gpt-4o-2024-08-06"
    validator_model: str = "gpt-4o"
    router_model: str = "gpt-4o"

    @property
    def use_azure_openai(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    # Pipeline controls
    max_retries_per_agent: int = 2
    max_tokens_per_job: int = 20000
    langgraph_recursion_limit: int = 15

    # Confidence thresholds
    confidence_escalate_threshold: float = 0.60
    confidence_low_threshold: float = 0.85

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
