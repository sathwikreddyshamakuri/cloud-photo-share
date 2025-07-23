"""
PyTest session-wide fixtures & global config
-------------------------------------------

* aws_stubs – spins up Moto’s in-memory DynamoDB & S3 (and now Tokens)
* warning filter – hides botocore’s utcnow deprecation spam
"""

import os
import warnings

import boto3
import pytest
from moto import mock_aws  # moto ≥5.x unified entry-point


#Hard-coded env so app imports cleanly in tests 
os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("REGION", "us-east-1")
os.environ.setdefault("JWT_SECRET", "unit-test-secret")
os.environ.setdefault("EMAIL_SENDER", "no-reply@test.local")
os.environ.setdefault("PUBLIC_UI_URL", "http://localhost:5173")
os.environ.setdefault("AUTO_VERIFY_USERS", "1")


def pytest_configure():
    warnings.filterwarnings(
        "ignore",
        message=r"datetime\.datetime\.utcnow\(\) is deprecated",
        module="botocore",
    )

#  Moto sandbox for the whole test session 
@pytest.fixture(autouse=True, scope="session")
def aws_stubs():
    """Spin up in-memory DynamoDB, S3 (and SES via moto) once per test session."""
    with mock_aws():
        dyna = boto3.resource("dynamodb", region_name="us-east-1")

        # Users
        dyna.create_table(
            TableName="Users",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Albums
        dyna.create_table(
            TableName="Albums",
            KeySchema=[{"AttributeName": "album_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "album_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Photos
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

        # NEW: Tokens table used for forgot-password / verify-email one-time tokens
        dyna.create_table(
            TableName="Tokens",
            KeySchema=[{"AttributeName": "token", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "token", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # S3 bucket
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=os.environ["S3_BUCKET"])

        yield
