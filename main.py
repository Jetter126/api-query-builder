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
try:
    # Get the current directory where main.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_path = os.path.join(current_dir, "frontend")
    
    if os.path.exists(frontend_path):
        css_path = os.path.join(frontend_path, "css")
        js_path = os.path.join(frontend_path, "js")
        
        # Mount CSS and JS directories if they exist
        if os.path.exists(css_path):
            app.mount("/css", StaticFiles(directory=css_path), name="css")
            print(f"Mounted CSS directory: {css_path}")
        
        if os.path.exists(js_path):
            app.mount("/js", StaticFiles(directory=js_path), name="js")
            print(f"Mounted JS directory: {js_path}")
        
        # Keep static mount for backwards compatibility
        app.mount("/static", StaticFiles(directory=frontend_path), name="static")
        print(f"Mounted static directory: {frontend_path}")
    else:
        print(f"Frontend directory not found: {frontend_path}")
        
except Exception as e:
    print(f"Error mounting static files: {e}")
    # Fallback: try relative paths
    if os.path.exists("frontend"):
        frontend_path = "frontend"
        if os.path.exists("frontend/css"):
            app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
        if os.path.exists("frontend/js"):
            app.mount("/js", StaticFiles(directory="frontend/js"), name="js")
        app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    """Serve the frontend UI"""
    from fastapi.responses import FileResponse
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_file = os.path.join(current_dir, "frontend", "index.html")
        if os.path.exists(frontend_file):
            return FileResponse(frontend_file)
    except:
        # Fallback to relative path
        if os.path.exists("frontend/index.html"):
            return FileResponse("frontend/index.html")
    
    return {"message": "Intelligent API Query Builder is running", "frontend": "not_found"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is operational"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)