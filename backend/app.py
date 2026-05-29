from fastapi import FastAPI
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Serve static files from frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def serve_index():
    index_file = os.path.join(frontend_path, "index.html")
    return FileResponse(index_file, media_type="text/html")

@app.get("/status")
def home():
    return {"status": "LAN CHAT V2 ONLINE"}
