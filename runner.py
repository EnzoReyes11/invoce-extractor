import argparse
import base64
import json

from pdf_data_extraction_agent.pipeline.handler import handle_pubsub

parser = argparse.ArgumentParser()
parser.add_argument("file_name", help="Name of the PDF file in the bucket")
parser.add_argument("--bucket", default="expense-tracking-documents", help="GCS bucket name")
args = parser.parse_args()

payload = base64.b64encode(
    json.dumps(
        {
            "bucket": args.bucket,
            "name": args.file_name,
            "contentType": "application/pdf",
        }
    ).encode()
).decode()

body, status = handle_pubsub({"message": {"data": payload}})
print(status, body)
