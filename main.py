from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

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

@app.get("/")
async def root():
    return {"message": "Intelligent API Query Builder is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is operational"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)