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

app = FastAPI()

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# Agent1 node: First agent processes input
def agent1(state: AgentState):
    msg = model.invoke(state["messages"])
    return {"messages": [msg]}

# Middleware node: Custom function between agents (e.g., log/transform state)
def middleware(state: AgentState):
    # Example: Log last message content and add middleware stamp
    last_msg = state["messages"][-1].content
    print(f"Middleware: Processed '{last_msg[:50]}...'")  # Logging example
    # Transform: Append middleware note
    stamped_msg = model.invoke([f"Add middleware note to: {last_msg}"])
    return {"messages": [stamped_msg]}

# Agent2 node: Second agent finalizes
def agent2(state: AgentState):
    msg = model.invoke(state["messages"])
    return {"messages": [msg]}

# Build linear graph: START -> agent1 -> middleware -> agent2 -> END
workflow = StateGraph(state_schema=AgentState)
workflow.add_node("agent1", agent1)
workflow.add_node("middleware", middleware)
workflow.add_node("agent2", agent2)
workflow.add_edge(START, "agent1")
workflow.add_edge("agent1", "middleware")
workflow.add_edge("middleware", "agent2")
workflow.add_edge("agent2", END)

graph = workflow.compile()  # No checkpointer for stateless endpoint demo

class InvokeRequest(BaseModel):
    messages: List[Dict[str, Any]]
    config: Dict[str, Any] = {}

@app.post("/invoke")
async def invoke_workflow(req: InvokeRequest = Body(...)):
    """FastAPI endpoint to run the linear workflow."""
    result = graph.invoke(
        {"messages": req.messages},
        req.config  # Optional: thread_id, etc. for persistence if checkpointer added
    )
    return {"result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
