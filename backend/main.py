import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.post("/call_agent")
async def call_agent():
    return {"message": "Hello Call"}


@app.post("/triage_agent")
async def triage_agent():
    return {"message": "Hello triage"}


def run():
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()