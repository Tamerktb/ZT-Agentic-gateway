import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    identity_provider_url: str = os.environ.get(
        "IDENTITY_PROVIDER_URL", "http://identity-provider:8001")
    credential_vault_url: str = os.environ.get(
        "CREDENTIAL_VAULT_URL", "http://credential-vault:8002")
    policy_engine_url: str = os.environ.get(
        "POLICY_ENGINE_URL", "http://policy-engine:8003")
    audit_service_url: str = os.environ.get(
        "AUDIT_SERVICE_URL", "http://audit-service:8004")
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")

    class Config:
        env_prefix = ""


settings = Settings()
