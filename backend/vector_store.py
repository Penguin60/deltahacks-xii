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
    "Theft", "PickPocket", "Fire", "Mass Fire", "Crowd Stampede", "Terrorist Attack"
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
        "Theft", "PickPocket", "Fire", "Mass Fire", "Crowd Stampede", "Terrorist Attack"
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

query = "residential fire"
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