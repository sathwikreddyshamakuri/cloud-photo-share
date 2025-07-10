"""
PyTest session-wide fixtures & global config
-------------------------------------------

* aws_stubs – spins up Moto’s in-memory DynamoDB & S3
* warning filter – hides botocore’s utcnow deprecation spam
"""

from pathlib import Path
import os
import warnings

import boto3
import pytest
from moto import mock_aws  # moto ≥5.x unified entry-point

# ─── Hard-coded env defaults so the app imports without real AWS creds ─────────
os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("REGION", "us-east-1")
os.environ.setdefault("JWT_SECRET", "unit-test-secret")   # NEW ⬅⬅⬅

# ─── Silence botocore deprecation warnings ────────────────────────────────────
def pytest_configure():
    warnings.filterwarnings(
        "ignore",
        message="datetime\\.datetime\\.utcnow\\(\\) is deprecated",
        module="botocore",
    )

# ─── Moto sandbox for the whole test session ──────────────────────────────────
@pytest.fixture(autouse=True, scope="session")
def aws_stubs():
    """Spin up in-memory DynamoDB & S3 once per test session."""
    with mock_aws():
        # DynamoDB tables
        dyna = boto3.resource("dynamodb", region_name="us-east-1")

        dyna.create_table(
            TableName="Users",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        dyna.create_table(
            TableName="Albums",
            KeySchema=[{"AttributeName": "album_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "album_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        dyna.create_table(
            TableName="PhotoMeta",
            KeySchema=[{"AttributeName": "photo_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "photo_id",   "AttributeType": "S"},
                {"AttributeName": "album_id",   "AttributeType": "S"},
                {"AttributeName": "uploaded_at","AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "album_id-index",
                    "KeySchema": [
                        {"AttributeName": "album_id",    "KeyType": "HASH"},
                        {"AttributeName": "uploaded_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )

        # S3 bucket
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=os.environ["S3_BUCKET"])

        yield
