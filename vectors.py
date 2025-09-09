import os
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tidb_vector.integrations import TiDBVectorClient
from embedders import embedding_manager
from dotenv import load_dotenv
import logging
import uuid

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorManager:
    
    def __init__(self):
        """Initialize vector store manager"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        self.vector_client = None
        self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """Initialize TiDB Vector Client"""
        try:
            connection_string = os.getenv('TIDB_CONNECTION_URL')
            if not connection_string:
                raise ValueError("TIDB_CONNECTION_URL not found in environment variables")
            
            self.vector_client = TiDBVectorClient(
                table_name='embed',
                connection_string=connection_string,
                vector_dimension=embedding_manager.get_dimension(),
                drop_existing_table=False,  # Don't drop existing table
                distance_strategy="cosine"
            )
            logger.info("TiDB Vector Client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing TiDB Vector Client: {e}")
            raise
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks using RecursiveCharacterTextSplitter
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        try:
            chunks = self.text_splitter.split_text(text)
            logger.info(f"Text split into {len(chunks)} chunks")
            return chunks
        except Exception as e:
            logger.error(f"Error chunking text: {e}")
            return []
    
    def store_document_chunks(self, 
                            text_content: str, 
                            attachment_data: Dict[str, Any]) -> bool:
        """
        Process document: chunk text, generate embeddings, and store in vector store
        
        Args:
            text_content: Extracted text from document
            attachment_data: Metadata about the attachment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Chunk the text
            chunks = self.chunk_text(text_content)
            if not chunks:
                logger.warning("No chunks generated from text")
                return False
            
            # Generate embeddings for all chunks
            embeddings = embedding_manager.get_embeddings(chunks)
            
            # Prepare documents for vector store
            documents = []
            metadatas = []
            ids = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Create unique ID for each chunk
                chunk_id = f"{attachment_data['message_id']}_{i}"
                ids.append(chunk_id)
                
                # Document text is the chunk
                documents.append(chunk)
                
                # Metadata includes attachment info and chunk info
                metadata = {
                    "message_id": attachment_data['message_id'],
                    "channel_id": attachment_data['channel_id'],
                    "guild_id": attachment_data.get('guild_id'),
                    "author": attachment_data['author'],
                    "filename": attachment_data['filename'],
                    "attachment_id": attachment_data['attachment_id'],
                    "content_type": attachment_data.get('content_type'),
                    "timestamp": attachment_data['timestamp'].isoformat() if attachment_data.get('timestamp') else None,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                }
                metadatas.append(metadata)
            
            # Store in vector database
            self.vector_client.add_texts(
                texts=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully stored {len(chunks)} chunks for {attachment_data['filename']}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing document chunks: {e}")
            return False
    
    def search_similar_chunks(self, 
                            query: str, 
                            k: int = 5,
                            channel_id: Optional[str] = None,
                            author: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks
        
        Args:
            query: Search query
            k: Number of results to return
            channel_id: Filter by channel ID
            author: Filter by author
            
        Returns:
            List of similar chunks with metadata
        """
        try:
            # Build metadata filter
            metadata_filter = {}
            if channel_id:
                metadata_filter["channel_id"] = channel_id
            if author:
                metadata_filter["author"] = author
            
            # Search vector store
            results = self.vector_client.similarity_search_with_score(
                query=query,
                k=k,
                filter=metadata_filter if metadata_filter else None
            )
            
            # Format results
            formatted_results = []
            for doc, score in results:
                result = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score
                }
                formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} similar chunks for query: {query}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
    
    def delete_document_chunks(self, message_id: str) -> bool:
        """
        Delete all chunks for a specific message
        
        Args:
            message_id: Message ID to delete chunks for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # TiDBVectorClient doesn't have direct delete by metadata
            # We'll need to search first then delete by IDs
            results = self.vector_client.similarity_search(
                query="",  # Empty query to get all
                k=1000,  # Large number to get all chunks
                filter={"message_id": message_id}
            )
            
            if results:
                # Extract IDs and delete
                ids_to_delete = [f"{message_id}_{i}" for i in range(len(results))]
                self.vector_client.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(results)} chunks for message {message_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document chunks: {e}")
            return False

# Global instance
vector_manager = VectorManager()