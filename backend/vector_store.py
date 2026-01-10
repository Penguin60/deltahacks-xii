import os
import time
import json
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pinecone import Pinecone
from typing import TypedDict, Literal

load_dotenv()

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
    Add an incident directly to Pinecone index from JSON string.
    
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
        
        # Upsert directly to Pinecone
        dense_index.upsert_records("incidents", [validated])
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

def load_and_add_incidents(json_file: str):
    """Load incidents from JSON file and add them to the database"""
    try:
        with open(json_file, 'r') as f:
            incidents = json.load(f)
        
        if not incidents:
            print(f"No incidents found in {json_file}")
            return
        
        print(f"\nLoading {len(incidents)} incidents from {json_file}...")
        
        # Validate all records first
        validated_records = []
        for incident in incidents:
            try:
                validated = validate_record(incident)
                validated_records.append(validated)
            except ValueError as e:
                print(f"Validation error: {e}")
        
        # Only upsert if we have valid records
        if validated_records:
            dense_index.upsert_records("incidents", validated_records)
            print(f"Successfully loaded {len(validated_records)} incidents to Pinecone\n")
        else:
            print("No valid records to load")
            
    except FileNotFoundError:
        print(f"Error: File {json_file} not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file}: {e}")
    except Exception as e:
        print(f"Error loading incidents: {e}")

def _norm_text(s: str) -> str:
    return " ".join(s.lower().split()) if isinstance(s, str) else ""

def _time_within_window(time1: str, time2: str, window_minutes: int) -> bool:
    """Check if two times are within a window of each other (same day assumed)."""
    try:
        t1 = datetime.strptime(time1, "%H:%M")
        t2 = datetime.strptime(time2, "%H:%M")
        diff = abs((t1 - t2).total_seconds() / 60)
        return diff <= window_minutes
    except (ValueError, TypeError):
        return False

def find_similar_incidents(json_data: str, similarity_threshold: float = 0.85, top_k: int = 10, 
                           match_incident_type: bool = True, match_postal_code: bool = True, 
                           match_date: bool = True, match_time: bool = True, 
                           time_window_minutes: int = 30) -> list:
    """
    Find similar or duplicate incidents in the database, filtered by metadata.

    Args:
        json_data: JSON string containing incident data
        similarity_threshold: Score threshold (0-1) for semantic similarity
        top_k: Number of results to fetch from search
        match_incident_type: Only return incidents with same incidentType
        match_postal_code: Only return incidents with same postal_code
        match_date: Only return incidents on the same date
        match_time: Only return incidents within time_window_minutes of each other
        time_window_minutes: Time window in minutes for matching (default: 30)

    Returns:
        list: Similar incidents with flags for exact duplicates
    """
    try:
        incident = json.loads(json_data)
        query_text = incident.get("chunk_text", "")
        if not query_text:
            return []

        # Get metadata from input incident
        input_type = incident.get("incidentType", "")
        input_postal = incident.get("postal_code", "")
        input_date = incident.get("date", "")
        input_time = incident.get("time", "")

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
            hit_type = hit['fields'].get('incidentType', '')
            hit_postal = hit['fields'].get('postal_code', '')
            hit_date = hit['fields'].get('date', '')
            hit_time = hit['fields'].get('time', '')
            
            # Apply metadata filters
            if match_incident_type and hit_type != input_type:
                continue
            if match_postal_code and hit_postal != input_postal:
                continue
            if match_date and hit_date != input_date:
                continue
            if match_time and not _time_within_window(input_time, hit_time, time_window_minutes):
                continue
            
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
                    "incidentType": hit_type,
                    "postal_code": hit_postal,
                    "date": hit_date,
                    "time": hit_time,
                    "metadata_match": {
                        "incidentType": hit_type == input_type,
                        "postal_code": hit_postal == input_postal,
                        "date": hit_date == input_date,
                        "time_within_window": _time_within_window(input_time, hit_time, time_window_minutes)
                    }
                })

        return similar_incidents

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return []
    except Exception as e:
        print(f"Error finding similar incidents: {e}")
        return []


# Only run this code when executing the file directly
if __name__ == "__main__":
    # Load sample incidents
    load_and_add_incidents("sample_incidents.json")

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
        "chunk_text": "Fire in warehouse",
        "incidentType": "Fire",
        "postal_code": "10004",
        "severity_level": "3",
        "date": "2026-01-10",
        "time": "20:15"
    }

    similar = find_similar_incidents(json.dumps(test_incident), similarity_threshold=0.8, top_k=5)
    print("\nSimilar incidents found:")
    for incident in similar:
        print(incident)
