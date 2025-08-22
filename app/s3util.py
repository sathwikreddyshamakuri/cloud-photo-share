# app/s3util.py
import os
import boto3

S3_BUCKET = os.getenv("S3_BUCKET")
_s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))

def sign_key(key: str, expires: int = 3600) -> str:
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
