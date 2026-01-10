import json
import time
from backend.vector_store import dense_index, validate_record, find_similar_incidents

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