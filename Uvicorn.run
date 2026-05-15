import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/status")
def status():
    return {"status": "running on port 8000"}

if __name__ == "__main__":
    # FastAPI backend runs on port 8000 (internal)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
