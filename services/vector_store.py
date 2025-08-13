import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import uuid

class VectorStoreService:
    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "api_docs"):
        """Initialize ChromaDB vector store with sentence transformers"""
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model (faster and local)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"Loaded existing collection '{collection_name}' with {self.collection.count()} documents")
        except ValueError:
            # Collection doesn't exist, create it
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "API documentation chunks for RAG"}
            )
            print(f"Created new collection '{collection_name}'")
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using sentence transformers"""
        return self.embedding_model.encode(texts).tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query"""
        return self.embedding_model.encode([query])[0].tolist()
    
    def add_documents(self, documents: List, doc_id: str) -> bool:
        """Add document chunks to vector store"""
        try:
            texts = [doc.page_content for doc in documents]
            embeddings = self.embed_texts(texts)
            
            # Create unique IDs for each chunk
            chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(documents))]
            
            # Prepare metadata (ensure all values are JSON serializable)
            metadatas = []
            for doc in documents:
                metadata = doc.metadata.copy()
                # Convert datetime to string if present
                if 'uploaded_at' in metadata:
                    metadata['uploaded_at'] = str(metadata['uploaded_at'])
                # Remove embedding from metadata to avoid duplication
                if 'embedding' in metadata:
                    del metadata['embedding']
                metadatas.append(metadata)
            
            # Add to ChromaDB
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            
            print(f"Added {len(documents)} chunks to vector store for document {doc_id}")
            return True
            
        except Exception as e:
            print(f"Error adding documents to vector store: {e}")
            return False
    
    def search_similar(self, query: str, n_results: int = 5, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            # Build where clause for filtering by document if specified
            where_clause = None
            if doc_id:
                where_clause = {"doc_id": doc_id}
            
            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if results['distances'] else None
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching vector store: {e}")
            return []
    
    def search_by_metadata(self, metadata_filter: Dict[str, Any], n_results: int = 10) -> List[Dict[str, Any]]:
        """Search documents by metadata filters"""
        try:
            results = self.collection.get(
                where=metadata_filter,
                limit=n_results,
                include=['documents', 'metadatas']
            )
            
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        'id': results['ids'][i],
                        'content': results['documents'][i],
                        'metadata': results['metadatas'][i]
                    })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching by metadata: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks for a specific document"""
        try:
            # Find all chunks for this document
            results = self.collection.get(
                where={"doc_id": doc_id},
                include=['ids']
            )
            
            if results['ids']:
                # Delete all chunks
                self.collection.delete(ids=results['ids'])
                print(f"Deleted {len(results['ids'])} chunks for document {doc_id}")
                return True
            else:
                print(f"No chunks found for document {doc_id}")
                return True
                
        except Exception as e:
            print(f"Error deleting document from vector store: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection"""
        try:
            count = self.collection.count()
            
            # Get sample of documents to analyze
            sample = self.collection.get(limit=min(10, count), include=['metadatas'])
            
            # Count documents by type
            doc_types = {}
            doc_names = set()
            
            if sample['metadatas']:
                for metadata in sample['metadatas']:
                    doc_type = metadata.get('doc_type', 'unknown')
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                    
                    if 'doc_name' in metadata:
                        doc_names.add(metadata['doc_name'])
            
            return {
                'total_chunks': count,
                'unique_documents': len(doc_names),
                'document_types': doc_types,
                'collection_name': self.collection_name
            }
            
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {'error': str(e)}
    
    def reset_collection(self) -> bool:
        """Reset/clear the entire collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "API documentation chunks for RAG"}
            )
            print(f"Reset collection '{self.collection_name}'")
            return True
        except Exception as e:
            print(f"Error resetting collection: {e}")
            return False