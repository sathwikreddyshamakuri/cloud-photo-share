import os
import boto3
import pytest
from moto import mock_aws   # ← new unified mock

# dummy env-vars for the app
os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("REGION", "us-east-1")

@pytest.fixture(autouse=True, scope="session")
def aws_stubs():
    """
    Spin up in-memory DynamoDB + S3 for the entire test session.
    """
    with mock_aws():                # ← this mocks *all* AWS services
        # create fake resources before tests run
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
            AttributeDefinitions=[{"AttributeName": "photo_id", "AttributeType": "S"},
                                  {"AttributeName": "album_id",  "AttributeType": "S"},
                                  {"AttributeName": "uploaded_at","AttributeType": "N"}],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[{
                "IndexName": "album_id-index",
                "KeySchema": [
                    {"AttributeName": "album_id", "KeyType": "HASH"},
                    {"AttributeName": "uploaded_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }],
        )
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=os.environ["S3_BUCKET"])
        yield
