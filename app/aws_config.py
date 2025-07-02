# app/aws_config.py
import os
import boto3
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())  # load .env

REGION    = os.getenv("REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET")

s3   = boto3.client("s3",   region_name=REGION)
dyna = boto3.resource("dynamodb", region_name=REGION)
