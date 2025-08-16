# Intelligent API Query Builder

A developer assistant that converts natural language requests into executable API queries using Retrieval-Augmented Generation (RAG).

## Features

- 📄 **Document Upload**: Upload OpenAPI/Swagger JSON/YAML files or Postman collections from files or URLs
- 🤖 **Natural Language Processing**: Convert plain English to API queries
- 🔍 **Vector Search**: Find relevant API documentation using semantic similarity
- 📊 **Smart Query Generation**: Generate complete API calls with proper parameters
- 🎯 **Confidence Scoring**: Get reliability scores for generated queries
- 🔧 **Modern UI**: Professional, responsive web interface with clean design
- 🌐 **URL Support**: Fetch API documentation directly from URLs
- 📱 **Mobile-Friendly**: Responsive design that works on all devices

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python3 main.py
```

or for Windows:
```bash
python main.py
```

### 3. Open the Web Interface
Navigate to `http://localhost:8000` in your browser

## Usage

### Upload Documentation

**From Files:**
1. Click on the "Upload Documentation" tab
2. Select "Upload File"
3. Choose an OpenAPI/Swagger JSON/YAML file or Postman collection
4. Click "Upload" to process the documentation

**From URLs:**
1. Click on the "Upload Documentation" tab
2. Select "From URL"
3. Enter the URL to an API specification (e.g., `https://petstore.swagger.io/v2/swagger.json`)
4. Click "Fetch Documentation" to download and process

### Generate API Queries
1. Go to the "Generate Query" tab
2. Enter a natural language request like:
   - "Find pets by status"
   - "Get pet by ID"
   - "Create a new pet"
   - "Delete a pet"
3. Click "Generate" to get your API query

### View Results
The generated query includes:
- HTTP method and complete URL with parameters
- Required headers and request body
- Confidence score and explanation
- Relevant documentation sources used

### Manage Documents
1. Go to the "Documents" tab
2. View all uploaded documentation with metadata
3. See endpoint counts, file sizes, and upload dates
4. Delete documents when no longer needed

## Example Usage

### Pet Store API Queries
Using the Swagger Petstore API (`https://petstore.swagger.io/v2/swagger.json`):

- **"Find pets by status"** → `GET https://petstore.swagger.io/v2/pet/findByStatus?status=available`
- **"Get pet by ID"** → `GET https://petstore.swagger.io/v2/pet/{petId}`
- **"Create a new pet"** → `POST https://petstore.swagger.io/v2/pet`
- **"Delete a pet"** → `DELETE https://petstore.swagger.io/v2/pet/{petId}`

### Generic API Patterns
- "Get current weather for Tokyo"
- "Create a new user with email"
- "Update user profile information"
- "List all available endpoints"

## API Endpoints

### Documentation Management
- `POST /api/documentation/upload` - Upload API documentation files
- `POST /api/documentation/upload-url` - Upload API documentation from URL
- `GET /api/documentation/list` - List uploaded documents
- `GET /api/documentation/stats` - Get vector store statistics
- `GET /api/documentation/search` - Search documentation
- `DELETE /api/documentation/{doc_id}` - Delete specific document

### Query Generation
- `POST /api/query/generate` - Generate API query from natural language
- `GET /api/query/examples` - Get example queries
- `GET /api/query/health` - Check service health

### System
- `GET /health` - Application health check
- `GET /` - Serve web interface

## Architecture

```
User Input → Vector Search → Context Retrieval → Query Generation → API Response
```

### Processing Pipeline

1. **Document Upload**: API documentation is uploaded via file or URL
2. **Document Processing**: Specifications are parsed and split into semantic chunks
3. **Vector Storage**: Text chunks are embedded using sentence transformers and stored in ChromaDB
4. **Query Processing**: User queries are converted to embeddings for similarity search
5. **Context Retrieval**: Most relevant documentation chunks are retrieved
6. **Query Generation**: RAG service analyzes context to generate appropriate API calls
7. **Response**: Complete API query with confidence scoring is returned

## Technology Stack

- **Backend**: FastAPI, Python
- **Frontend**: React (CDN), Tailwind CSS
- **Vector DB**: ChromaDB with sentence-transformers
- **Embeddings**: Local sentence transformers (all-MiniLM-L6-v2)
- **Text Processing**: Custom API-aware chunking

## Project Structure

```
├── main.py                      # FastAPI application entry point
├── requirements.txt             # Python dependencies
├── models.py                    # Pydantic data models
├── routers/
│   ├── documentation.py        # Document upload and management endpoints
│   └── query_generation.py     # RAG query generation endpoints
├── services/
│   ├── document_processor.py   # API documentation parsing
│   ├── vector_store.py         # ChromaDB integration and vector operations
│   ├── rag_service.py          # RAG pipeline and query generation
│   └── embedding_service.py    # OpenAI embeddings (optional)
├── frontend/
│   ├── index.html              # Main HTML file with external resources
│   ├── css/
│   │   └── styles.css          # Modern responsive styling
│   └── js/
│       └── app.js              # React application with components
└── chroma_db/                  # ChromaDB vector database (auto-created)
```

## Development

### Running the Application
```bash
# Development mode with auto-reload
python3 main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Testing API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Upload documentation from URL
curl -X POST "http://localhost:8000/api/documentation/upload-url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://petstore.swagger.io/v2/swagger.json"}'

# Generate query
curl -X POST "http://localhost:8000/api/query/generate" \
  -H "Content-Type: application/json" \
  -d '{"query": "Find pets by status", "include_explanation": true}'

# Get statistics
curl http://localhost:8000/api/documentation/stats
```

### File Structure Notes
- **Static Files**: CSS and JS files are served at `/css/` and `/js/` routes
- **Vector Database**: ChromaDB automatically creates and manages the `chroma_db/` directory
- **Document Storage**: Uploaded documents are processed and stored in the vector database
- **CORS Enabled**: Frontend can make requests from any origin during development

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Optional - enables OpenAI embeddings as backup to local embeddings

### Default Settings
- **Host**: 127.0.0.1 (localhost)
- **Port**: 8000
- **Vector DB**: ChromaDB with sentence transformers
- **Embedding Model**: all-MiniLM-L6-v2 (local, no API required)
- **Reload**: Enabled in development mode

## Supported Formats

### API Documentation
- **OpenAPI 3.x**: JSON and YAML formats
- **Swagger 2.x**: JSON and YAML formats  
- **Postman Collections**: JSON format

### Upload Methods
- **File Upload**: Drag and drop or file picker
- **URL Fetch**: Direct URL to API specification
- **Format Detection**: Automatic JSON/YAML detection

## Notes

- **Local Embeddings**: Uses sentence transformers by default - no API keys required
- **Persistent Storage**: Vector database persists between application restarts
- **CORS Support**: Enabled for cross-origin requests during development
- **Hot Reload**: Development server automatically reloads on code changes
- **Responsive Design**: UI adapts to desktop, tablet, and mobile screen sizes
- **Error Handling**: Comprehensive error handling with user-friendly messages