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


app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

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
    
    prompt = f"""You are a 911 call dispatcher assistant. Extract the following information from the caller's transcript and output ONLY a JSON object (no other text).

Required fields:
- incidentType: classify as one of: "Public Nuisance", "Break In", "Armed Robbery", "Car Theft", "Theft", "PickPocket", "Fire", "Mass Fire", "Crowd Stampede", "Terrorist Attack", "other"
- location: extract and format as a Canadian postal code (format: L#L#L# where L=letter, #=digit, e.g., "M5H2N2"). If unclear, make best guess.
- date: format as "month/day/year" (e.g., "1/10/2026")
- time: format as 24-hour time "HH:MM" (e.g., "14:30")

Transcript text: {transcript.text}
Transcript time: {transcript.time}
Transcript location hint: {transcript.location}

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
    """
    triage_incident = state["triage_incident"]
    
    print(f"TRIAGE CHECKPOINT: {triage_incident.model_dump_json()}")

    # Calculate priority score: current time - (severity * 30 minutes)
    # Higher severity gets a lower score (higher priority)
    severity_int = int(triage_incident.severity_level)
    score = time.time() - (severity_int * 1800)

    def _enum_value(value: Any):
        return value.value if hasattr(value, "value") else value
    
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

    # Append the full triage incident JSON to Pinecone for downstream analytics
    triage_full_payload = triage_incident.model_dump()
    timestamped = state.get("timestamped_transcript")
    if timestamped is not None:
        triage_full_payload["transcript"] = timestamped
        print(f"[enqueue] Appending timestamped transcript with {len(timestamped) if isinstance(timestamped, list) else 'unknown count'} segments")
    else:
        print("[enqueue] No timestamped transcript to append to Pinecone payload")
    pinecone_json = json.dumps(triage_full_payload)
    print(f"ACTION: enqueue_pinecone {pinecone_json}")
    pinecone_ok = add_incident(pinecone_json)
    if pinecone_ok:
        print(f"[enqueue] Pinecone: indexed incident {triage_incident.id}")
    else:
        print(f"[enqueue] Pinecone: failed to index incident {triage_incident.id}")
    await redis_client.set(f"triage_full:{triage_incident.id}", pinecone_json)
    print(f"[enqueue] Cached full Pinecone payload for {triage_incident.id}")
    
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
        
        return {"result": triage_incident.model_dump()}
        
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
    """Retrieve a single incident by ULID from Pinecone."""
    if not os.getenv("PINECONE_API_KEY"):
        raise HTTPException(status_code=500, detail="Pinecone API key is not configured.")

    try:
        record = get_incident_by_id(incident_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if record is None:
        raise HTTPException(status_code=404, detail="Incident not found.")

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

    cache_key = f"triage_full:{incident_id}"
    cached_payload = await redis_client.get(cache_key)
    if not cached_payload:
        print(f"[remove] No cached full payload found for {incident_id}")
        print(f"ACTION: remove_status_update {{\"status\": \"missing cached payload\"}}")
        return {"removed": removed, "status_update": "missing cached payload"}

    try:
        full_record = json.loads(cached_payload)
    except json.JSONDecodeError:
        print(f"[remove] Cached payload was malformed for {incident_id}")
        raise HTTPException(status_code=500, detail="Cached payload corrupted")

    previous_status = full_record.get("status")
    full_record["status"] = "completed"
    print(f"ACTION: remove_status_update {json.dumps(full_record)}")
    status_updated = add_incident(json.dumps(full_record))
    if status_updated:
        print(f"[remove] Updated status from {previous_status} to completed for {incident_id}")
        await redis_client.delete(cache_key)
    else:
        print(f"[remove] Failed to update Pinecone status for {incident_id}")

    return {"removed": removed, "status_update": "completed" if status_updated else "failed"}


call_times = {}

# incoming web hook for Twilio calls 
@app.post("/call")
async def incoming_call(CallSid: str = Form(None)):
    """Webhook to receive calls."""
    response = VoiceResponse()
    call_times[CallSid] = datetime.utcnow().isoformat()
    response.say("911, please describe your emergency. Press the star key when you are finished.")
    response.record(finish_on_key="*", action=f"/recording-finished?CallSid={CallSid}", method="POST")
    return Response(content=str(response), media_type="application/xml")

# send the recording back to Twilo to upload 
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

def transcribe_enqueue(src: str, call_start_time: str):
    import asyncio
    content = transcribe_url(src, call_start_time)
    asyncio.run(invoke_workflow({"transcript": content.get("process_transcript"), "location": content.get("location", ""), "time": content.get("call_start_time"), "duration": content.get("duration")}, content.get("transcript")))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
