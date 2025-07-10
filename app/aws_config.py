"""
Central AWS configuration & helpers
-----------------------------------
Exports:

    REGION, S3_BUCKET, JWT_SECRET
    s3  – shared boto3 S3 client
    dyna – shared boto3 DynamoDB resource
"""

from __future__ import annotations

import os
import boto3
from functools import lru_cache

# ── Pydantic imports ────────────────────────────────────────────────────
from pydantic import Field, ValidationError

try:                                # Pydantic ≥ v2 (preferred)
    from pydantic_settings import BaseSettings
except ModuleNotFoundError:         # Pydantic v1 fallback
    from pydantic import BaseSettings  # type: ignore


# ────────────────────────────────────────────────────────────────────────
class _Settings(BaseSettings):
    REGION: str = Field(..., env="REGION")
    S3_BUCKET: str = Field(..., env="S3_BUCKET")
    JWT_SECRET: str = Field(..., env="JWT_SECRET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def _load_settings() -> _Settings:
    """
    One-time settings load.  
    Tries env/.env first, then (optionally) pulls from AWS SecretsManager
    if `APP_SECRET_NAME` is defined.
    """
    try:
        return _Settings()                    # .env or plain env-vars
    except ValidationError as e:
        secret_name = os.getenv("APP_SECRET_NAME")
        if not secret_name:
            missing = [err["loc"][0] for err in e.errors()]
            raise RuntimeError(f"Missing config keys: {missing}") from None

        sm = boto3.client(
            "secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        secret_blob = sm.get_secret_value(SecretId=secret_name)["SecretString"]
        env_override = {**os.environ, **eval(secret_blob)}
        return _Settings(_env_file=None, **env_override)


_CFG = _load_settings()

REGION: str = _CFG.REGION
S3_BUCKET: str = _CFG.S3_BUCKET
JWT_SECRET: str = _CFG.JWT_SECRET

# ── Shared boto3 clients/resources ─────────────────────────────────────
_session = boto3.session.Session(region_name=REGION)

s3   = _session.client("s3")
dyna = _session.resource("dynamodb")

__all__ = ["REGION", "S3_BUCKET", "JWT_SECRET", "s3", "dyna"]
