import os
import time
import json
import uuid
from dotenv import load_dotenv
from pinecone import Pinecone
from typing import TypedDict, Literal

load_dotenv()
records = []

pinecone_key = os.getenv("PINECONE_API_KEY")

pc = Pinecone(pinecone_key)

index_name = "dispatch"
if not pc.has_index(index_name):
    pc.create_index_for_model(
        name=index_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model": "llama-text-embed-v2",
            "field_map": {"text": "chunk_text"}
        }
    )

dense_index = pc.Index(index_name)

# Define the schema
IncidentType = Literal[
    "Public Nuisance", "Break In", "Armed Robbery", "Car Theft", 
    "Theft", "Pick Pocket", "Fire", "Mass Fire", "Crowd Stampede", "Terrorist Attack"
]

SeverityLevel = Literal["1", "2", "3"]

class DispatchRecord(TypedDict):
    _id: str
    chunk_text: str
    incidentType: IncidentType
    postal_code: str
    severity_level: SeverityLevel
    date: str
    time: str

def validate_record(record: dict) -> DispatchRecord:
    """Validate record matches the schema"""
    required_fields = ["chunk_text", "incidentType", "postal_code", "severity_level", "date", "time"]
    
    # Check all required fields exist
    for field in required_fields:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate incidentType
    valid_types = {
        "Public Nuisance", "Break In", "Armed Robbery", "Car Theft", 
        "Theft", "Pick Pocket", "Fire", "Mass Fire", "Crowd Stampede", "Terrorist Attack"
    }
    if record["incidentType"] not in valid_types:
        raise ValueError(f"Invalid incidentType. Must be one of: {valid_types}")
    
    # Validate severity_level
    if record["severity_level"] not in ["1", "2", "3"]:
        raise ValueError(f"Invalid severity_level. Must be '1', '2', or '3'")
    
    # Auto-generate _id if not provided
    if "_id" not in record:
        record["_id"] = str(uuid.uuid4())
    
    return record

def add_incident(json_data: str) -> bool:
    """
    Add an incident to the index from JSON string.
    
    Args:
        json_data: JSON string containing incident data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Parse JSON string
        incident = json.loads(json_data)
        
        # Validate the record (this will auto-generate _id if missing)
        validated = validate_record(incident)
        
        # Add to records list
        records.append(validated)
        print(f"Successfully added incident {validated['_id']}")
        return True
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return False
    except ValueError as e:
        print(f"Validation error: {e}")
        return False
    except Exception as e:
        print(f"Error adding incident: {e}")
        return False

# Load and add sample incidents from JSON file
def load_and_add_incidents(json_file: str):
    """Load incidents from JSON file and add them to the database"""
    try:
        with open(json_file, 'r') as f:
            incidents = json.load(f)
        
        print(f"\nLoading {len(incidents)} incidents from {json_file}...")
        
        for incident in incidents:
            # Convert dict to JSON string and add via add_incident
            incident_json = json.dumps(incident)
            add_incident(incident_json)
        
        print(f"Successfully loaded all incidents from {json_file}\n")
    except FileNotFoundError:
        print(f"Error: File {json_file} not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file}: {e}")
    except Exception as e:
        print(f"Error loading incidents: {e}")

def _norm_text(s: str) -> str:
    return " ".join(s.lower().split()) if isinstance(s, str) else ""

def find_similar_incidents(json_data: str, similarity_threshold: float = 0.85, top_k: int = 5) -> list:
    """
    Find similar or duplicate incidents in the database.

    Flags:
    - is_exact_duplicate: normalized `chunk_text` matches an existing record exactly
    - score: semantic similarity score from Pinecone search
    """
    try:
        incident = json.loads(json_data)
        query_text = incident.get("chunk_text", "")
        if not query_text:
            return []

        results = dense_index.search(
            namespace="incidents",
            query={
                "top_k": top_k,
                "inputs": {'text': query_text}
            },
            rerank={
                "model": "bge-reranker-v2-m3",
                "top_n": top_k,
                "rank_fields": ["chunk_text"]
            }
        )

        q_norm = _norm_text(query_text)
        similar_incidents = []
        for hit in results.get('result', {}).get('hits', []):
            hit_text = hit['fields'].get('chunk_text', '')
            h_norm = _norm_text(hit_text)
            score = float(hit.get('_score', 0.0))

            is_exact = (q_norm == h_norm)
            # Include exact matches OR anything above the threshold
            if is_exact or score >= similarity_threshold:
                similar_incidents.append({
                    "_id": hit['_id'],
                    "score": round(score, 4),
                    "is_exact_duplicate": is_exact,
                    "chunk_text": hit_text,
                    "incidentType": hit['fields'].get('incidentType', ''),
                    "postal_code": hit['fields'].get('postal_code', ''),
                    "date": hit['fields'].get('date', ''),
                    "time": hit['fields'].get('time', '')
                })

        return similar_incidents

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return []
    except Exception as e:
        print(f"Error finding similar incidents: {e}")
        return []

# Load sample incidents
load_and_add_incidents("sample_incidents.json")

print(len(records))

validated_records = []
for record in records:
    try:
        validated_records.append(validate_record(record))
    except ValueError as e:
        print(f"Validation error for record {record.get('_id')}: {e}")

dense_index.upsert_records("incidents", validated_records)

time.sleep(10)

stats = dense_index.describe_index_stats()
print(stats)

query = "pickpocketing in transit"
results = dense_index.search(
    namespace="incidents",
    query={
        "top_k": 10,
        "inputs": {
            'text': query
        }
    },
    rerank={
        "model": "bge-reranker-v2-m3",
        "top_n": 10,
        "rank_fields": ["chunk_text"]
    } 
)

# Print the results
for hit in results['result']['hits']:
    print(f"id: {hit['_id']:<5} | score: {round(hit['_score'], 2):<5} | incidentType: {hit['fields']['incidentType']:<15} | text: {hit['fields']['chunk_text']:<50}")

print("search complete.")

# test find_similar_incidents
test_incident = {
    "chunk_text": "Crowd stampede",
    "incidentType": "Crowd Stampede",
    "postal_code": "10008",
    "severity_level": "3",
    "date": "2026-01-10",
    "time": "20:15"
}

similar = find_similar_incidents(json.dumps(test_incident), similarity_threshold=0.8, top_k=5)
print("\nSimilar incidents found:")
for incident in similar:
    print(incident)
