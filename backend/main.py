# app.py - Complete FastAPI + LangGraph app
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import TypedDict, Annotated
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


app = FastAPI()

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# Agent1 node: First agent processes input
async def agent1(state: AgentState):
    msg = await model.ainvoke(state["messages"])
    return {"messages": [msg]}

# Middleware node: Custom function between agents (e.g., log/transform state)
async def middleware(state: AgentState):
    # Example: Log last message content and add middleware stamp
    last_msg = state["messages"][-1].content
    print(f"Middleware: Processed '{last_msg[:50]}...'")  # Logging example
    # Transform: Append middleware note
    stamped_msg = await model.ainvoke([f"Add middleware note to: {last_msg}"])
    return {"messages": [stamped_msg]}

# Agent2 node: Second agent finalizes
async def agent2(state: AgentState):
    msg = await model.ainvoke(state["messages"])
    return {"messages": [msg]}

async def add_to_triage_queue(state: AgentState):
    """
    Node to add the final state to a Redis Sorted Set (ZSET) for triage.
    """
    print("Adding item to triage queue.")
    # The final message from the graph is the one we want to queue
    final_message = state["messages"][-1]
    # Use a timestamp as the score for ordering
    score = time.time()
    # Serialize the message content for storage in Redis
    item = json.dumps({"content": final_message.content, "type": final_message.type})
    await redis_client.zadd("triage_queue", {item: score})
    return {} # This node doesn't modify the state, just interacts with an external system

# Build linear graph: START -> agent1 -> middleware -> agent2 -> queue -> END
workflow = StateGraph(state_schema=AgentState)
workflow.add_node("agent1", agent1)
workflow.add_node("middleware", middleware)
workflow.add_node("agent2", agent2)
workflow.add_node("add_to_triage_queue", add_to_triage_queue)

workflow.add_edge(START, "agent1")
workflow.add_edge("agent1", "middleware")
workflow.add_edge("middleware", "agent2")
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

call_times = {}

@app.post("/call")
async def incoming_call(CallSid: str = Form(None)):
    # form = await request.form()
    # print(form)
    # CallSid = form.get("CallSid")
    # print(CallSid)
    # if CallSid:
    #     call_times[CallSid] = datetime.utcnow().isoformat()
    # base = str(request.base_url).rstrip("/")
    # action_url = f"{base}/recording-finished?CallSid={CallSid}"
    response = VoiceResponse()
    response.say("911, please describe your emergency. Press the pound button when you are finished.")
    response.record(finish_on_key="*", action="/recording-finished", method="POST")
    response.say("Thank you. Please stay on the line for further instructions.")
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
    return Response("<Response></Response>", media_type="application/xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
