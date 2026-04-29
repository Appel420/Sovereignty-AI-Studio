import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/status")
def status():
    return {"status": "running on port 9898"}

if __name__ == "__main__":
    # This forces FastAPI to always run on port 9898
    uvicorn.run(app, host="0.0.0.0", port=9898, reload=True)
