import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone

records = [
    { "_id": "rec1", "chunk_text": "Structure fire at downtown warehouse. Multiple units responding. High priority.", "category": "fire" },
    { "_id": "rec2", "chunk_text": "Vehicle collision on Highway 101 near exit 42. Two cars involved. Minor injuries reported.", "category": "traffic" },
    { "_id": "rec3", "chunk_text": "Medical emergency: Chest pain at 456 Oak Street. Ambulance dispatched.", "category": "medical" },
    { "_id": "rec4", "chunk_text": "Robbery in progress at convenience store on 5th Avenue. Suspect armed.", "category": "crime" },
    { "_id": "rec5", "chunk_text": "House fire spreading rapidly at 123 Maple Lane. Residents evacuating.", "category": "fire" },
    { "_id": "rec6", "chunk_text": "Cardiac arrest patient at Central Park. CPR in progress. AED deployed.", "category": "medical" },
    { "_id": "rec7", "chunk_text": "Multi-vehicle pileup on Interstate 95. Traffic backed up for miles.", "category": "traffic" },
    { "_id": "rec8", "chunk_text": "Burglary reported at residential home on Pine Street. Police investigating.", "category": "crime" },
    { "_id": "rec9", "chunk_text": "Severe allergic reaction at school. Child needs immediate medical attention.", "category": "medical" },
    { "_id": "rec10", "chunk_text": "Commercial building fire with possible entrapment. Rescue units on scene.", "category": "fire" },
    { "_id": "rec11", "chunk_text": "Hit and run accident on Main Street. Victim transported to hospital.", "category": "traffic" },
    { "_id": "rec12", "chunk_text": "Assault in progress at downtown bar. Multiple subjects involved.", "category": "crime" },
    { "_id": "rec13", "chunk_text": "Diabetic emergency: Patient unresponsive. Glucose levels critical.", "category": "medical" },
    { "_id": "rec14", "chunk_text": "Wildfire spreading near residential area. Evacuation orders issued.", "category": "fire" },
    { "_id": "rec15", "chunk_text": "Pedestrian struck by vehicle on Harbor Boulevard. Injuries unknown.", "category": "traffic" },
    { "_id": "rec16", "chunk_text": "Armed robbery at bank downtown. Suspects fleeing northbound.", "category": "crime" },
    { "_id": "rec17", "chunk_text": "Severe burns sustained at construction site. Victim needs burn unit.", "category": "medical" },
    { "_id": "rec18", "chunk_text": "Apartment complex fire. Multiple residents needing rescue.", "category": "fire" },
    { "_id": "rec19", "chunk_text": "Motorcycle crash on Sunset Road. Rider ejected from vehicle.", "category": "traffic" },
    { "_id": "rec20", "chunk_text": "Domestic violence situation. Victim requesting police assistance.", "category": "crime" },
    { "_id": "rec21", "chunk_text": "Respiratory distress in elderly patient. Oxygen needed immediately.", "category": "medical" },
    { "_id": "rec22", "chunk_text": "Brush fire threatening nearby homes. Firefighters establishing perimeter.", "category": "fire" },
    { "_id": "rec23", "chunk_text": "Rear-end collision on freeway. Three vehicles involved. Road hazards.", "category": "traffic" },
    { "_id": "rec24", "chunk_text": "Shoplifting in progress at mall. Security pursuing suspect.", "category": "crime" },
    { "_id": "rec25", "chunk_text": "Stroke symptoms: Patient slurring speech and facial drooping.", "category": "medical" },
    { "_id": "rec26", "chunk_text": "Industrial plant fire with chemical hazards. Hazmat team called.", "category": "fire" },
    { "_id": "rec27", "chunk_text": "Head-on collision on rural road. Both drivers trapped in vehicles.", "category": "traffic" },
    { "_id": "rec28", "chunk_text": "Break-in at jewelry store. Alarm triggered. Police en route.", "category": "crime" },
    { "_id": "rec29", "chunk_text": "Overdose suspected. Patient unresponsive. Narcan administered.", "category": "medical" },
    { "_id": "rec30", "chunk_text": "Vehicle fire on side of highway. Potential explosion risk.", "category": "fire" },
    { "_id": "rec31", "chunk_text": "Train derailment near downtown. Multiple cars off tracks.", "category": "traffic" },
    { "_id": "rec32", "chunk_text": "Home invasion in progress. Residents barricaded in safe room.", "category": "crime" },
    { "_id": "rec33", "chunk_text": "Severe laceration requiring stitches. Heavy bleeding from wound.", "category": "medical" },
    { "_id": "rec34", "chunk_text": "Dumpster fire in alley. Smoke spreading to nearby businesses.", "category": "fire" },
    { "_id": "rec35", "chunk_text": "Bus accident with pedestrians. Multiple casualties reported.", "category": "traffic" },
    { "_id": "rec36", "chunk_text": "Stolen vehicle report. White sedan spotted heading south.", "category": "crime" },
    { "_id": "rec37", "chunk_text": "Poisoning suspected. Patient vomiting and in severe pain.", "category": "medical" },
    { "_id": "rec38", "chunk_text": "School building fire during daytime. Evacuation in progress.", "category": "fire" },
    { "_id": "rec39", "chunk_text": "Hazardous materials spill on roadway. Lane closure required.", "category": "traffic" },
    { "_id": "rec40", "chunk_text": "Carjacking reported. Victim safe but vehicle missing.", "category": "crime" },
    { "_id": "rec41", "chunk_text": "Severe burns from kitchen fire. Victim requiring ICU care.", "category": "medical" },
    { "_id": "rec42", "chunk_text": "Gas leak detected in apartment building. Evacuation ordered.", "category": "fire" },
    { "_id": "rec43", "chunk_text": "Train-car collision at railroad crossing. Injuries reported.", "category": "traffic" },
    { "_id": "rec44", "chunk_text": "Drug dealing operation busted. Multiple arrests made.", "category": "crime" },
    { "_id": "rec45", "chunk_text": "Broken bone sustained in fall. Immobilization required.", "category": "medical" },
    { "_id": "rec46", "chunk_text": "Electrical fire in office building. Power cut off. Evacuation.", "category": "fire" },
    { "_id": "rec47", "chunk_text": "Tractor-trailer jackknife. Multiple lane blockage. Cleanup needed.", "category": "traffic" },
    { "_id": "rec48", "chunk_text": "Sexual assault reported. Suspect still at large. BOLO issued.", "category": "crime" },
    { "_id": "rec49", "chunk_text": "Choking victim. Heimlich maneuver needed. Rescue units dispatched.", "category": "medical" },
    { "_id": "rec50", "chunk_text": "Warehouse explosion. Large debris field. Search and rescue ongoing.", "category": "fire" }
]

load_dotenv()

pinecone_key=os.getenv("PINECONE_API_KEY")

pc = Pinecone(pinecone_key)

index_name = "dispatch"
if not pc.has_index(index_name):
    pc.create_index_for_model(
        name=index_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model":"llama-text-embed-v2",
            "field_map":{"text": "chunk_text"}
        }
    )

dense_index = pc.Index(index_name)

dense_index.upsert_records("Test", records)

time.sleep(10)

stats = dense_index.describe_index_stats()
print(stats)

query = "residential fire"
results = dense_index.search(
    namespace="Test",
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
        print(f"id: {hit['_id']:<5} | score: {round(hit['_score'], 2):<5} | category: {hit['fields']['category']:<10} | text: {hit['fields']['chunk_text']:<50}")

print("Search complete.")