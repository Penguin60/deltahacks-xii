import os
from pathlib import Path
from dotenv import load_dotenv
from typing import TypedDict, Annotated, NotRequired
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import operator
from fastapi import FastAPI, Body, Response, Request, Form
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
from twilio.twiml.voice_response import VoiceResponse
from backend.transcribe_audio import transcribe_url


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
    messages: Annotated[List[BaseMessage], add_messages]
    is_duplicate: NotRequired[bool]
    severity_level: NotRequired[int]
    classification_prompt: NotRequired[str]


def _extract_json_block(content: str) -> str:
    text = content.strip()
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text

# Agent1 node: First agent processes input
async def agent1(state: AgentState):
    msg = await model.ainvoke(state["messages"])
    return {"messages": [msg]}

# Middleware node: Custom function between agents (e.g., log/transform state)
async def middleware(state: AgentState):
    last_msg = state["messages"][-1].content
    

    print(f"Middleware: Processed '{last_msg[:50]}...'")  # Logging example

    # Extract incident details to check for duplicates in the vector DB
    extract_prompt = f"""Extract incident details from the following text into JSON format with fields: 
    - chunk_text (summary)
    - incidentType (one of: Public Nuisance, Break In, Armed Robbery, Car Theft, Theft, Pick Pocket, Fire, Mass Fire, Crowd Stampede, Terrorist Attack)
    - postal_code
    - severity_level (1, 2, or 3)
    - date (YYYY-MM-DD)
    - time (HH:MM)
    
    Text: {last_msg}
    JSON:"""
    
    extraction = await model.ainvoke(extract_prompt)
    json_str = _extract_json_block(extraction.content)

    try:
        similar = find_similar_incidents(json_str)
        if similar:
            print(False)
            return {"messages": state["messages"], "is_duplicate": True}
    except Exception as e:
        print(f"Error checking similar incidents: {e}")
    
    return {"messages": state["messages"], "is_duplicate": False}

def router(state: AgentState):
    if state.get("is_duplicate"):
        print("Duplicate incident found, ending workflow.")
        return END
    return "agent2"

# Agent2 node: Second agent finalizes
async def agent2(state: AgentState):
    final_message = state["messages"][-1]
    classification_prompt = (
        "Classify the following incident description into a severity level from 1 (lowest) to 3 (highest). "
        "Respond with plain JSON that includes:\n"
        "{\n"
        '    "level": <integer>,\n'
        '    "prompt": <the prompt you used (short string)>\n'
        "}\n"
        f"Message: {final_message.content}\n"
        "Only reply with the JSON object."
    )

    classification_result = await model.ainvoke(classification_prompt)
    classification_json = _extract_json_block(classification_result.content)
    severity_level = 1

    try:
        parsed = json.loads(classification_json)
        severity_level = int(parsed.get("level", severity_level))
    except Exception as e:
        print(f"Unable to parse severity level: {e}")

    severity_level = max(1, min(3, severity_level))

    return {
        "messages": [classification_result],
        "severity_level": severity_level,
        "classification_prompt": classification_prompt,
    }

async def add_to_triage_queue(state: AgentState):
    """
    Node to add the final state to a Redis Sorted Set (ZSET) for triage.
    """

    print("Adding item to triage queue.")
    final_message = state["messages"][-1]
    severity_level = state.get("severity_level") or 1
    prompt_used = state.get("classification_prompt") or ""
    score = time.time() - (severity_level * 1800)
    item = json.dumps(
        {
            "content": final_message.content,
            "type": final_message.type,
            "severity_level": severity_level,
            "prompt": prompt_used,
        }
    )
    print(f"Calculated score={score} for severity_level={severity_level}")
    await redis_client.zadd("triage_queue", {item: score})
    queue_snapshot = await redis_client.zrange("triage_queue", 0, -1, withscores=True)
    print("Current triage queue:", queue_snapshot)
    return {} # This node doesn't modify the state, just interacts with an external system

# Build linear graph: START -> agent1 -> middleware -> agent2 -> queue -> END
workflow = StateGraph(state_schema=AgentState)
workflow.add_node("agent1", agent1)
workflow.add_node("middleware", middleware)
workflow.add_node("agent2", agent2)
workflow.add_node("add_to_triage_queue", add_to_triage_queue)

workflow.add_edge(START, "agent1")
workflow.add_edge("agent1", "middleware")
workflow.add_conditional_edges("middleware", router)
workflow.add_edge("agent2", "add_to_triage_queue")
workflow.add_edge("add_to_triage_queue", END)

graph = workflow.compile()  # No checkpointer for stateless endpoint demo

class InvokeRequest(BaseModel):
    messages: List[Dict[str, Any]]
    config: Dict[str, Any] = {}

@app.post("/invoke")
async def invoke_workflow(req: InvokeRequest = Body(...)):
    """FastAPI endpoint to run the linear workflow."""
    result = await graph.ainvoke(
        {"messages": req.messages},
        req.config  # Optional: thread_id, etc. for persistence if checkpointer added
    )

    return {"result": result}

@app.get("/queue")
async def get_queue():
    with open("dummy-queue.json") as f:
        data = json.load(f)
    
    queue_summary = []
    for incident in data:
        queue_summary.append({
            "id": incident.get("id"),
            "incidentType": incident.get("incidentType"),
            "location": incident.get("location"),
            "time": incident.get("time")
        })
    return queue_summary




call_times = {}

@app.post("/call")
async def incoming_call(CallSid: str = Form(None)):
    response = VoiceResponse()
    call_times[CallSid] = datetime.utcnow().isoformat()
    response.say("911, please describe your emergency. Press the star key when you are finished.")
    response.record(finish_on_key="*", action=f"/recording-finished?CallSid={CallSid}", method="POST")
    return Response(content=str(response), media_type="application/xml")

@app.post("/recording-finished")
async def upload_recording(request: Request):
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
