from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.rag_service import RAGService
from services.vector_store import VectorStoreService

router = APIRouter(prefix="/api/query", tags=["query-generation"])

# Initialize services
vector_store = VectorStoreService()
rag_service = RAGService(vector_store)

class QueryRequest(BaseModel):
    query: str
    max_context: Optional[int] = 3
    include_explanation: Optional[bool] = True

class QueryResponse(BaseModel):
    success: bool
    user_query: str
    generated_query: Optional[Dict[str, Any]] = None
    context_used: Optional[int] = None
    relevant_documents: Optional[list] = None
    explanation: Optional[str] = None
    error: Optional[str] = None

@router.post("/generate", response_model=QueryResponse)
async def generate_api_query(request: QueryRequest):
    """
    Generate an API query from natural language description
    
    This endpoint uses RAG (Retrieval-Augmented Generation) to:
    1. Find relevant API documentation using vector similarity search
    2. Generate an executable API query based on the user's natural language request
    3. Provide explanations and confidence scores
    """
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # Generate API query using RAG
        result = rag_service.generate_api_query(
            user_query=request.query.strip(),
            max_results=request.max_context or 3
        )
        
        if not result['success']:
            return QueryResponse(
                success=False,
                user_query=request.query,
                error=result.get('error', 'Unknown error occurred')
            )
        
        # Generate explanation if requested
        explanation = None
        if request.include_explanation and result.get('generated_query'):
            explanation = rag_service.explain_query(result['generated_query'])
        
        return QueryResponse(
            success=True,
            user_query=request.query,
            generated_query=result['generated_query'],
            context_used=result.get('context_used'),
            relevant_documents=result.get('relevant_documents'),
            explanation=explanation
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate query: {str(e)}"
        )

@router.get("/examples")
async def get_query_examples():
    """Get example queries that work well with the system"""
    return {
        "examples": [
            {
                "category": "Weather APIs",
                "queries": [
                    "Get current weather for Tokyo",
                    "Show me the weather forecast for the next 7 days",
                    "Get temperature in Celsius for New York",
                    "What's the current humidity in London?"
                ]
            },
            {
                "category": "User Management",
                "queries": [
                    "Create a new user with name John Doe",
                    "Get all users from the system",
                    "Update user profile information",
                    "Delete a user by ID"
                ]
            },
            {
                "category": "General API Operations",
                "queries": [
                    "List all available endpoints",
                    "Search for items with filters",
                    "Get data with pagination",
                    "Submit a form with user data"
                ]
            }
        ],
        "tips": [
            "Be specific about what data you want to retrieve or modify",
            "Mention parameter values when possible (e.g., 'Tokyo' instead of 'a city')",
            "Include the action you want to perform (get, create, update, delete)",
            "Specify formats or units if relevant (e.g., 'in Celsius', 'as JSON')"
        ]
    }

@router.post("/explain")
async def explain_api_query(query_data: Dict[str, Any]):
    """
    Explain an existing API query structure
    
    Takes an API query object and provides a detailed explanation
    """
    
    try:
        explanation = rag_service.explain_query(query_data)
        
        return {
            "query": query_data,
            "explanation": explanation,
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to explain query: {str(e)}"
        )

@router.get("/health")
async def query_service_health():
    """Check the health of the query generation service"""
    
    try:
        # Check vector store connection
        stats = vector_store.get_collection_stats()
        
        return {
            "status": "healthy",
            "service": "query_generation",
            "vector_store_status": "connected",
            "available_documents": stats.get('total_chunks', 0),
            "rag_service": "operational"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "query_generation",
            "error": str(e)
        }