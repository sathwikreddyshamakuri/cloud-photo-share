"""
Central place for all runtime configuration
and shared AWS clients (boto3).

* Reads from real env-vars / .env in production
* Provides safe defaults when they are absent
  (e.g. during pytest or CI runs).
"""

from __future__ import annotations

import os
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Pydantic settings model ────────────────────────────────────────────
class _Settings(BaseSettings):
    # required in prod – but we supply fall-backs below
    JWT_SECRET: str | None = None
    S3_BUCKET: str | None = None
    REGION: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# ── helper to inject defaults when missing (for tests) ────────────────
def _hydrate() -> _Settings:
    s = _Settings()  # first parse whatever is available

    if s.JWT_SECRET and s.S3_BUCKET and s.REGION:
        return s  # all good

    # ↓ Still here ⇒ we’re probably inside pytest / CI.
    # Supply dummy-but-safe defaults *only* for empty fields.
    return _Settings(
        JWT_SECRET=s.JWT_SECRET or "unit-test-secret",
        S3_BUCKET=s.S3_BUCKET or "test-bucket",
        REGION=s.REGION or os.getenv("AWS_REGION", "us-east-1"),
    )


@lru_cache          # parse exactly once
def _cfg() -> _Settings:
    return _hydrate()


# ── public “constants” other modules import ───────────────────────────
CFG = _cfg()            # export whole settings object if someone wants it

JWT_SECRET: str = CFG.JWT_SECRET  # type: ignore  # guaranteed not None now
S3_BUCKET:  str = CFG.S3_BUCKET   # type: ignore
REGION:     str = CFG.REGION      # type: ignore

# ── shared AWS clients/resources (all modules reuse these) ────────────
session = boto3.Session(region_name=REGION)

s3   = session.client("s3")
dyna = session.resource("dynamodb")
