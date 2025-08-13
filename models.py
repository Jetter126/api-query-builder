from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    OPENAPI = "openapi"
    SWAGGER = "swagger"
    POSTMAN = "postman"
    TEXT = "text"

class APIDocumentation(BaseModel):
    id: str
    name: str
    type: DocumentType
    content: Dict[Any, Any]
    uploaded_at: datetime
    file_size: int
    endpoints_count: Optional[int] = 0

class DocumentUploadResponse(BaseModel):
    id: str
    message: str
    type: DocumentType
    endpoints_parsed: int
    file_size: int