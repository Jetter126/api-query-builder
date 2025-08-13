from typing import List, Dict, Any
import json
from models import DocumentType, APIDocumentation

class Document:
    """Simple Document class to avoid import issues"""
    def __init__(self, page_content: str, metadata: Dict[str, Any]):
        self.page_content = page_content
        self.metadata = metadata

class SimpleTextSplitter:
    """Simple text splitter implementation"""
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to find a good breaking point
            break_point = end
            for separator in ['\n\n', '\n', '. ', ' ']:
                last_sep = text.rfind(separator, start, end)
                if last_sep > start:
                    break_point = last_sep + len(separator)
                    break
            
            chunks.append(text[start:break_point])
            start = break_point - self.chunk_overlap if break_point > self.chunk_overlap else break_point
        
        return [chunk.strip() for chunk in chunks if chunk.strip()]

class APIDocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = SimpleTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def extract_text_from_openapi(self, content: Dict[Any, Any]) -> str:
        """Extract meaningful text from OpenAPI/Swagger specification"""
        text_parts = []
        
        # API Info
        if "info" in content:
            info = content["info"]
            text_parts.append(f"API: {info.get('title', 'Unknown API')}")
            text_parts.append(f"Version: {info.get('version', 'Unknown')}")
            if "description" in info:
                text_parts.append(f"Description: {info['description']}")
        
        # Base URL/Servers
        if "servers" in content:
            servers = [server.get("url", "") for server in content["servers"]]
            text_parts.append(f"Base URLs: {', '.join(servers)}")
        elif "host" in content:
            scheme = content.get("schemes", ["https"])[0]
            base_path = content.get("basePath", "")
            text_parts.append(f"Base URL: {scheme}://{content['host']}{base_path}")
        
        # Paths/Endpoints
        if "paths" in content:
            for path, methods in content["paths"].items():
                for method, details in methods.items():
                    if method.lower() in ["get", "post", "put", "delete", "patch"]:
                        endpoint_text = f"\nEndpoint: {method.upper()} {path}"
                        
                        if "summary" in details:
                            endpoint_text += f"\nSummary: {details['summary']}"
                        
                        if "description" in details:
                            endpoint_text += f"\nDescription: {details['description']}"
                        
                        # Parameters
                        if "parameters" in details:
                            params = []
                            for param in details["parameters"]:
                                param_info = f"{param.get('name')} ({param.get('in', 'unknown')})"
                                if param.get('required', False):
                                    param_info += " - required"
                                if "description" in param:
                                    param_info += f": {param['description']}"
                                params.append(param_info)
                            endpoint_text += f"\nParameters: {', '.join(params)}"
                        
                        # Request body
                        if "requestBody" in details:
                            req_body = details["requestBody"]
                            if "description" in req_body:
                                endpoint_text += f"\nRequest Body: {req_body['description']}"
                        
                        # Responses
                        if "responses" in details:
                            responses = []
                            for code, response in details["responses"].items():
                                response_info = f"{code}"
                                if "description" in response:
                                    response_info += f": {response['description']}"
                                responses.append(response_info)
                            endpoint_text += f"\nResponses: {', '.join(responses)}"
                        
                        text_parts.append(endpoint_text)
        
        return "\n\n".join(text_parts)
    
    def extract_text_from_postman(self, content: Dict[Any, Any]) -> str:
        """Extract meaningful text from Postman collection"""
        text_parts = []
        
        # Collection info
        if "info" in content:
            info = content["info"]
            text_parts.append(f"Collection: {info.get('name', 'Unknown Collection')}")
            if "description" in info:
                text_parts.append(f"Description: {info['description']}")
        
        def process_items(items, prefix=""):
            for item in items:
                if isinstance(item, dict):
                    if "request" in item:
                        # This is a request
                        request = item["request"]
                        name = item.get("name", "Unnamed Request")
                        method = request.get("method", "GET")
                        
                        request_text = f"\n{prefix}Request: {method} {name}"
                        
                        # URL
                        if "url" in request:
                            url = request["url"]
                            if isinstance(url, dict):
                                raw_url = url.get("raw", "")
                                request_text += f"\nURL: {raw_url}"
                            else:
                                request_text += f"\nURL: {url}"
                        
                        # Headers
                        if "header" in request and request["header"]:
                            headers = [f"{h.get('key')}={h.get('value')}" for h in request["header"]]
                            request_text += f"\nHeaders: {', '.join(headers)}"
                        
                        # Body
                        if "body" in request and request["body"]:
                            body = request["body"]
                            if "raw" in body:
                                request_text += f"\nBody: {body['raw'][:200]}..."
                        
                        # Description
                        if "description" in item:
                            request_text += f"\nDescription: {item['description']}"
                        
                        text_parts.append(request_text)
                    
                    elif "item" in item:
                        # This is a folder
                        folder_name = item.get("name", "Unnamed Folder")
                        text_parts.append(f"\n{prefix}Folder: {folder_name}")
                        process_items(item["item"], prefix + "  ")
        
        if "item" in content:
            process_items(content["item"])
        
        return "\n\n".join(text_parts)
    
    def extract_text_from_document(self, doc: APIDocumentation) -> str:
        """Extract text content from API documentation based on type"""
        if doc.type in [DocumentType.OPENAPI, DocumentType.SWAGGER]:
            return self.extract_text_from_openapi(doc.content)
        elif doc.type == DocumentType.POSTMAN:
            return self.extract_text_from_postman(doc.content)
        else:
            # For generic text documents, convert to string
            return json.dumps(doc.content, indent=2)
    
    def create_chunks(self, doc: APIDocumentation) -> List[Document]:
        """Create text chunks from API documentation"""
        # Extract text content
        text_content = self.extract_text_from_document(doc)
        
        # Create metadata
        metadata = {
            "doc_id": doc.id,
            "doc_name": doc.name,
            "doc_type": doc.type.value,
            "uploaded_at": doc.uploaded_at.isoformat(),
            "endpoints_count": doc.endpoints_count
        }
        
        # Split text into chunks
        text_chunks = self.text_splitter.split_text(text_content)
        
        # Create Document objects with metadata
        documents = []
        for i, chunk in enumerate(text_chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_id"] = i
            chunk_metadata["total_chunks"] = len(text_chunks)
            
            documents.append(Document(
                page_content=chunk,
                metadata=chunk_metadata
            ))
        
        return documents
    
    def process_document(self, doc: APIDocumentation) -> List[Document]:
        """Main method to process API documentation into chunks"""
        return self.create_chunks(doc)