"""
setup_opensearch.py
--------------------
One-time setup script that creates an AWS OpenSearch Serverless
Vector Search collection fully via boto3 — no AWS Console clicking needed.

Follows these steps:
  1. Create encryption policy
  2. Create network policy
  3. Create the collection (type=VECTORSEARCH) and wait for ACTIVE
  4. Create data access policy
  5. Fetch the collection endpoint
  6. Save endpoint to .env automatically
  7. Create the k-NN index (384 dimensions, matches all-MiniLM-L6-v2)

Run once:
    python setup_opensearch.py

Safe to re-run — it detects existing policies/collections and skips them.
"""

import sys
import time
import json
import boto3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config.settings import settings

COLLECTION_NAME = "mediashippers-vectors"
INDEX_NAME      = "mediashippers-docs"
VECTOR_DIM      = 384   # all-MiniLM-L6-v2 output size
ENV_FILE        = Path(__file__).parent / ".env"

if not settings.AWS_ACCESS_KEY_ID or "your-aws" in settings.AWS_ACCESS_KEY_ID:
    print("\n❌  AWS credentials not set in .env — fill AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY first.\n")
    sys.exit(1)

aoss = boto3.client(
    "opensearchserverless",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)

sts = boto3.client(
    "sts",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def get_caller_identity():
    try:
        identity = sts.get_caller_identity()
        return identity["Arn"]
    except Exception as e:
        print(f"❌  Could not verify AWS identity: {e}")
        sys.exit(1)


def step1_encryption_policy():
    print("\n── Step 1: Encryption policy ──────────────────────")
    name = f"{COLLECTION_NAME}-enc"
    try:
        aoss.create_security_policy(
            name=name,
            type="encryption",
            policy=json.dumps({
                "Rules": [{
                    "ResourceType": "collection",
                    "Resource": [f"collection/{COLLECTION_NAME}"]
                }],
                "AWSOwnedKey": True
            }),
        )
        print(f"   ✅ Created encryption policy: {name}")
    except aoss.exceptions.ConflictException:
        print(f"   ✅ Encryption policy already exists: {name}")
    except Exception as e:
        print(f"   ❌ {e}")
        sys.exit(1)


def step2_network_policy():
    print("\n── Step 2: Network policy ─────────────────────────")
    name = f"{COLLECTION_NAME}-net"
    try:
        aoss.create_security_policy(
            name=name,
            type="network",
            policy=json.dumps([{
                "Rules": [
                    {"ResourceType": "collection", "Resource": [f"collection/{COLLECTION_NAME}"]},
                    {"ResourceType": "dashboard",  "Resource": [f"collection/{COLLECTION_NAME}"]},
                ],
                "AllowFromPublic": True
            }]),
        )
        print(f"   ✅ Created network policy: {name}")
    except aoss.exceptions.ConflictException:
        print(f"   ✅ Network policy already exists: {name}")
    except Exception as e:
        print(f"   ❌ {e}")
        sys.exit(1)


def step3_create_collection():
    print("\n── Step 3: Create Vector Search collection ────────")
    try:
        aoss.create_collection(
            name=COLLECTION_NAME,
            type="VECTORSEARCH",   # Critical: not TIMESERIES or SEARCH
            description="MediaShippers RAG vector store"
        )
        print(f"   ✅ Collection creation requested: {COLLECTION_NAME}")
    except aoss.exceptions.ConflictException:
        print(f"   ✅ Collection already exists: {COLLECTION_NAME}")
    except Exception as e:
        print(f"   ❌ {e}")
        sys.exit(1)

    print("   ⏳ Waiting for collection to become ACTIVE (this can take 2-5 minutes)...")
    while True:
        res    = aoss.batch_get_collection(names=[COLLECTION_NAME])
        items  = res.get("collectionDetails", [])
        if not items:
            time.sleep(10)
            continue
        status = items[0]["status"]
        print(f"      status = {status}")
        if status == "ACTIVE":
            print("   ✅ Collection is ACTIVE")
            return items[0]
        if status == "FAILED":
            print("   ❌ Collection creation FAILED")
            sys.exit(1)
        time.sleep(15)


def step4_data_access_policy(caller_arn):
    print("\n── Step 4: Data access policy ─────────────────────")
    name = f"{COLLECTION_NAME}-access"
    try:
        aoss.create_access_policy(
            name=name,
            type="data",
            policy=json.dumps([{
                "Rules": [
                    {
                        "ResourceType": "index",
                        "Resource": [f"index/{COLLECTION_NAME}/*"],
                        "Permission": [
                            "aoss:CreateIndex", "aoss:DeleteIndex", "aoss:UpdateIndex",
                            "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument"
                        ]
                    },
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{COLLECTION_NAME}"],
                        "Permission": [
                            "aoss:CreateCollectionItems", "aoss:DeleteCollectionItems",
                            "aoss:UpdateCollectionItems", "aoss:DescribeCollectionItems"
                        ]
                    }
                ],
                "Principal": [caller_arn]
            }]),
        )
        print(f"   ✅ Created data access policy: {name}")
    except aoss.exceptions.ConflictException:
        print(f"   ✅ Data access policy already exists: {name}")
    except Exception as e:
        print(f"   ❌ {e}")
        sys.exit(1)


def step5_get_endpoint(collection_info):
    print("\n── Step 5: Collection endpoint ────────────────────")
    endpoint = collection_info["collectionEndpoint"]
    # Strip https:// for storage in .env (we'll add scheme back when connecting)
    host = endpoint.replace("https://", "")
    print(f"   ✅ Endpoint: {host}")
    return host


def step6_save_to_env(host):
    print("\n── Step 6: Save endpoint to .env ──────────────────")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("OPENSEARCH_HOST="):
            new_lines.append(f"OPENSEARCH_HOST={host}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"OPENSEARCH_HOST={host}")
        new_lines.append(f"OPENSEARCH_INDEX={INDEX_NAME}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"   ✅ Saved OPENSEARCH_HOST to .env")


def step7_create_index(host):
    print("\n── Step 7: Create k-NN index ──────────────────────")
    from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

    credentials = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    ).get_credentials()

    auth = AWSV4SignerAuth(credentials, settings.AWS_REGION, "aoss")

    client = OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
    )

    if client.indices.exists(index=INDEX_NAME):
        print(f"   ✅ Index already exists: {INDEX_NAME}")
        return

    body = {
        "settings": {
            "index": {
                "knn": True,
            }
        },
        "mappings": {
            "properties": {
                "text":          {"type": "text"},
                "source_file":   {"type": "keyword"},
                "document_name": {"type": "keyword"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": VECTOR_DIM,
                    "method": {
                        "name": "hnsw",
                        "engine": "nmslib",
                        "space_type": "cosinesimil",
                    }
                }
            }
        }
    }

    # Retry a few times — fresh collections sometimes need a moment before indexing works
    for attempt in range(5):
        try:
            client.indices.create(index=INDEX_NAME, body=body)
            print(f"   ✅ Created index: {INDEX_NAME} (dimension={VECTOR_DIM})")
            return
        except Exception as e:
            print(f"   ⏳ Attempt {attempt+1}/5 failed ({e}); retrying in 15s...")
            time.sleep(15)

    print("   ❌ Could not create index after retries.")
    sys.exit(1)


def main():
    print("\n🚀  MediaShippers — AWS OpenSearch Serverless Setup")
    print("    Collection:", COLLECTION_NAME)
    print("    Region:    ", settings.AWS_REGION)

    caller_arn = get_caller_identity()
    print(f"    Identity:  {caller_arn}")

    step1_encryption_policy()
    step2_network_policy()
    collection_info = step3_create_collection()
    step4_data_access_policy(caller_arn)
    host = step5_get_endpoint(collection_info)
    step6_save_to_env(host)
    step7_create_index(host)

    print("\n✅  ALL DONE — OpenSearch Serverless is ready!")
    print(f"    Run next: python -m ingestion.index_document\n")


if __name__ == "__main__":
    main()
