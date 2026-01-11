#!/usr/bin/env python3
"""Diagnostic script to test Pinecone fetch and see response structure."""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone

# Load environment
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

pc = Pinecone(os.getenv("PINECONE_API_KEY"))
index_name = "dispatch-triage"
test_id = "01H8XJWBWMD4E5F6G7H8J9K0L1"

print(f"Testing Pinecone fetch for ID: {test_id}")
print("=" * 80)

# Get index host
host = pc.describe_index(index_name).host
print(f"Index host: {host}")

# Test 1: Fetch with include fields
print("\n[TEST 1] Fetching with include=['fields']...")
url = f"https://{host}/records/fetch"
headers = {
    "Api-Key": os.getenv("PINECONE_API_KEY"),
    "Content-Type": "application/json",
    "X-Pinecone-Api-Version": "2025-10",
}
payload = {
    "ids": [test_id],
    "namespace": "incidents",
    "include": ["fields"]
}

response = requests.post(url, json=payload, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response body:\n{json.dumps(response.json(), indent=2)}")

# Test 2: List some records to see what IDs exist
print("\n[TEST 2] Listing records via query to see what exists...")
index = pc.Index(name=index_name, host=host)

try:
    # Try to query with a simple search to see what records exist
    results = index.search(
        namespace="incidents",
        query={
            "top_k": 5,
            "inputs": {'text': 'fire'}
        }
    )
    print(f"Sample records in index:")
    print(json.dumps(results, indent=2))
except Exception as e:
    print(f"Error querying: {e}")

print("\n" + "=" * 80)
print("Diagnostic complete")
