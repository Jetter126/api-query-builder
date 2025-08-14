from typing import List, Dict, Any, Optional
import json
import re
from services.vector_store import VectorStoreService

class RAGService:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
    
    def create_api_query_prompt(self, user_query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Create a prompt template for API query generation"""
        
        # Extract context information
        context_text = "\n\n".join([
            f"Document: {chunk['metadata'].get('doc_name', 'Unknown')}\n"
            f"Content: {chunk['content']}"
            for chunk in context_chunks
        ])
        
        prompt = f"""You are an expert API assistant that converts natural language requests into executable API queries.

Based on the API documentation provided below, generate a specific API request for the user's query.

API DOCUMENTATION:
{context_text}

USER REQUEST: "{user_query}"

Please generate a JSON response with the following structure:
{{
  "method": "GET|POST|PUT|DELETE|PATCH",
  "url": "complete URL with parameters",
  "headers": {{"header_name": "header_value"}},
  "body": {{"key": "value"}},
  "explanation": "Brief explanation of what this API call does",
  "parameters_used": ["list", "of", "parameters"],
  "confidence": 0.85
}}

Requirements:
1. Use actual endpoint URLs from the documentation
2. Fill in realistic parameter values based on the user's request
3. Include appropriate headers if specified in the documentation
4. Provide a confidence score (0-1) based on how well the request matches available APIs
5. If no exact match exists, suggest the closest available API

RESPONSE (JSON only):"""
        
        return prompt
    
    def parse_generated_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate the generated API query response"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['method', 'url', 'explanation']
                if all(field in parsed for field in required_fields):
                    return {
                        'success': True,
                        'query': parsed,
                        'raw_response': response_text
                    }
            
            return {
                'success': False,
                'error': 'Could not parse valid JSON response',
                'raw_response': response_text
            }
            
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'JSON parsing error: {str(e)}',
                'raw_response': response_text
            }
    
    def generate_mock_response(self, user_query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a mock API query response when no LLM is available"""
        
        if not context_chunks:
            return {
                'method': 'GET',
                'url': 'https://api.example.com/search',
                'headers': {},
                'body': None,
                'explanation': f'No relevant API documentation found for: {user_query}',
                'parameters_used': [],
                'confidence': 0.1,
                'mock_response': True
            }
        
        # Analyze the first chunk to generate a reasonable mock response
        chunk = context_chunks[0]
        content = chunk['content'].lower()
        doc_name = chunk['metadata'].get('doc_name', 'api.json')
        
        # Simple heuristics based on content analysis
        if 'weather' in content and 'current' in user_query.lower():
            return {
                'method': 'GET',
                'url': 'https://api.weather.com/v1/current?city=Tokyo&units=metric',
                'headers': {'Accept': 'application/json'},
                'body': None,
                'explanation': f'Get current weather data based on API documentation in {doc_name}',
                'parameters_used': ['city', 'units'],
                'confidence': 0.8,
                'mock_response': True
            }
        elif 'weather' in content and 'forecast' in user_query.lower():
            return {
                'method': 'GET',
                'url': 'https://api.weather.com/v1/forecast?city=Tokyo&days=7',
                'headers': {'Accept': 'application/json'},
                'body': None,
                'explanation': f'Get weather forecast based on API documentation in {doc_name}',
                'parameters_used': ['city', 'days'],
                'confidence': 0.8,
                'mock_response': True
            }
        elif 'user' in content and ('get' in user_query.lower() or 'list' in user_query.lower()):
            return {
                'method': 'GET',
                'url': 'https://api.example.com/users',
                'headers': {'Authorization': 'Bearer YOUR_TOKEN'},
                'body': None,
                'explanation': f'Get users based on API documentation in {doc_name}',
                'parameters_used': [],
                'confidence': 0.7,
                'mock_response': True
            }
        elif 'user' in content and 'create' in user_query.lower():
            return {
                'method': 'POST',
                'url': 'https://api.example.com/users',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer YOUR_TOKEN'
                },
                'body': {
                    'name': 'John Doe',
                    'email': 'john@example.com'
                },
                'explanation': f'Create a new user based on API documentation in {doc_name}',
                'parameters_used': ['name', 'email'],
                'confidence': 0.7,
                'mock_response': True
            }
        else:
            # Generic response based on content
            return {
                'method': 'GET',
                'url': 'https://api.example.com/query',
                'headers': {'Accept': 'application/json'},
                'body': None,
                'explanation': f'API query generated from documentation in {doc_name}',
                'parameters_used': [],
                'confidence': 0.5,
                'mock_response': True
            }
    
    def generate_api_query(self, user_query: str, max_results: int = 3) -> Dict[str, Any]:
        """
        Main method to generate API queries from natural language
        
        Args:
            user_query: Natural language description of what the user wants
            max_results: Maximum number of relevant chunks to retrieve
        
        Returns:
            Dictionary with generated API query and metadata
        """
        
        # Step 1: Retrieve relevant context using vector search
        try:
            context_chunks = self.vector_store.search_similar(
                query=user_query,
                n_results=max_results
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to retrieve context: {str(e)}',
                'user_query': user_query
            }
        
        # Step 2: Generate API query (using mock for now, can be replaced with real LLM)
        try:
            generated_query = self.generate_mock_response(user_query, context_chunks)
            
            return {
                'success': True,
                'user_query': user_query,
                'generated_query': generated_query,
                'context_used': len(context_chunks),
                'relevant_documents': [
                    {
                        'document': chunk['metadata'].get('doc_name'),
                        'doc_type': chunk['metadata'].get('doc_type'),
                        'relevance_score': chunk.get('distance', 0)
                    }
                    for chunk in context_chunks
                ],
                'retrieval_method': 'vector_similarity'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to generate query: {str(e)}',
                'user_query': user_query,
                'context_used': len(context_chunks) if context_chunks else 0
            }
    
    def explain_query(self, generated_query: Dict[str, Any]) -> str:
        """Generate a human-readable explanation of the API query"""
        
        if not generated_query:
            return "No query was generated."
        
        method = generated_query.get('method', 'UNKNOWN')
        url = generated_query.get('url', 'unknown URL')
        explanation = generated_query.get('explanation', 'No explanation provided')
        confidence = generated_query.get('confidence', 0)
        
        explanation_text = f"""
API Query Explanation:
- Method: {method}
- URL: {url}
- Purpose: {explanation}
- Confidence: {confidence:.2f}/1.00
"""
        
        if generated_query.get('headers'):
            explanation_text += f"- Headers: {json.dumps(generated_query['headers'], indent=2)}\n"
        
        if generated_query.get('body'):
            explanation_text += f"- Body: {json.dumps(generated_query['body'], indent=2)}\n"
        
        if generated_query.get('parameters_used'):
            explanation_text += f"- Parameters Used: {', '.join(generated_query['parameters_used'])}\n"
        
        if generated_query.get('mock_response'):
            explanation_text += "\nNote: This is a mock response generated without an LLM. In production, this would use GPT-4 or similar for more accurate results.\n"
        
        return explanation_text.strip()