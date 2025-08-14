# Intelligent API Query Builder

A developer assistant that converts natural language requests into executable API queries using Retrieval-Augmented Generation (RAG).

## Features

- 📄 **Document Upload**: Upload OpenAPI/Swagger JSON/YAML files or Postman collections
- 🤖 **Natural Language Processing**: Convert plain English to API queries
- 🔍 **Vector Search**: Find relevant API documentation using semantic similarity
- 📊 **Smart Query Generation**: Generate complete API calls with proper parameters
- 🎯 **Confidence Scoring**: Get reliability scores for generated queries
- 🔧 **Interactive UI**: Clean, modern web interface built with React

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python3 main.py
```

### 3. Open the Web Interface
Navigate to `http://localhost:8000` in your browser

## Usage

### Upload Documentation
1. Click on the "Upload Documentation" tab
2. Select an OpenAPI/Swagger JSON/YAML file or Postman collection
3. Click "Upload" to process the documentation

### Generate API Queries
1. Go to the "Generate Query" tab
2. Enter a natural language request like:
   - "Get current weather for Tokyo"
   - "Create a new user with email"
   - "List all available endpoints"
3. Click "Generate" to get your API query

### View Results
The generated query includes:
- HTTP method and complete URL
- Required headers and request body
- Confidence score and explanation
- Relevant documentation sources

## API Endpoints

### Documentation Management
- `POST /api/documentation/upload` - Upload API documentation
- `GET /api/documentation/list` - List uploaded documents
- `GET /api/documentation/stats` - Get vector store statistics
- `GET /api/documentation/search` - Search documentation

### Query Generation
- `POST /api/query/generate` - Generate API query from natural language
- `GET /api/query/examples` - Get example queries
- `GET /api/query/health` - Check service health

## Example Queries

### Weather APIs
- "Get current weather for Tokyo"
- "Show me the weather forecast for the next 7 days"
- "Get temperature in Celsius for New York"

### User Management
- "Create a new user with name John Doe"
- "Get all users from the system"
- "Update user profile information"

## Architecture

```
User Input → Vector Search → Context Retrieval → Query Generation → API Call
```

1. **Document Processing**: API docs are parsed and split into semantic chunks
2. **Vector Storage**: Chunks are embedded and stored in ChromaDB
3. **Retrieval**: User queries find relevant documentation via similarity search
4. **Generation**: RAG service combines context with query to generate API calls

## Technology Stack

- **Backend**: FastAPI, Python
- **Frontend**: React (CDN), Tailwind CSS
- **Vector DB**: ChromaDB with sentence-transformers
- **Embeddings**: Local sentence transformers (all-MiniLM-L6-v2)
- **Text Processing**: Custom API-aware chunking

## Development

### Project Structure
```
├── main.py                 # FastAPI application
├── routers/
│   ├── documentation.py   # Document upload/management
│   └── query_generation.py # RAG query generation  
├── services/
│   ├── document_processor.py # API doc parsing
│   ├── vector_store.py     # ChromaDB integration
│   └── rag_service.py      # RAG pipeline
├── models.py              # Pydantic models
├── frontend/
│   └── index.html         # React UI
└── requirements.txt       # Dependencies
```

### Run Tests
```bash
# Start server
python3 main.py

# Test API endpoints
curl http://localhost:8000/api/query/health
curl http://localhost:8000/api/documentation/stats
```

## Notes

- Currently uses mock query generation logic
- Ready for LLM integration (OpenAI, Claude, etc.)
- Vector database persists in `./chroma_db/`
- Supports CORS for frontend development

## Next Steps (Phase 2)

- Real LLM integration for better query generation
- API key management and authentication
- Advanced prompt engineering
- Query execution and testing
- Multiple documentation support