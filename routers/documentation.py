from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict
import json
import yaml
import uuid
import os
from datetime import datetime

from models import DocumentUploadResponse, DocumentType, APIDocumentation
from services.document_processor import APIDocumentProcessor
from services.embedding_service import EmbeddingService

router = APIRouter(prefix="/api/documentation", tags=["documentation"])

in_memory_docs: Dict[str, APIDocumentation] = {}
in_memory_chunks: Dict[str, List] = {}  # Store processed chunks

# Initialize services
document_processor = APIDocumentProcessor()

# Initialize embedding service only if API key is available
embedding_service = None
if os.getenv("OPENAI_API_KEY"):
    try:
        embedding_service = EmbeddingService()
    except ValueError:
        print("Warning: OpenAI API key not found. Embedding functionality will be disabled.")

def parse_openapi_swagger(content: dict) -> int:
    """Parse OpenAPI/Swagger content and count endpoints"""
    paths = content.get("paths", {})
    endpoint_count = 0
    for path, methods in paths.items():
        endpoint_count += len([m for m in methods.keys() if m.lower() in ["get", "post", "put", "delete", "patch"]])
    return endpoint_count

def parse_postman_collection(content: dict) -> int:
    """Parse Postman collection and count requests"""
    def count_requests(item):
        if isinstance(item, dict):
            if "request" in item:
                return 1
            elif "item" in item:
                return sum(count_requests(subitem) for subitem in item["item"])
        return 0
    
    items = content.get("item", [])
    return sum(count_requests(item) for item in items)

def detect_document_type(content: dict, filename: str) -> DocumentType:
    """Detect the type of API documentation"""
    if "openapi" in content:
        return DocumentType.OPENAPI
    elif "swagger" in content or ("info" in content and "paths" in content):
        return DocumentType.SWAGGER
    elif "info" in content and ("item" in content or "collection" in filename.lower() or "postman" in filename.lower()):
        return DocumentType.POSTMAN
    else:
        return DocumentType.TEXT

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documentation(file: UploadFile = File(...)):
    """Upload and parse API documentation files"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        content = await file.read()
        file_size = len(content)
        
        # Parse JSON or YAML
        try:
            if file.filename.endswith(('.json', '.postman_collection.json')):
                parsed_content = json.loads(content.decode('utf-8'))
            elif file.filename.endswith(('.yaml', '.yml')):
                parsed_content = yaml.safe_load(content.decode('utf-8'))
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format. Please upload JSON or YAML files.")
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid file format: {str(e)}")
        
        # Detect document type
        doc_type = detect_document_type(parsed_content, file.filename)
        
        # Count endpoints based on type
        if doc_type in [DocumentType.OPENAPI, DocumentType.SWAGGER]:
            endpoints_count = parse_openapi_swagger(parsed_content)
        elif doc_type == DocumentType.POSTMAN:
            endpoints_count = parse_postman_collection(parsed_content)
        else:
            endpoints_count = 0
        
        # Create document record
        doc_id = str(uuid.uuid4())
        doc = APIDocumentation(
            id=doc_id,
            name=file.filename,
            type=doc_type,
            content=parsed_content,
            uploaded_at=datetime.now(),
            file_size=file_size,
            endpoints_count=endpoints_count
        )
        
        # Store in memory (temporary)
        in_memory_docs[doc_id] = doc
        
        # Process document into chunks using LangChain
        try:
            chunks = document_processor.process_document(doc)
            in_memory_chunks[doc_id] = chunks
            
            # Generate embeddings if service is available (optional for now)
            if embedding_service:
                try:
                    embeddings = embedding_service.embed_documents_sync(chunks)
                    # Store embeddings with chunks metadata
                    for i, chunk in enumerate(chunks):
                        chunk.metadata["embedding"] = embeddings[i]
                except Exception as e:
                    print(f"Warning: Failed to generate embeddings: {e}")
                    
        except Exception as e:
            print(f"Warning: Failed to process document into chunks: {e}")
            in_memory_chunks[doc_id] = []
        
        chunks_count = len(in_memory_chunks.get(doc_id, []))
        
        return DocumentUploadResponse(
            id=doc_id,
            message=f"Successfully uploaded, parsed, and processed {file.filename} into {chunks_count} chunks",
            type=doc_type,
            endpoints_parsed=endpoints_count,
            file_size=file_size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.get("/list")
async def list_documentation():
    """List all uploaded documentation"""
    docs = []
    for doc in in_memory_docs.values():
        docs.append({
            "id": doc.id,
            "name": doc.name,
            "type": doc.type,
            "uploaded_at": doc.uploaded_at,
            "endpoints_count": doc.endpoints_count,
            "file_size": doc.file_size
        })
    return {"documents": docs}

@router.get("/{doc_id}")
async def get_documentation(doc_id: str):
    """Get specific documentation by ID"""
    if doc_id not in in_memory_docs:
        raise HTTPException(status_code=404, detail="Documentation not found")
    
    doc = in_memory_docs[doc_id]
    return {
        "id": doc.id,
        "name": doc.name,
        "type": doc.type,
        "content": doc.content,
        "uploaded_at": doc.uploaded_at,
        "endpoints_count": doc.endpoints_count,
        "file_size": doc.file_size
    }

@router.get("/{doc_id}/chunks")
async def get_documentation_chunks(doc_id: str):
    """Get processed chunks for specific documentation"""
    if doc_id not in in_memory_docs:
        raise HTTPException(status_code=404, detail="Documentation not found")
    
    chunks = in_memory_chunks.get(doc_id, [])
    
    return {
        "doc_id": doc_id,
        "total_chunks": len(chunks),
        "chunks": [
            {
                "chunk_id": chunk.metadata.get("chunk_id", i),
                "content": chunk.page_content[:200] + "..." if len(chunk.page_content) > 200 else chunk.page_content,
                "metadata": {k: v for k, v in chunk.metadata.items() if k != "embedding"},
                "has_embedding": "embedding" in chunk.metadata
            }
            for i, chunk in enumerate(chunks)
        ]
    }

@router.delete("/{doc_id}")
async def delete_documentation(doc_id: str):
    """Delete documentation by ID"""
    if doc_id not in in_memory_docs:
        raise HTTPException(status_code=404, detail="Documentation not found")
    
    doc_name = in_memory_docs[doc_id].name
    del in_memory_docs[doc_id]
    
    # Also delete chunks
    if doc_id in in_memory_chunks:
        del in_memory_chunks[doc_id]
    
    return {"message": f"Successfully deleted {doc_name}"}