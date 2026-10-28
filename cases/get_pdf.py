
import boto3
from pathlib import Path

# Public S3 bucket: no AWS account or credentials required.
BUCKET = "indian-supreme-court-judgments"
PREFIX = "data/pdf/year=2025/english/"

OUTPUT_DIR = Path("supreme_court_2025")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Connect to public S3.
s3 = boto3.client(
    "s3",
    region_name="ap-south-1",
    config=__import__("botocore").config.Config(
        signature_version=__import__("botocore").UNSIGNED
    )
)

# List English judgment PDFs from 2025.
response = s3.list_objects_v2(
    Bucket=BUCKET,
    Prefix=PREFIX,
    MaxKeys=100
)

pdf_keys = [
    obj["Key"]
    for obj in response.get("Contents", [])
    if obj["Key"].lower().endswith(".pdf")
][:10]

if not pdf_keys:
    raise RuntimeError(
        "No PDFs found. Check the S3 prefix and bucket access."
    )

# Download the 10 PDFs.
for i, key in enumerate(pdf_keys, start=1):
    filename = f"case_{i:02d}.pdf"
    destination = OUTPUT_DIR / filename

    s3.download_file(BUCKET, key, str(destination))

    print(f"Downloaded {i}/10: {key} -> {destination}")

print(f"\nDownloaded {len(pdf_keys)} judgments to {OUTPUT_DIR}")
