# scripts/mark_all_verified.py
import os, boto3

REGION = os.getenv("REGION", "us-east-1")
table = boto3.resource("dynamodb", region_name=REGION).Table("Users")

scan = table.scan()
items = scan["Items"]

# keep scanning if >1MB
while "LastEvaluatedKey" in scan:
    scan = table.scan(ExclusiveStartKey=scan["LastEvaluatedKey"])
    items.extend(scan["Items"])

updated = 0
with table.batch_writer() as bw:
    for u in items:
        if not u.get("email_verified", False):
            u["email_verified"] = True
            bw.put_item(Item=u)
            updated += 1

print(f"Marked {updated} users as verified.")
