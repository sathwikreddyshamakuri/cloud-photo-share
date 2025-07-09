# tests/conftest.py
import uuid, time, os
import boto3
import pytest
from moto import mock_s3, mock_dynamodb

@pytest.fixture(autouse=True, scope="session")
def moto_aws():
    """
    Start in-memory S3 & Dynamo mocks for every test session.
    Then create the buckets / tables our app boot code expects,
    so imports don’t crash.
    """
    with mock_s3(), mock_dynamodb():
        # ---------- minimal bootstrap ----------
        REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        s3   = boto3.client("s3", region_name=REGION)
        dyna = boto3.resource("dynamodb", region_name=REGION)

        # S3 bucket needed by generate_presigned_url
        bucket_name = os.getenv("S3_BUCKET", "photo-share-test")
        s3.create_bucket(Bucket=bucket_name)

        # Users table
        dyna.create_table(
            TableName="Users",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Albums table
        dyna.create_table(
            TableName="Albums",
            KeySchema=[{"AttributeName": "album_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "album_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # PhotoMeta table + GSI
        dyna.create_table(
            TableName="PhotoMeta",
            KeySchema=[{"AttributeName": "photo_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "photo_id",   "AttributeType": "S"},
                {"AttributeName": "album_id",   "AttributeType": "S"},
                {"AttributeName": "uploaded_at","AttributeType": "N"},
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "album_id-index",
                "KeySchema": [
                    {"AttributeName": "album_id",   "KeyType": "HASH"},
                    {"AttributeName": "uploaded_at","KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }],
            BillingMode="PAY_PER_REQUEST",
        )

        # run the tests
        yield
