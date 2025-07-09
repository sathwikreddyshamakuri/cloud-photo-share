import pytest, boto3
from moto import mock_dynamodb, mock_s3

# ⚠️ moto must be started BEFORE the app imports boto3 clients
@pytest.fixture(scope="session", autouse=True)
def _moto():
    with mock_dynamodb(), mock_s3():
        # pre-create the tables & bucket the app expects
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
                {"AttributeName": "photo_id", "AttributeType": "S"},
                {"AttributeName": "album_id", "AttributeType": "S"},
                {"AttributeName": "uploaded_at", "AttributeType": "N"},
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "album_id-index",
                "KeySchema": [
                    {"AttributeName": "album_id", "KeyType": "HASH"},
                    {"AttributeName": "uploaded_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
            }],
            BillingMode="PAY_PER_REQUEST",
        )

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="photo-share-test")

        # now yield control to the tests
        yield
