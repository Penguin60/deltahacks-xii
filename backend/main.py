import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import TypedDict, NotRequired, Optional
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi import FastAPI, Body, Response, Request, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any
from datetime import datetime
import traceback
from twilio.twiml.voice_response import VoiceResponse
from backend.transcribe_audio import transcribe_url
from backend.schemas import (
    TranscriptIn,
    CallIncident,
    AssessmentIncident,
    TriageIncident,
    IncidentType,
    SuggestedAction
)
import ulid


# Construct the absolute path to the .env file and load it
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Global model init (critical for Gemini to avoid blocking errors)
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # Or your preferred Gemini model
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)

import json
import time
from backend.redis_client import redis_client
from backend.vector_store import find_similar_incidents, add_incident, get_incident_by_id

DEBUG_LOG_PATH = "/Users/tlam/delta/.cursor/debug.log"

def _agent_log(payload: dict) -> None:
    """Append one NDJSON line for debug-mode evidence (no secrets)."""
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        # Never let debug logging break app flow
        pass


app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware


TRIAGE_FULL_PAYLOADS_LIST_KEY = "triage_full_payloads"


""" 
NOTE: this function is commented out; run the script for every demo instead! 
@app.on_event("startup")
async def startup_event():
    # Clear full payload list for a clean slate (demo/dev behavior)
    Reset full payload storage on dev server startup
    deleted = await redis_client.delete(TRIAGE_FULL_PAYLOADS_LIST_KEY)
    print(
        f"[startup] Cleared full payload list ({TRIAGE_FULL_PAYLOADS_LIST_KEY}), deleted={deleted}"
    ) """

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentState(TypedDict, total=False):
    """State for the incident triage pipeline"""
    transcript: NotRequired[TranscriptIn]
    timestamped_transcript: NotRequired[Any]
    call_incident: NotRequired[CallIncident]
    assessment_incident: NotRequired[AssessmentIncident]
    triage_incident: NotRequired[TriageIncident]


def _extract_json_block(content: str) -> str:
    """Extract JSON from LLM response, handling code blocks"""
    text = content.strip()
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text


# Agent 1: call_agent - Extract core incident fields from transcript
async def call_agent_node(state: AgentState):
    """
    Extracts caller's provided information from transcript into structured JSON.
    Outputs: incidentType, location (postal code), date, time
    """
    transcript = state["transcript"]
    if isinstance(transcript, dict):
        transcript = TranscriptIn(**transcript)
    
    prompt = f"""You are a 911 call dispatcher assistant. Extract the following information from the caller's transcript and output ONLY a JSON object (no other text).

Required fields:
- incidentType: classify as one of: "Public Nuisance", "Break In", "Armed Robbery", "Car Theft", "Theft", "PickPocket", "Fire", "Mass Fire", "Crowd Stampede", "Terrorist Attack", "Other"
- location: extract and format as a Canadian postal code (format: L#L#L# where L=letter, #=digit, e.g., "M5H2N2"). If unclear, make best guess.
- date: format as "month/day/year" (e.g., "1/10/2026")
- time: format as 24-hour time "HH:MM" (e.g., "14:30")

Transcript text: {transcript.text}
Transcript time: {transcript.time}
Transcript location hint: {transcript.location}
EXTREMELY_IMPORTANT: Do not enclose the JSON with 3 backticks, ```.

Output ONLY valid JSON with these exact fields: incidentType, location, date, time
JSON:"""
    
    try:
        print(f"[call_agent] Prompt: {prompt}")
        response = await model.ainvoke(prompt)
        json_str = _extract_json_block(response.content)
        parsed = json.loads(json_str)
        
        # Generate ULID and add required fields
        incident_id = str(ulid.new())
        parsed["id"] = incident_id
        parsed["message"] = transcript.text  # Force original transcript text
        # Ensure duration is present (LLM prompt does not request it)
        if "duration" not in parsed or parsed["duration"] in (None, ""):
            parsed["duration"] = transcript.duration
        
        # Validate with Pydantic
        call_incident = CallIncident(**parsed)
        
        print(f"[call_agent] Extracted incident: {call_incident.incidentType}, location: {call_incident.location}")
        print(f"[call_incident] FULL JSON OUTPUT: {call_incident.model_dump_json()}") # check output of agent 1 
        return {"call_incident": call_incident}
        
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[call_agent] Error parsing LLM output: {e}")
        print(f"[call_agent] Raw LLM output: {response.content if 'response' in locals() else 'N/A'}")
        raise HTTPException(status_code=422, detail=f"Failed to parse call agent output: {str(e)}")
    except Exception as e:
        print(f"[call_agent] Unexpected error: {e}")
        traceback.print_exc()
        raise


# Agent 2: assessment_agent - Add description and suggested action
async def assessment_agent_node(state: AgentState):
    """
    Adds AI-generated description and suggested action based on incident details.
    Outputs: desc (summary), suggested_actions
    """
    call_incident = state["call_incident"]
    
    prompt = f"""You are a 911 dispatcher assistant. Based on the incident details, generate a concise one-line description and suggest an appropriate action.

Incident details:
- Type: {call_incident.incidentType}
- Location: {call_incident.location}
- Date/Time: {call_incident.date} at {call_incident.time}
- Caller message: {call_incident.message}

Output ONLY a JSON object with these exact fields:
- desc: a one-line description/summary of the incident (max 150 chars)
- suggested_actions: choose ONE from: "console", "ask for more details", "dispatch officer", "dispatch first-aiders", "dispatch firefighters"

JSON:"""
    
    try:
        print(f"[assessment_agent] Prompt: {prompt}")
        response = await model.ainvoke(prompt)
        json_str = _extract_json_block(response.content)
        parsed = json.loads(json_str)
        
        # Merge with call_incident data and add hard-coded fields
        incident_data = call_incident.model_dump()
        incident_data.update(parsed)
        incident_data["status"] = "called"  # Hard-coded
        incident_data["severity_level"] = "none"  # Hard-coded
        
        # Validate with Pydantic
        assessment_incident = AssessmentIncident(**incident_data)
        
        print(f"[assessment_agent] Added desc: {assessment_incident.desc[:50]}...")
        print(f"[assessment_agent] Suggested action: {assessment_incident.suggested_actions}")
        print(f"[assessment_agent] FULL JSON FROM AGENT 2: {assessment_incident.model_dump_json()}") # check the full JSON output 
        return {"assessment_incident": assessment_incident}
        
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[assessment_agent] Error parsing LLM output: {e}")
        print(f"[assessment_agent] Raw LLM output: {response.content if 'response' in locals() else 'N/A'}")
        raise HTTPException(status_code=422, detail=f"Failed to parse assessment agent output: {str(e)}")
    except Exception as e:
        print(f"[assessment_agent] Unexpected error: {e}")
        traceback.print_exc()
        raise


# Agent 3: triage_agent - Assign severity level
async def triage_agent_node(state: AgentState):
    """
    Classifies incident severity and prepares for queue.
    Outputs: severity_level ("1", "2", or "3")
    """
    assessment_incident = state["assessment_incident"]
    
    prompt = f"""You are a 911 triage specialist. Classify the severity of this incident from 1 to 3:

Severity levels:
- "1": Nuisance, minor injuries, non-threatening (e.g., noise complaints, minor theft)
- "2": Injuries inflicted, potentially life-threatening (e.g., break-ins, robberies, small fires)
- "3": Life-threatening, urgent, immediate action required (e.g., armed robbery, mass fire, terrorist attack)

Incident details:
- Type: {assessment_incident.incidentType}
- Description: {assessment_incident.desc}
- Location: {assessment_incident.location}
- Message: {assessment_incident.message}

Output ONLY a JSON object with this exact field:
- severity_level: must be "1", "2", or "3" (as a string)

JSON:"""
    
    try:
        print(f"[triage_agent] Prompt: {prompt}")
        response = await model.ainvoke(prompt)
        json_str = _extract_json_block(response.content)
        parsed = json.loads(json_str)
        
        # Merge with assessment data and override status
        incident_data = assessment_incident.model_dump()
        incident_data["severity_level"] = parsed["severity_level"]
        incident_data["status"] = "in progress"  # Hard-coded for queue
        
        # Validate with Pydantic
        triage_incident = TriageIncident(**incident_data)
        
        print(f"[triage_agent] Assigned severity: {triage_incident.severity_level}")
        print(f"[triage_agent] FULL JSON FROM AGENT 3: {triage_incident.model_dump_json()}") 
        # check the full JSON output of agent 3
        return {"triage_incident": triage_incident}
        
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[triage_agent] Error parsing LLM output: {e}")
        print(f"[triage_agent] Raw LLM output: {response.content if 'response' in locals() else 'N/A'}")
        raise HTTPException(status_code=422, detail=f"Failed to parse triage agent output: {str(e)}")
    except Exception as e:
        print(f"[triage_agent] Unexpected error: {e}")
        traceback.print_exc()
        raise


# Enqueue node: Add to Redis sorted set
async def enqueue_node(state: AgentState):
    """
    Add the final triage incident to Redis ZSET for queue processing.
    Lower score = higher priority (more urgent).
    Skips adding if a similar incident already exists.
    """
    triage_incident = state["triage_incident"]
    
    print(f"TRIAGE CHECKPOINT: {triage_incident.model_dump_json()}")

    def _enum_value(value: Any):
        return value.value if hasattr(value, "value") else value

    # Build the full payload first for duplicate checking
    triage_full_payload = triage_incident.model_dump()
    # Convert enum values to strings for JSON serialization
    triage_full_payload["incidentType"] = _enum_value(triage_full_payload.get("incidentType"))
    triage_full_payload["suggested_actions"] = _enum_value(triage_full_payload.get("suggested_actions"))
    
    timestamped = state.get("timestamped_transcript")
    if timestamped is not None:
        triage_full_payload["transcript"] = timestamped
        print(f"[enqueue] Appending timestamped transcript with {len(timestamped) if isinstance(timestamped, list) else 'unknown count'} segments")
    else:
        print("[enqueue] No timestamped transcript to append to Pinecone payload")

    pinecone_json = json.dumps(triage_full_payload)

    # Check for similar/duplicate incidents before adding
    similar_incidents = find_similar_incidents(pinecone_json, similarity_threshold=0.7)
    if similar_incidents:
        print(f"[enqueue] Found {len(similar_incidents)} similar incident(s), skipping duplicate:")
        for dup in similar_incidents:
            print(f"  - ID: {dup['id']}, Score: {dup['score']}, Exact: {dup['is_exact_duplicate']}")
        print(f"[enqueue] Incident {triage_incident.id} NOT added (duplicate of {similar_incidents[0]['id']})")
        _agent_log({
            "sessionId": "debug-session",
            "runId": "pre-fix-2",
            "hypothesisId": "J",
            "location": "backend/main.py:enqueue_node:duplicate",
            "message": "Similarity hit; skipping enqueue to Redis",
            "data": {
                "newIncidentId": getattr(triage_incident, "id", None),
                "duplicateOf": similar_incidents[0].get("id"),
                "similarCount": len(similar_incidents),
            },
            "timestamp": int(time.time() * 1000),
        })
        return {"duplicate_of": similar_incidents[0]["id"]}

    # Calculate priority score: current time - (severity * 30 minutes)
    # Higher severity gets a lower score (higher priority)
    severity_int = int(triage_incident.severity_level)
    score = time.time() - (severity_int * 1800)
    
    # Store only the minimal queue payload
    queue_entry = {
        "id": triage_incident.id,
        "incidentType": _enum_value(triage_incident.incidentType),
        "location": triage_incident.location,
        "time": triage_incident.time,
        "severity_level": triage_incident.severity_level,
        "suggested_actions": _enum_value(triage_incident.suggested_actions),
    }
    item_json = json.dumps(queue_entry)
    print(f"[enqueue] Queue entry payload: {item_json}")
    print(f"ACTION: enqueue_queue {item_json}")
    
    print(f"[enqueue] Adding to queue - ID: {triage_incident.id}, Severity: {severity_int}, Score: {score}")
    await redis_client.zadd("triage_queue", {item_json: score})
    
    # Log queue state
    queue_size = await redis_client.zcard("triage_queue")
    print(f"[enqueue] Queue size: {queue_size}")

    # Store full payload in Redis using a separate data structure (list) (before Pinecone, no TTL)
    await redis_client.rpush(TRIAGE_FULL_PAYLOADS_LIST_KEY, pinecone_json)
    print(
        f"[enqueue] Appended full payload for {triage_incident.id} to {TRIAGE_FULL_PAYLOADS_LIST_KEY}"
    )

    # Add to Pinecone for downstream analytics
    print(f"ACTION: enqueue_pinecone {pinecone_json}")
    pinecone_ok = add_incident(pinecone_json)
    if pinecone_ok:
        print(f"[enqueue] Pinecone: indexed incident {triage_incident.id}")
    else:
        print(f"[enqueue] Pinecone: failed to index incident {triage_incident.id}")
    
    return {}  # No state changes, just side effect

# Build the incident triage pipeline graph
# Flow: START -> call_agent -> assessment_agent -> triage_agent -> enqueue -> END
workflow = StateGraph(state_schema=AgentState)
workflow.add_node("call_agent", call_agent_node)
workflow.add_node("assessment_agent", assessment_agent_node)
workflow.add_node("triage_agent", triage_agent_node)
workflow.add_node("enqueue", enqueue_node)

workflow.add_edge(START, "call_agent")
workflow.add_edge("call_agent", "assessment_agent")
workflow.add_edge("assessment_agent", "triage_agent")
workflow.add_edge("triage_agent", "enqueue")
workflow.add_edge("enqueue", END)

graph = workflow.compile()


class InvokeRequest(BaseModel):
    """Request body for the /invoke endpoint"""
    transcript: TranscriptIn
    timestamped_transcript: Any = None


@app.post("/invoke")
async def invoke_workflow(request: InvokeRequest):
    """
    Process a transcript through the 3-agent pipeline and enqueue for triage.
    
    Input: TranscriptIn (text, time, location)
    Output: TriageIncident JSON (the final incident that was enqueued)
    """
    try:
        # Debug logging to verify request payload
        transcript = request.transcript
        timestamped = request.timestamped_transcript
        print(
            "[invoke] Received body:",
            {
                "text_len": len(transcript.text) if transcript and transcript.text else 0,
                "time": transcript.time if transcript else None,
                "location": transcript.location if transcript else None,
                "duration": transcript.duration if transcript else None,
                "timestamped_count": len(timestamped) if isinstance(timestamped, list) else "n/a",
            },
        )

        result = await graph.ainvoke({
            "transcript": request.transcript,
            "timestamped_transcript": request.timestamped_transcript,
        })
        
        # Return the final triage incident
        triage_incident = result.get("triage_incident")
        if not triage_incident:
            raise HTTPException(status_code=500, detail="Pipeline did not produce triage incident")

        duplicate_of = result.get("duplicate_of")
        enqueued = duplicate_of is None
        if duplicate_of is not None:
            notice = "Similar incident detected; this call was not added to the live queue."
        else:
            notice = None

        _agent_log({
            "sessionId": "debug-session",
            "runId": "pre-fix-2",
            "hypothesisId": "K",
            "location": "backend/main.py:invoke_workflow:response",
            "message": "Invoke completed",
            "data": {
                "incidentId": getattr(triage_incident, "id", None),
                "enqueued": enqueued,
                "duplicateOf": duplicate_of,
            },
            "timestamp": int(time.time() * 1000),
        })

        # NOTE: clients can use `enqueued=false` to show a toast/banner for this specific call
        response_payload = {
            "result": triage_incident.model_dump(),
            "enqueued": enqueued,
            "duplicate_of": duplicate_of,
            "notice": notice,
        }
        # Safe print: do NOT print transcript/message text (PII risk)
        print(
            "[invoke] Response summary:",
            json.dumps(
                {
                    "incidentId": getattr(triage_incident, "id", None),
                    "enqueued": enqueued,
                    "duplicate_of": duplicate_of,
                    "notice": notice,
                }
            ),
        )
        return response_payload
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[invoke] Unexpected error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")

@app.get("/queue")
async def get_queue():
    queue_summary = []
    raw_entries = await redis_client.zrange("triage_queue", 0, -1)
    for raw_entry in raw_entries:
        try:
            entry = json.loads(raw_entry)
            queue_summary.append(entry)
        except json.JSONDecodeError:
            print("[queue] Failed to decode queue entry:", raw_entry)
    print(f"[queue] Returning {len(queue_summary)} entries")
    print(f"ACTION: queue_return {json.dumps(queue_summary)}")
    return queue_summary


@app.get("/agent/{incident_id}")
async def get_agent(incident_id: str):
    """Retrieve a single incident by ULID. Checks Redis cache first, falls back to Pinecone."""
    
    # First, check Redis list cache for a matching ULID
    cached_entries = await redis_client.lrange(TRIAGE_FULL_PAYLOADS_LIST_KEY, 0, -1)
    for cached_payload in cached_entries:
        try:
            record = json.loads(cached_payload)
        except json.JSONDecodeError:
            continue
        if record.get("id") == incident_id:
            print(
                f"[get_agent] Found incident {incident_id} in Redis list {TRIAGE_FULL_PAYLOADS_LIST_KEY}"
            )
            return {"result": record}
    
    # Fall back to Pinecone
    if not os.getenv("PINECONE_API_KEY"):
        raise HTTPException(status_code=500, detail="Pinecone API key is not configured.")

    try:
        record = get_incident_by_id(incident_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if record is None:
        raise HTTPException(status_code=404, detail="Incident not found.")

    print(f"[get_agent] Found incident {incident_id} in Pinecone")
    return {"result": record}


@app.delete("/remove/{incident_id}")
async def remove_incident(incident_id: str):
    raw_entries = await redis_client.zrange("triage_queue", 0, -1)
    matched_entry = None
    for entry in raw_entries:
        try:
            payload = json.loads(entry)
        except json.JSONDecodeError:
            continue
        if payload.get("id") == incident_id:
            matched_entry = entry
            break

    if not matched_entry:
        print(f"[remove] No queue entry found for {incident_id}")
        raise HTTPException(status_code=404, detail="Incident not found in queue")

    print(f"ACTION: remove_match {matched_entry}")
    removed = await redis_client.zrem("triage_queue", matched_entry)
    print(f"[remove] Removed {removed} queue entries for {incident_id}")
    print(f"ACTION: remove_result {{\"removed\": {removed}}}")

    matched_payload_raw = None
    matched_full_record = None
    cached_entries = await redis_client.lrange(TRIAGE_FULL_PAYLOADS_LIST_KEY, 0, -1)
    for cached_payload in cached_entries:
        try:
            record = json.loads(cached_payload)
        except json.JSONDecodeError:
            continue
        if record.get("id") == incident_id:
            matched_payload_raw = cached_payload
            matched_full_record = record
            break

    if not matched_full_record or not matched_payload_raw:
        print(
            f"[remove] No cached full payload found for {incident_id} in {TRIAGE_FULL_PAYLOADS_LIST_KEY}"
        )
        print(f"ACTION: remove_status_update {{\"status\": \"missing cached payload\"}}")
        return {"removed": removed, "status_update": "missing cached payload"}

    previous_status = matched_full_record.get("status")
    matched_full_record["status"] = "completed"
    print(f"ACTION: remove_status_update {json.dumps(matched_full_record)}")
    status_updated = add_incident(json.dumps(matched_full_record))
    if status_updated:
        print(f"[remove] Updated status from {previous_status} to completed for {incident_id}")
        # Remove the cached entry from the list (first occurrence)
        await redis_client.lrem(TRIAGE_FULL_PAYLOADS_LIST_KEY, 1, matched_payload_raw)
    else:
        print(f"[remove] Failed to update Pinecone status for {incident_id}")

    return {"removed": removed, "status_update": "completed" if status_updated else "failed"}


call_times = {}
call_numbers = {}
# will add phone numbers

# incoming web hook for Twilio calls 
@app.post("/call")
async def incoming_call(CallSid: str = Form(None)):
    """Webhook to receive calls."""
    response = VoiceResponse()
    call_times[CallSid] = datetime.utcnow().isoformat()
    response.say("911, please describe your emergency. Press the star key when you are finished.")
    response.record(finish_on_key="*", action=f"/recording-finished?CallSid={CallSid}", method="POST")
    return Response(content=str(response), media_type="application/xml")

# send the recording back to Twilio to upload 
@app.post("/recording-finished")
async def upload_recording(request: Request, background: BackgroundTasks):
    """Transcribes the recording."""
    form = await request.form()
    recording_url = form.get("RecordingUrl")
    recording_sid = form.get("RecordingSid")
    call_sid = request.query_params.get("CallSid")
    call_start_time = call_times.get(call_sid)
    print(f"Recording URL: {recording_url}")
    print(f"Recording SID: {recording_sid}")
    print(f"Call SID: {call_sid}")
    print(f"Call started at: {call_start_time}")

    if recording_url:
        background.add_task(transcribe_enqueue, recording_url, call_start_time)
    
    response = VoiceResponse()
    response.say("Thank you for calling. A dispatcher will contact you shortly.")
    response.hangup()
    return Response(content=str(response), media_type="application/xml")

async def transcribe_enqueue(src: str, call_start_time: str):
    import asyncio
    content = transcribe_url(src, call_start_time)
    transcript_payload = TranscriptIn(
        text=content.get("process_transcript", ""),
        time=content.get("call_start_time", ""),
        location=content.get("location", ""),
        duration=content.get("duration", ""),
    )

    request_model = InvokeRequest(
        transcript=transcript_payload,
        timestamped_transcript=content.get("transcript"),
    )
    await invoke_workflow(request_model)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
