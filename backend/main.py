import os
from pathlib import Path
from dotenv import load_dotenv
from typing import TypedDict, NotRequired, Optional
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi import FastAPI, Body, Response, Request, Form, HTTPException
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any
from datetime import datetime
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
from ulid import ULID


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
from backend.vector_store import find_similar_incidents


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
        response = await model.ainvoke(prompt)
        json_str = _extract_json_block(response.content)
        parsed = json.loads(json_str)
        
        # Generate ULID and add required fields
        incident_id = str(ULID())
        parsed["id"] = incident_id
        parsed["message"] = transcript.text  # Force original transcript text
        
        # Validate with Pydantic
        call_incident = CallIncident(**parsed)
        
        print(f"[call_agent] Extracted incident: {call_incident.incidentType}, location: {call_incident.location}")
        return {"call_incident": call_incident}
        
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[call_agent] Error parsing LLM output: {e}")
        print(f"[call_agent] Raw LLM output: {response.content if 'response' in locals() else 'N/A'}")
        raise HTTPException(status_code=422, detail=f"Failed to parse call agent output: {str(e)}")


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
        return {"assessment_incident": assessment_incident}
        
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[assessment_agent] Error parsing LLM output: {e}")
        print(f"[assessment_agent] Raw LLM output: {response.content if 'response' in locals() else 'N/A'}")
        raise HTTPException(status_code=422, detail=f"Failed to parse assessment agent output: {str(e)}")


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
        return {"triage_incident": triage_incident}
        
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"[triage_agent] Error parsing LLM output: {e}")
        print(f"[triage_agent] Raw LLM output: {response.content if 'response' in locals() else 'N/A'}")
        raise HTTPException(status_code=422, detail=f"Failed to parse triage agent output: {str(e)}")


# Enqueue node: Add to Redis sorted set
async def enqueue_node(state: AgentState):
    """
    Add the final triage incident to Redis ZSET for queue processing.
    Lower score = higher priority (more urgent).
    """
    triage_incident = state["triage_incident"]
    
    # Calculate priority score: current time - (severity * 30 minutes)
    # Higher severity gets lower score (higher priority)
    severity_int = int(triage_incident.severity_level)
    score = time.time() - (severity_int * 1800)
    
    # Store the exact triage JSON
    item_json = triage_incident.model_dump_json()
    
    print(f"[enqueue] Adding to queue - ID: {triage_incident.id}, Severity: {severity_int}, Score: {score}")
    await redis_client.zadd("triage_queue", {item_json: score})
    
    # Log queue state
    queue_size = await redis_client.zcard("triage_queue")
    print(f"[enqueue] Queue size: {queue_size}")
    
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

@app.post("/invoke")
async def invoke_workflow(transcript: TranscriptIn = Body(...)):
    """
    Process a transcript through the 3-agent pipeline and enqueue for triage.
    
    Input: TranscriptIn (text, time, location)
    Output: TriageIncident JSON (the final incident that was enqueued)
    """
    try:
        result = await graph.ainvoke({"transcript": transcript})
        
        # Return the final triage incident
        triage_incident = result.get("triage_incident")
        if not triage_incident:
            raise HTTPException(status_code=500, detail="Pipeline did not produce triage incident")
        
        return {"result": triage_incident.model_dump()}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[invoke] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")

@app.get("/queue")
async def get_queue():
    queue_file_path = Path(__file__).parent / "dummy-queue.json"
    with open(queue_file_path) as f:
        data = json.load(f)
    
    queue_summary = []
    for incident in data:
        queue_summary.append({
            "id": incident.get("id"),
            "incidentType": incident.get("incidentType"),
            "location": incident.get("location"),
            "time": incident.get("time"),
            "severity_level": int(incident.get("severity_level", 1)), # Add severity_level, default to 1 and ensure int
            "callers": 1 # Default callers to 1
        })
    return queue_summary


call_times = {}

# incoming web hook for Twilo calls 
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
async def upload_recording(request: Request):
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
    
    response = VoiceResponse()
    response.say("Thank you for calling. A dispatcher will contact you shortly.")
    response.hangup()
    transcribe_url(recording_url)
    return Response(content=str(response), media_type="application/xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
