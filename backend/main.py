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
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List, Dict, Any

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
    is_duplicate: bool

# Agent1 node: First agent processes input
async def agent1(state: AgentState):
    msg = await model.ainvoke(state["messages"])
    return {"messages": [msg]}

# Middleware node: Custom function between agents (e.g., log/transform state)
async def middleware(state: AgentState):
    last_msg = state["messages"][-1].content
    
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
    json_str = extraction.content.strip()
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0].strip()
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0].strip()

    try:
        similar = find_similar_incidents(json_str)
        if similar:
            print(False)
            return {"is_duplicate": True}
    except Exception as e:
        print(f"Error checking similar incidents: {e}")
    
    return {"is_duplicate": False}

def router(state: AgentState):
    if state.get("is_duplicate"):
        return END
    return "agent2"

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
