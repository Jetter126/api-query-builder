from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

from routers import documentation, query_generation

app = FastAPI(
    title="Intelligent API Query Builder",
    description="A developer assistant that converts natural language to API queries using RAG",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documentation.router)
app.include_router(query_generation.router)

# Mount static files for frontend
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def root():
    """Serve the frontend UI"""
    from fastapi.responses import FileResponse
    frontend_file = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    else:
        return {"message": "Intelligent API Query Builder is running", "frontend": "not_found"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is operational"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)