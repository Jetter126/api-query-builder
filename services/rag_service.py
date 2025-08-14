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
    
    def extract_endpoints_from_context(self, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract API endpoints from context chunks"""
        endpoints = []
        
        for chunk in context_chunks:
            content = chunk['content']
            lines = content.split('\n')
            
            current_endpoint = None
            for line in lines:
                line = line.strip()
                
                # Look for endpoint definitions
                if line.startswith('Endpoint: '):
                    endpoint_line = line.replace('Endpoint: ', '').strip()
                    
                    # Parse method and path (e.g., "GET /pet/findByStatus")
                    parts = endpoint_line.split(' ', 1)
                    if len(parts) == 2:
                        method, path = parts
                        current_endpoint = {
                            'method': method.upper(),
                            'path': path,
                            'summary': '',
                            'description': '',
                            'parameters': [],
                            'doc_name': chunk['metadata'].get('doc_name', ''),
                            'doc_type': chunk['metadata'].get('doc_type', '')
                        }
                        endpoints.append(current_endpoint)
                
                elif current_endpoint and line.startswith('Summary: '):
                    current_endpoint['summary'] = line.replace('Summary: ', '').strip()
                
                elif current_endpoint and line.startswith('Description: '):
                    current_endpoint['description'] = line.replace('Description: ', '').strip()
                
                elif current_endpoint and line.startswith('Parameters: '):
                    params_text = line.replace('Parameters: ', '').strip()
                    # Parse parameters (basic parsing for now)
                    if params_text:
                        current_endpoint['parameters'] = params_text.split(', ')
        
        return endpoints

    def find_best_matching_endpoint(self, user_query: str, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the best matching endpoint for a user query"""
        if not endpoints:
            return None
        
        user_query_lower = user_query.lower()
        best_match = None
        best_score = 0
        
        for endpoint in endpoints:
            score = 0
            
            # Check summary and description for keyword matches
            summary_lower = endpoint['summary'].lower()
            description_lower = endpoint['description'].lower()
            path_lower = endpoint['path'].lower()
            
            # Higher weight for exact keyword matches
            if 'find' in user_query_lower and 'find' in summary_lower:
                score += 10
            if 'pets' in user_query_lower and 'pet' in path_lower:
                score += 10
            if 'status' in user_query_lower and 'status' in summary_lower:
                score += 10
            if 'get' in user_query_lower and endpoint['method'] == 'GET':
                score += 5
            if 'create' in user_query_lower and endpoint['method'] == 'POST':
                score += 5
            if 'update' in user_query_lower and endpoint['method'] in ['PUT', 'PATCH']:
                score += 5
            if 'delete' in user_query_lower and endpoint['method'] == 'DELETE':
                score += 5
            
            # Additional scoring based on path segments
            query_words = user_query_lower.split()
            for word in query_words:
                if word in path_lower:
                    score += 3
                if word in summary_lower:
                    score += 2
                if word in description_lower:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = endpoint
        
        return best_match

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
        
        # Extract endpoints from context chunks
        endpoints = self.extract_endpoints_from_context(context_chunks)
        
        # Find the best matching endpoint
        best_endpoint = self.find_best_matching_endpoint(user_query, endpoints)
        
        if best_endpoint:
            # Determine base URL from doc_name or use a reasonable default
            doc_name = best_endpoint['doc_name']
            if 'petstore' in doc_name.lower():
                base_url = 'https://petstore.swagger.io/v2'
            elif 'github' in doc_name.lower():
                base_url = 'https://api.github.com'
            else:
                base_url = 'https://api.example.com'
            
            # Build the full URL
            full_url = base_url + best_endpoint['path']
            
            # Add query parameters if needed
            if 'status' in user_query.lower() and 'status' in best_endpoint['summary'].lower():
                full_url += '?status=available'
            elif 'tag' in user_query.lower() and 'tag' in best_endpoint['summary'].lower():
                full_url += '?tags=tag1'
            
            return {
                'method': best_endpoint['method'],
                'url': full_url,
                'headers': {'Accept': 'application/json'},
                'body': None if best_endpoint['method'] == 'GET' else {},
                'explanation': f"Found matching endpoint: {best_endpoint['method']} {best_endpoint['path']} - {best_endpoint['summary']}",
                'parameters_used': best_endpoint['parameters'],
                'confidence': 0.85,
                'mock_response': True,
                'matched_endpoint': best_endpoint
            }
        
        # Fallback: use the old heuristic method if no specific endpoint was found
        chunk = context_chunks[0]
        content = chunk['content'].lower()
        doc_name = chunk['metadata'].get('doc_name', 'api.json')
        
        # Simple heuristics based on content analysis (fallback method)
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
        
        # Step 1: Try multiple search strategies to find the best context
        try:
            # Strategy 1: Use the original query
            context_chunks = self.vector_store.search_similar(
                query=user_query,
                n_results=max_results
            )
            
            # Strategy 2: If the original query doesn't yield good results, try rephrased versions
            all_endpoints = self.extract_endpoints_from_context(context_chunks)
            best_match = self.find_best_matching_endpoint(user_query, all_endpoints)
            
            # If we didn't find a good match or it's not relevant, try alternative search terms
            # Check if the matched endpoint is actually relevant to the user query
            relevant_match = False
            if best_match:
                summary_lower = best_match.get('summary', '').lower()
                query_lower = user_query.lower()
                # Check if key terms align
                if ('status' in query_lower and 'status' in summary_lower) or \
                   ('tag' in query_lower and 'tag' in summary_lower):
                    relevant_match = True
            
            if not best_match or not relevant_match:
                # Create alternative search terms based on the user query
                alternative_queries = []
                
                # Try more specific variations
                if 'find' in user_query.lower() and 'pets' in user_query.lower():
                    if 'status' in user_query.lower():
                        alternative_queries.extend(['Finds Pets by status', 'pet findByStatus', 'GET /pet/findByStatus'])
                    if 'tag' in user_query.lower():
                        alternative_queries.extend(['Finds Pets by tags', 'pet findByTags', 'GET /pet/findByTags'])
                
                # Try the alternative searches
                for alt_query in alternative_queries:
                    alt_chunks = self.vector_store.search_similar(
                        query=alt_query,
                        n_results=max_results
                    )
                    alt_endpoints = self.extract_endpoints_from_context(alt_chunks)
                    alt_match = self.find_best_matching_endpoint(user_query, alt_endpoints)
                    
                    # Check if alternative match is more relevant than original
                    if alt_match:
                        alt_summary_lower = alt_match.get('summary', '').lower()
                        query_lower = user_query.lower()
                        
                        # Check for key term alignment (more flexible than exact substring)
                        alt_relevant = False
                        if ('status' in query_lower and 'status' in alt_summary_lower) or \
                           ('tag' in query_lower and 'tag' in alt_summary_lower):
                            alt_relevant = True
                        
                        if alt_relevant:
                            # Found a better match with alternative search
                            context_chunks = alt_chunks
                            break
            
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