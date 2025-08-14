// API Query Builder React Application

const { useState, useEffect } = React;

// Configuration
const API_BASE_URL = 'http://localhost:8000';

// Utility Functions
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// API Service
class ApiService {
  static async request(endpoint, options = {}) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  static async generateQuery(query, includeExplanation = true) {
    return this.request('/api/query/generate', {
      method: 'POST',
      body: JSON.stringify({
        query,
        include_explanation: includeExplanation
      })
    });
  }

  static async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    return fetch(`${API_BASE_URL}/api/documentation/upload`, {
      method: 'POST',
      body: formData
    }).then(response => response.json());
  }

  static async uploadFromUrl(url, name = null) {
    return this.request('/api/documentation/upload-url', {
      method: 'POST',
      body: JSON.stringify({ url, name })
    });
  }

  static async getDocuments() {
    return this.request('/api/documentation/list');
  }

  static async getStats() {
    return this.request('/api/documentation/stats');
  }

  static async deleteDocument(docId) {
    return this.request(`/api/documentation/${docId}`, {
      method: 'DELETE'
    });
  }
}

// Components
const LoadingSpinner = ({ className = "" }) => (
  <div className={`loading-spinner ${className}`}></div>
);

const Alert = ({ type, message, details, onDismiss }) => (
  <div className={`alert alert-${type} fade-in`}>
    <i className={`fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle'} alert-icon`}></i>
    <div className="flex-1">
      <div className="font-medium">{message}</div>
      {details && <div className="text-sm mt-1">{details}</div>}
    </div>
    {onDismiss && (
      <button onClick={onDismiss} className="text-gray-400 hover:text-gray-600">
        <i className="fas fa-times"></i>
      </button>
    )}
  </div>
);

const QueryTab = ({ onQuerySubmit, loading, result }) => {
  const [query, setQuery] = useState('');

  const examples = [
    "Find pets by status",
    "Get pets by tags", 
    "Find pet by ID",
    "Create a new pet",
    "Delete a pet",
    "Get store inventory"
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onQuerySubmit(query.trim());
    }
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Natural Language Query</h2>
        </div>
        <div className="card-content">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., Find pets by status"
                  className="form-input"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !query.trim()}
                  className="btn btn-primary"
                >
                  {loading ? (
                    <>
                      <LoadingSpinner />
                      Generating...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-magic"></i>
                      Generate
                    </>
                  )}
                </button>
              </div>
            </div>
            
            <div className="mt-4">
              <p className="text-sm text-gray-600 mb-3">Try these examples:</p>
              <div className="query-examples">
                {examples.map((example, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => setQuery(example)}
                    className="example-tag"
                    disabled={loading}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </form>
        </div>
      </div>

      {result && (
        <div className="result-card fade-in">
          <div className={`result-header ${result.success ? '' : 'error'}`}>
            <h2 className="result-title">
              <i className={`fas ${result.success ? 'fa-check-circle' : 'fa-exclamation-triangle'}`}></i>
              {result.success ? 'Generated API Query' : 'Query Generation Failed'}
            </h2>
          </div>
          
          <div className="result-content">
            {result.success ? (
              <div>
                <div className="api-call">
                  <div className="text-lg mb-3">
                    <span className="method">{result.generated_query?.method}</span>{' '}
                    <span className="url">{result.generated_query?.url}</span>
                  </div>
                  
                  {result.generated_query?.headers && (
                    <div className="headers">
                      <strong>Headers:</strong>
                      <pre className="mt-1 text-sm">{JSON.stringify(result.generated_query.headers, null, 2)}</pre>
                    </div>
                  )}
                  
                  {result.generated_query?.body && (
                    <div className="body">
                      <strong>Body:</strong>
                      <pre className="mt-1 text-sm">{JSON.stringify(result.generated_query.body, null, 2)}</pre>
                    </div>
                  )}
                </div>

                <div className="metrics-grid">
                  <div className="metric-card">
                    <div className="metric-title">Confidence</div>
                    <div className="metric-value">
                      {Math.round((result.generated_query?.confidence || 0) * 100)}%
                    </div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-title">Context Used</div>
                    <div className="metric-value">{result.context_used || 0}</div>
                  </div>
                </div>

                {result.explanation && (
                  <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h4 className="font-medium text-yellow-800 mb-2">Explanation</h4>
                    <pre className="text-sm text-yellow-700 whitespace-pre-wrap">{result.explanation}</pre>
                  </div>
                )}

                {result.relevant_documents && result.relevant_documents.length > 0 && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium mb-3">Relevant Documents</h4>
                    <div className="space-y-2">
                      {result.relevant_documents.map((doc, index) => (
                        <div key={index} className="flex justify-between items-center text-sm">
                          <span className="font-medium">{doc.document}</span>
                          <span className="text-gray-500">
                            {doc.doc_type} (score: {doc.relevance_score?.toFixed(3)})
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Alert
                type="error"
                message="Failed to generate query"
                details={result.error}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const UploadTab = ({ onUploadSuccess, loading, uploadResult }) => {
  const [uploadMethod, setUploadMethod] = useState('file');
  const [urlInput, setUrlInput] = useState('');

  const handleFileUpload = async (e) => {
    e.preventDefault();
    const fileInput = e.target.querySelector('input[type="file"]');
    const file = fileInput.files[0];
    
    if (!file) return;

    try {
      const result = await ApiService.uploadFile(file);
      onUploadSuccess(result);
      fileInput.value = '';
    } catch (error) {
      onUploadSuccess({
        success: false,
        error: 'Failed to upload file: ' + error.message
      });
    }
  };

  const handleUrlUpload = async (e) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    try {
      const result = await ApiService.uploadFromUrl(urlInput.trim());
      onUploadSuccess(result);
      setUrlInput('');
    } catch (error) {
      onUploadSuccess({
        success: false,
        error: 'Failed to fetch from URL: ' + error.message
      });
    }
  };

  const exampleUrls = [
    'https://petstore.swagger.io/v2/swagger.json',
    'https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.yaml'
  ];

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Upload API Documentation</h2>
      </div>
      <div className="card-content">
        <div className="upload-methods">
          <button
            onClick={() => {
              setUploadMethod('file');
            }}
            className={`upload-method-btn ${uploadMethod === 'file' ? 'active' : ''}`}
          >
            <i className="fas fa-file-upload"></i>
            Upload File
          </button>
          <button
            onClick={() => {
              setUploadMethod('url');
            }}
            className={`upload-method-btn ${uploadMethod === 'url' ? 'active' : ''}`}
          >
            <i className="fas fa-link"></i>
            From URL
          </button>
        </div>

        {uploadMethod === 'file' && (
          <form onSubmit={handleFileUpload}>
            <div className="upload-area">
              <i className="fas fa-cloud-upload-alt upload-icon"></i>
              <h3 className="upload-title">Upload Documentation Files</h3>
              <p className="upload-description">
                Upload OpenAPI/Swagger JSON or YAML files, or Postman collections
              </p>
              <input
                type="file"
                accept=".json,.yaml,.yml"
                className="mb-4"
                disabled={loading}
                required
              />
              <div>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary"
                >
                  {loading ? (
                    <>
                      <LoadingSpinner />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-upload"></i>
                      Upload File
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        )}

        {uploadMethod === 'url' && (
          <div>
            <form onSubmit={handleUrlUpload}>
              <div className="upload-area">
                <i className="fas fa-link upload-icon"></i>
                <h3 className="upload-title">Fetch from URL</h3>
                <p className="upload-description">
                  Enter the URL to an OpenAPI/Swagger specification or Postman collection
                </p>
                
                <div className="form-group">
                  <input
                    type="url"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    placeholder="https://api.example.com/openapi.json"
                    className="form-input"
                    disabled={loading}
                    required
                  />
                </div>
                
                <button
                  type="submit"
                  disabled={loading || !urlInput.trim()}
                  className="btn btn-primary"
                >
                  {loading ? (
                    <>
                      <LoadingSpinner />
                      Fetching...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-download"></i>
                      Fetch Documentation
                    </>
                  )}
                </button>
              </div>
            </form>

            <div className="mt-4">
              <p className="text-sm text-gray-600 mb-3">Example API documentation URLs:</p>
              <div className="space-y-2">
                {exampleUrls.map((url, index) => (
                  <button
                    key={index}
                    onClick={() => setUrlInput(url)}
                    className="block text-sm text-blue-600 hover:text-blue-800 hover:underline transition-colors"
                    disabled={loading}
                  >
                    {url}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {uploadResult && (
          <Alert
            type={uploadResult.success ? 'success' : 'error'}
            message={uploadResult.success ? 'Upload Successful' : 'Upload Failed'}
            details={uploadResult.success 
              ? `${uploadResult.message} • Type: ${uploadResult.type} • Endpoints: ${uploadResult.endpoints_parsed} • Size: ${formatFileSize(uploadResult.file_size)}`
              : uploadResult.error
            }
          />
        )}
      </div>
    </div>
  );
};

const DocumentsTab = ({ documents, onDeleteDocument, loading }) => {
  if (documents.length === 0) {
    return (
      <div className="card">
        <div className="card-content">
          <div className="empty-state">
            <i className="fas fa-inbox empty-icon"></i>
            <h3 className="empty-title">No documents uploaded yet</h3>
            <p className="empty-description">Upload some API documentation to get started</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Uploaded Documents ({documents.length})</h2>
      </div>
      <div className="card-content">
        <div className="document-grid">
          {documents.map((doc) => (
            <div key={doc.id} className="document-card">
              <div className="document-header">
                <div>
                  <h3 className="document-title">{doc.name}</h3>
                  <div className="document-meta">
                    <span className="doc-type-badge">{doc.type}</span>
                    <span>
                      <i className="fas fa-code mr-1"></i>
                      {doc.endpoints_count} endpoints
                    </span>
                    <span>
                      <i className="fas fa-file mr-1"></i>
                      {formatFileSize(doc.file_size)}
                    </span>
                    <span>
                      <i className="fas fa-calendar mr-1"></i>
                      {formatDate(doc.uploaded_at)}
                    </span>
                  </div>
                </div>
                <button 
                  onClick={() => onDeleteDocument(doc.id)}
                  className="text-red-600 hover:text-red-800 transition-colors p-2"
                  disabled={loading}
                  title="Delete document"
                >
                  <i className="fas fa-trash"></i>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Main App Component
const App = () => {
  const [activeTab, setActiveTab] = useState('query');
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState(null);
  const [queryResult, setQueryResult] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  // Load initial data
  useEffect(() => {
    loadDocuments();
    loadStats();
  }, []);

  const loadDocuments = async () => {
    try {
      const data = await ApiService.getDocuments();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const loadStats = async () => {
    try {
      const data = await ApiService.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleQuerySubmit = async (query) => {
    setLoading(true);
    setQueryResult(null);
    
    try {
      const result = await ApiService.generateQuery(query, true);
      setQueryResult(result);
    } catch (error) {
      setQueryResult({
        success: false,
        error: error.message
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSuccess = async (result) => {
    setUploadResult(result);
    if (result.success) {
      await loadDocuments();
      await loadStats();
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    setLoading(true);
    try {
      await ApiService.deleteDocument(docId);
      await loadDocuments();
      await loadStats();
    } catch (error) {
      console.error('Failed to delete document:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    // Clear results when switching tabs
    if (tab !== 'query') setQueryResult(null);
    if (tab !== 'upload') setUploadResult(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="header">
        <div className="header-content">
          <h1>
            <div className="header-icon">
              <i className="fas fa-code"></i>
            </div>
            Intelligent API Query Builder
          </h1>
          <p>Convert natural language to API queries using RAG</p>
        </div>
      </header>

      {stats && (
        <div className="stats-bar">
          <div className="stats-content">
            <div className="stat-item">
              <i className="fas fa-database stat-icon"></i>
              <span>{stats.total_chunks} chunks</span>
            </div>
            <div className="stat-item">
              <i className="fas fa-file-alt stat-icon"></i>
              <span>{stats.unique_documents} documents</span>
            </div>
            <div className="stat-item">
              <i className="fas fa-cog stat-icon"></i>
              <span>Collection: {stats.collection_name}</span>
            </div>
          </div>
        </div>
      )}

      <main className="container">
        <nav className="tab-nav">
          <button
            onClick={() => handleTabChange('query')}
            className={`tab-button ${activeTab === 'query' ? 'active' : ''}`}
          >
            <i className="fas fa-search"></i>
            Generate Query
          </button>
          <button
            onClick={() => handleTabChange('upload')}
            className={`tab-button ${activeTab === 'upload' ? 'active' : ''}`}
          >
            <i className="fas fa-upload"></i>
            Upload Documentation
          </button>
          <button
            onClick={() => handleTabChange('documents')}
            className={`tab-button ${activeTab === 'documents' ? 'active' : ''}`}
          >
            <i className="fas fa-list"></i>
            Documents ({documents.length})
          </button>
        </nav>

        {activeTab === 'query' && (
          <QueryTab
            onQuerySubmit={handleQuerySubmit}
            loading={loading}
            result={queryResult}
          />
        )}

        {activeTab === 'upload' && (
          <UploadTab
            onUploadSuccess={handleUploadSuccess}
            loading={loading}
            uploadResult={uploadResult}
          />
        )}

        {activeTab === 'documents' && (
          <DocumentsTab
            documents={documents}
            onDeleteDocument={handleDeleteDocument}
            loading={loading}
          />
        )}
      </main>
    </div>
  );
};

// Render the app
ReactDOM.render(<App />, document.getElementById('root'));