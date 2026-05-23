import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/status")
def status():
    return {"status": "running on port 9897"}

if __name__ == "__main__":
    # FastAPI backend runs on port 9897 (internal)
    uvicorn.run(app, host="0.0.0.0", port=9897, reload=True)
