import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Note: The 'validate_record' and 'find_similar_incidents' imports are removed
# as the data schema has changed. These functions in 'vector_store.py'
# will need to be updated to work with the new JSON specification.
from backend.vector_store import dense_index

def load_and_add_incidents(json_file: str):
    """Load incidents from JSON file and add them to the Pinecone index."""
    try:
        with open(json_file, 'r') as f:
            incidents = json.load(f)
        
        if not incidents:
            print(f"No incidents found in {json_file}")
            return
        
        namespace = "incidents"
        print(f"\nFound {len(incidents)} incidents in {json_file}.")
        print(f"Upserting records to Pinecone namespace '{namespace}'...")
        
        # The validation step has been removed as the record schema has changed.
        # We are now passing the records directly to the upsert method.
        # The 'upsert_records' method is assumed to handle the new data structure.
        dense_index.upsert_records(namespace, incidents)
        
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
    if env_path.exists():
        print(f"Loading environment variables from {env_path.resolve()}")
        load_dotenv(dotenv_path=env_path)
    else:
        print("Warning: 'backend/.env' file not found. Pinecone credentials may be missing.")

    json_file_path = "backend/sample_incidents.json"
    
    print(f"\nStarting one-time incident loading script for {json_file_path}...")
    load_and_add_incidents(json_file_path)
    print("Script finished.")