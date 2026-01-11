import json
import os
import time
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# NOTE: this script is run once to seed dummy data to demo the VDB and filtering logic to prevent 
# redudant entries from calls. 
from backend.vector_store import dense_index

SCHEMA_FILE = Path("backend/db.json")

def load_schema_fields() -> List[str]:
    """Read the schema metadata from `backend/db.json`."""
    try:
        with SCHEMA_FILE.open() as schema_file:
            schema_data = json.load(schema_file)
            fields = schema_data.get("final_payload_fields", [])
            if not fields:
                raise ValueError("Schema file does not define `final_payload_fields`.")
            return fields
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid schema JSON: {exc}") from exc


def load_and_add_incidents(json_file: str):
    """Load incidents from JSON file and add them to the Pinecone index."""
    try:
        with open(json_file, 'r') as f:
            incidents = json.load(f)
        
        if not incidents:
            print(f"No incidents found in {json_file}")
            return
        schema_fields = load_schema_fields()
        namespace = "incidents"
        print(f"\nFound {len(incidents)} incidents in {json_file}.")
        print(f"Enforcing schema fields from '{SCHEMA_FILE}' for each record.")

        normalized_incidents = []
        for incident in incidents:
            missing = [field for field in schema_fields if field not in incident]
            if missing:
                print(f"[static_additions] Incident {incident.get('id', '<unknown>')} missing {missing}, inserting defaults.")
                for field in missing:
                    incident[field] = [] if field == "transcript" else ""
            normalized_incidents.append(incident)

        print(f"Upserting {len(normalized_incidents)} records to Pinecone namespace '{namespace}'...")
        dense_index.upsert_records(namespace, normalized_incidents)
        
        print("Upsert command sent. Waiting 10 seconds for indexing to process...")
        time.sleep(10)
        
        print("Fetching index statistics...")
        stats = dense_index.describe_index_stats()
        print("\n--- Pinecone Index Stats ---")
        print(stats)
        print("--------------------------\n")

    except FileNotFoundError:
        print(f"Error: The file {json_file} was not found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file}.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Please ensure 'backend/vector_store.py' is updated for the new data format.")


if __name__ == "__main__":
    # Set the working directory to the project root for consistent path resolution.
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Load environment variables from 'backend/.env'
    env_path = Path("backend/.env")
    print(f"Checking for env file at {env_path.resolve()}")
    if env_path.exists():
        print(f"Found env file, loading variables from {env_path.resolve()}")
        load_dotenv(dotenv_path=env_path)
    else:
        print("Warning: 'backend/.env' file not found. Pinecone credentials may be missing.")

    json_file_path = "backend/sample_incidents.json"
    
    print(f"\nStarting one-time incident loading script for {json_file_path}...")
    load_and_add_incidents(json_file_path)
    print("Script finished.")