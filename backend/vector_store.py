import os
import time
import json
import uuid
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pinecone import Pinecone
from typing import TypedDict, Literal

load_dotenv()

pinecone_key = os.getenv("PINECONE_API_KEY")

pc = Pinecone(pinecone_key)

index_name = "dispatch"
if not pc.has_index(index_name):
    print(f"Creating new Pinecone index '{index_name}'...")
    pc.create_index_for_model(
        name=index_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model": "llama-text-embed-v2",
            # Updated to use the 'desc' field from the new schema for embeddings
            "field_map": {"text": "desc"}
        }
    )
    print("Index created.")

dense_index = pc.Index(index_name)

# --- New Schema Definitions (Triage Agent Spec) ---
IncidentType = Literal[
    "Public Nuisance", "Break In", "Armed Robbery", "Car Theft", 
    "Theft", "PickPocket", "Fire", "Mass Fire", "Crowd Stampede", "Terrorist Attack"
]

SuggestedActions = Literal[
    "console", "ask for more details", "dispatch officer", 
    "dispatch first-aiders", "dispatch firefighters"
]

Status = Literal["in progress", "completed"]

SeverityLevel = Literal["1", "2", "3"]

class TriageRecord(TypedDict):
    id: str
    incidentType: IncidentType
    location: str
    date: str
    time: str
    message: str
    desc: str
    suggested_actions: SuggestedActions
    status: Status
    severity_level: SeverityLevel
# --- End of New Schema ---


def validate_record(record: dict) -> TriageRecord:
    """Validate record matches the Triage Agent JSON schema"""
    required_fields = [
        "id", "incidentType", "location", "date", "time", 
        "message", "desc", "suggested_actions", "status", "severity_level"
    ]
    
    for field in required_fields:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(record["id"], str) or len(record["id"]) != 26:
        raise ValueError("Invalid 'id' field. Must be a 26-character ULID string.")

    valid_types = {
        "Public Nuisance", "Break In", "Armed Robbery", "Car Theft", 
        "Theft", "PickPocket", "Fire", "Mass Fire", "Crowd Stampede", "Terrorist Attack"
    }
    if record["incidentType"] not in valid_types:
        raise ValueError(f"Invalid incidentType: {record['incidentType']}")

    if not re.match(r"^[A-Z]\d[A-Z] \d[A-Z]\d$", record["location"]):
        raise ValueError(f"Invalid location format for postal code: {record['location']}")

    try:
        datetime.strptime(record["date"], "%m/%d/%Y")
    except ValueError:
        raise ValueError(f"Invalid date format for date: {record['date']}. Expected MM/DD/YYYY.")

    try:
        datetime.strptime(record["time"], "%H:%M")
    except ValueError:
        raise ValueError(f"Invalid time format for time: {record['time']}. Expected HH:MM.")

    valid_actions = {
        "console", "ask for more details", "dispatch officer", 
        "dispatch first-aiders", "dispatch firefighters"
    }
    if record["suggested_actions"] not in valid_actions:
        raise ValueError(f"Invalid suggested_actions: {record['suggested_actions']}")

    if record["status"] not in {"in progress", "completed"}:
        raise ValueError(f"Invalid status: {record['status']}. Must be 'in progress' or 'completed'.")

    if record["severity_level"] not in {"1", "2", "3"}:
        raise ValueError(f"Invalid severity_level: {record['severity_level']}. Must be '1', '2', or '3'.")
    
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
        incident = json.loads(json_data)
        validated = validate_record(incident)
        
        # This function signature is based on other scripts in the project.
        dense_index.upsert_records("incidents", [validated])
        print(f"Successfully added incident {validated['id']}")
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
    """
    try:
        incident = json.loads(json_data)
        # Use 'desc' for the query text, matching the new schema
        query_text = incident.get("desc", "")
        if not query_text:
            return []

        # Get metadata from input incident using new field names
        input_type = incident.get("incidentType", "")
        input_location = incident.get("location", "")
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
                # Use 'desc' for reranking
                "rank_fields": ["desc"]
            }
        )

        q_norm = _norm_text(query_text)
        similar_incidents = []
        
        for hit in results.get('result', {}).get('hits', []):
            # Extract fields from result using new names
            hit_text = hit['fields'].get('desc', '')
            hit_type = hit['fields'].get('incidentType', '')
            hit_location = hit['fields'].get('location', '')
            hit_date = hit['fields'].get('date', '')
            hit_time = hit['fields'].get('time', '')
            
            # Apply metadata filters
            if match_incident_type and hit_type != input_type:
                continue
            if match_postal_code and hit_location != input_location:
                continue
            if match_date and hit_date != input_date:
                continue
            if match_time and not _time_within_window(input_time, hit_time, time_window_minutes):
                continue
            
            h_norm = _norm_text(hit_text)
            score = float(hit.get('_score', 0.0))

            is_exact = (q_norm == h_norm)
            
            if is_exact or score >= similarity_threshold:
                similar_incidents.append({
                    "id": hit['id'],
                    "score": round(score, 4),
                    "is_exact_duplicate": is_exact,
                    "desc": hit_text,
                    "incidentType": hit_type,
                    "location": hit_location,
                    "date": hit_date,
                    "time": hit_time,
                    "metadata_match": {
                        "incidentType": hit_type == input_type,
                        "location": hit_location == input_location,
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


