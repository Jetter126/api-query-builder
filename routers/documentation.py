from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict
import json
import yaml
import uuid
import os
import requests
from urllib.parse import urlparse
from datetime import datetime

from models import DocumentUploadResponse, DocumentType, APIDocumentation, URLUploadRequest
from services.document_processor import APIDocumentProcessor
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStoreService

router = APIRouter(prefix="/api/documentation", tags=["documentation"])

in_memory_docs: Dict[str, APIDocumentation] = {}
in_memory_chunks: Dict[str, List] = {}  # Store processed chunks

# Initialize services
document_processor = APIDocumentProcessor()
vector_store = VectorStoreService()

# Initialize embedding service only if API key is available (kept for backwards compatibility)
embedding_service = None
if os.getenv("OPENAI_API_KEY"):
    try:
        embedding_service = EmbeddingService()
    except ValueError:
        print("Warning: OpenAI API key not found. OpenAI embedding functionality will be disabled.")
        print("Using sentence transformers for local embeddings via vector store.")

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

def fetch_url_content(url: str) -> tuple[str, str]:
    """
    Fetch content from URL and determine content type
    Returns: (content_string, detected_format)
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")
        
        # Set headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, application/yaml, text/yaml, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Fetch content with timeout
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        content_type = response.headers.get('content-type', '').lower()
        
        # Determine format based on content-type header or URL extension
        if 'json' in content_type or url.endswith('.json'):
            detected_format = 'json'
        elif 'yaml' in content_type or url.endswith(('.yaml', '.yml')):
            detected_format = 'yaml'
        else:
            # Try to detect based on content
            content_stripped = content.strip()
            if content_stripped.startswith(('{', '[')):
                detected_format = 'json'
            elif content_stripped.startswith(('openapi:', 'swagger:', 'info:')):
                detected_format = 'yaml'
            else:
                # Default to JSON and let parser handle it
                detected_format = 'json'
        
        return content, detected_format
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=408, detail="Request timeout - URL took too long to respond")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Connection error - could not connect to URL")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {e.response.reason}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching URL: {str(e)}")

def extract_filename_from_url(url: str, custom_name: str = None) -> str:
    """Extract a reasonable filename from URL"""
    if custom_name:
        return custom_name if custom_name.endswith(('.json', '.yaml', '.yml')) else f"{custom_name}.json"
    
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Common API documentation URL patterns
    if '/openapi.json' in path or '/openapi.yaml' in path:
        return f"openapi_{parsed_url.netloc.replace('.', '_')}.json"
    elif '/swagger.json' in path or '/swagger.yaml' in path:
        return f"swagger_{parsed_url.netloc.replace('.', '_')}.json"
    elif path.endswith(('.json', '.yaml', '.yml')):
        return os.path.basename(path)
    else:
        # Generate filename from domain
        domain = parsed_url.netloc.replace('.', '_').replace(':', '_')
        return f"api_docs_{domain}.json"

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
            
            # Store chunks in vector database
            vector_store_success = vector_store.add_documents(chunks, doc_id)
            if not vector_store_success:
                print(f"Warning: Failed to store document {doc_id} in vector database")
            
            # Generate embeddings if OpenAI service is available (optional backup)
            if embedding_service:
                try:
                    embeddings = embedding_service.embed_documents_sync(chunks)
                    # Store embeddings with chunks metadata
                    for i, chunk in enumerate(chunks):
                        chunk.metadata["embedding"] = embeddings[i]
                except Exception as e:
                    print(f"Warning: Failed to generate OpenAI embeddings: {e}")
                    
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

@router.post("/upload-url", response_model=DocumentUploadResponse)
async def upload_documentation_from_url(request: URLUploadRequest):
    """Upload and parse API documentation from URL"""
    
    try:
        # Fetch content from URL
        content_str, detected_format = fetch_url_content(request.url)
        file_size = len(content_str.encode('utf-8'))
        
        # Generate filename
        filename = extract_filename_from_url(request.url, request.name)
        
        # Parse content based on detected format
        try:
            if detected_format == 'json':
                parsed_content = json.loads(content_str)
            elif detected_format == 'yaml':
                parsed_content = yaml.safe_load(content_str)
            else:
                raise HTTPException(status_code=400, detail="Unsupported content format")
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid {detected_format} format: {str(e)}")
        
        # Detect document type
        doc_type = detect_document_type(parsed_content, filename)
        
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
            name=filename,
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
            
            # Store chunks in vector database
            vector_store_success = vector_store.add_documents(chunks, doc_id)
            if not vector_store_success:
                print(f"Warning: Failed to store document {doc_id} in vector database")
            
            # Generate embeddings if OpenAI service is available (optional backup)
            if embedding_service:
                try:
                    embeddings = embedding_service.embed_documents_sync(chunks)
                    # Store embeddings with chunks metadata
                    for i, chunk in enumerate(chunks):
                        chunk.metadata["embedding"] = embeddings[i]
                except Exception as e:
                    print(f"Warning: Failed to generate OpenAI embeddings: {e}")
                    
        except Exception as e:
            print(f"Warning: Failed to process document into chunks: {e}")
            in_memory_chunks[doc_id] = []
        
        chunks_count = len(in_memory_chunks.get(doc_id, []))
        
        return DocumentUploadResponse(
            id=doc_id,
            message=f"Successfully fetched, parsed, and processed {filename} from URL into {chunks_count} chunks",
            type=doc_type,
            endpoints_parsed=endpoints_count,
            file_size=file_size
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing URL: {str(e)}")

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

@router.get("/search")
async def search_documentation(query: str, limit: int = 5, doc_id: str = None):
    """Search documentation using vector similarity"""
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        results = vector_store.search_similar(query, n_results=limit, doc_id=doc_id)
        
        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/stats")
async def get_vector_store_stats():
    """Get vector store statistics"""
    try:
        stats = vector_store.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

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

@router.delete("/{doc_id}")
async def delete_documentation(doc_id: str):
    """Delete documentation by ID"""
    if doc_id not in in_memory_docs:
        raise HTTPException(status_code=404, detail="Documentation not found")
    
    doc_name = in_memory_docs[doc_id].name
    
    # Delete from vector store
    vector_store.delete_document(doc_id)
    
    # Delete from memory
    del in_memory_docs[doc_id]
    if doc_id in in_memory_chunks:
        del in_memory_chunks[doc_id]
    
    return {"message": f"Successfully deleted {doc_name}"}