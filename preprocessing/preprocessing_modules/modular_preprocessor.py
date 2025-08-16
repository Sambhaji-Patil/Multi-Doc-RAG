"""
Modular Document Preprocessor

Main orchestrator class that uses all preprocessing modules to process documents.
"""

import os
import asyncio
from typing import List, Dict, Any
from pathlib import Path

from config.config import OUTPUT_DIR
from .pdf_extractor import TextExtractor
from .text_chunker import TextChunker
from .embedding_manager import EmbeddingManager
from .vector_storage import VectorStorage
from .metadata_manager import MetadataManager

from .file_downloader import FileDownloader
from .docx_extractor import extract_docx
from .pptx_extractor import extract_pptx
from .xlsx_extractor import extract_xlsx

from dotenv import load_dotenv
# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY_")

class ModularDocumentPreprocessor:
    """
    Modular document preprocessor that orchestrates the entire preprocessing pipeline.
    
    This class combines all preprocessing modules to provide a clean interface
    for document processing while maintaining separation of concerns.
    """
    
    def __init__(self):
        """Initialize the modular document preprocessor."""
        # Set up base database path
        self.base_db_path = Path(OUTPUT_DIR).resolve()
        self._ensure_base_directory()
        
        # Initialize all modules
        self.file_downloader = FileDownloader()
        self.text_extractor = TextExtractor()
        self.text_chunker = TextChunker()
        self.embedding_manager = EmbeddingManager()
        self.vector_storage = VectorStorage(self.base_db_path)
        self.metadata_manager = MetadataManager(self.base_db_path)
        self.cached_chunks = {}
        
        print("✅ Modular Document Preprocessor initialized successfully")
    
    def _ensure_base_directory(self):
        """Ensure the base directory exists."""
        if not self.base_db_path.exists():
            try:
                self.base_db_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ Created directory: {self.base_db_path}")
            except PermissionError:
                print(f"⚠️  Directory {self.base_db_path} should exist in production environment")
                if not self.base_db_path.exists():
                    raise RuntimeError(f"Required directory {self.base_db_path} does not exist and cannot be created")
    
    # Delegate metadata operations to metadata manager
    def generate_doc_id(self, document_url: str) -> str:
        """Generate a unique document ID from the URL."""
        return self.metadata_manager.generate_doc_id(document_url)
    
    def is_document_processed(self, document_url: str) -> bool:
        """Check if a document has already been processed."""
        return self.metadata_manager.is_document_processed(document_url)
    
    def get_document_info(self, document_url: str) -> Dict[str, Any]:
        """Get information about a processed document."""
        return self.metadata_manager.get_document_info(document_url)
    
    def list_processed_documents(self) -> Dict[str, Dict]:
        """List all processed documents."""
        return self.metadata_manager.list_processed_documents()
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about all collections."""
        return self.metadata_manager.get_collection_stats()
    
    async def process_document(self, document_url: str, force_reprocess: bool = False, timeout: int = 300) -> str | List:
        """
        Process a single document: download, extract, chunk, embed, and store.
        
        Args:
            document_url: URL of the document
            force_reprocess: If True, reprocess even if already processed
            timeout: Download timeout in seconds (default: 300s/5min)
            
        Returns:
            str: Document ID
        """
        doc_id = self.generate_doc_id(document_url)
        
        # Check if already processed
        if not force_reprocess and self.is_document_processed(document_url):
            print(f"✅ Document {doc_id} already processed, skipping...")
            return doc_id
        
        print(f"🚀 Processing document: {doc_id}")
        print(f"📄 URL: {document_url}")
        
        temp_file_path = None
        try:
            # Step 1: Download Document
            temp_file_path, ext = await self.file_downloader.download_file(document_url, timeout=timeout)
            
            if temp_file_path == 'not supported':
                return ['unsupported', ext]

            # Step 2: Extract text
            full_text = ""
            match ext:
                case 'pdf':
                    full_text = self.text_extractor.extract_text_from_pdf(temp_file_path)
                
                case 'docx':
                    full_text = extract_docx(temp_file_path)
                
                case 'pptx':
                    full_text = extract_pptx(temp_file_path)
                    return [full_text, 'oneshot']
                
                case 'url':
                    new_context = "URL for Context: " + temp_file_path
                    return [new_context, 'oneshot']
                
                case 'txt':
                    with open (temp_file_path, 'r') as f:
                        full_text = f.read()
                
                case 'xlsx':
                    full_text = extract_xlsx(temp_file_path)
                    return [full_text, 'tabular']
                
                case 'csv':
                    with open (temp_file_path, 'r') as f:
                        full_text = f.read()
                    return [full_text, 'tabular']

                case 'png':
                    # Don't clean up image files - they'll be cleaned up by the caller
                    return [temp_file_path, 'image', True]  # Third element indicates no cleanup needed
                
                case 'jpeg':
                    # Don't clean up image files - they'll be cleaned up by the caller
                    return [temp_file_path, 'image', True]  # Third element indicates no cleanup needed
                
                case 'jpg':
                    # Don't clean up image files - they'll be cleaned up by the caller
                    return [temp_file_path, 'image', True]  # Third element indicates no cleanup needed

            # Validate extracted text
            if not self.text_extractor.validate_extracted_text(full_text):
                raise Exception("No meaningful text extracted from PDF")
            
            # Step 3: Create chunks
            chunks = self.cached_chunks.get(document_url)
            if not chunks:
                chunks = self.text_chunker.chunk_text(full_text)
                self.cached_chunks[document_url] = chunks
            else:
                print("Using Cache: Skipped chunking")
            if len(chunks) < 5:
                    print(f"Only {len(chunks)} chunks formed, going for oneshot.")
                    return [full_text, 'oneshot']
            
            if not chunks:
                raise Exception("No chunks created from text")
            
            # Log chunk statistics
            chunk_stats = self.text_chunker.get_chunk_stats(chunks)
            print(f"📊 Chunk Statistics: {chunk_stats['total_chunks']} chunks, "
                  f"avg size: {chunk_stats['avg_chunk_size']:.0f} chars")
            
            # Step 4: Create embeddings
            embeddings = await self.embedding_manager.create_embeddings(chunks)
            
            # Validate embeddings
            if not self.embedding_manager.validate_embeddings(embeddings, len(chunks)):
                raise Exception("Invalid embeddings generated")
            
            # Step 5: Store in Qdrant
            await self.vector_storage.store_in_qdrant(chunks, embeddings, doc_id)
            
            # Step 6: Save metadata
            self.metadata_manager.save_document_metadata(chunks, doc_id, document_url)
            
            print(f"✅ Document {doc_id} processed successfully: {len(chunks)} chunks")
            return doc_id
            
        except Exception as e:
            print(f"❌ Error processing document {doc_id}: {str(e)}")
            raise
        # finally:
            # Clean up temporary file - but NOT for images since they need the file path
            # Images return a third element indicating no cleanup needed
            # if temp_file_path and ext not in ['png', 'jpeg', 'jpg']:
            #     self.file_downloader.cleanup_temp_file(temp_file_path)
    
    async def process_multiple_documents(self, document_urls: List[str], force_reprocess: bool = False) -> Dict[str, str]:
        """
        Process multiple documents concurrently.
        
        Args:
            document_urls: List of PDF URLs
            force_reprocess: If True, reprocess even if already processed
            
        Returns:
            Dict[str, str]: Mapping of URLs to document IDs
        """
        print(f"🚀 Processing {len(document_urls)} documents...")
        
        results = {}
        
        # Process documents concurrently (with limited concurrency)
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent downloads
        
        async def process_single(url):
            async with semaphore:
                try:
                    doc_id = await self.process_document(url, force_reprocess)
                    return url, doc_id
                except Exception as e:
                    print(f"❌ Failed to process {url}: {str(e)}")
                    return url, None
        
        tasks = [process_single(url) for url in document_urls]
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed_tasks:
            if isinstance(result, tuple):
                url, doc_id = result
                if doc_id:
                    results[url] = doc_id
        
        print(f"✅ Successfully processed {len(results)}/{len(document_urls)} documents")
        return results
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get information about the preprocessing system.
        
        Returns:
            Dict[str, Any]: System information
        """
        return {
            "base_db_path": str(self.base_db_path),
            "embedding_model": self.embedding_manager.get_model_info(),
            "text_chunker_config": {
                "chunk_size": self.text_chunker.chunk_size,
                "chunk_overlap": self.text_chunker.chunk_overlap
            },
            "processed_documents_registry": self.metadata_manager.get_registry_path(),
            "collection_stats": self.get_collection_stats()
        }
    
    def cleanup_document(self, document_url: str) -> bool:
        """
        Remove all data for a specific document.
        
        Args:
            document_url: URL of the document to clean up
            
        Returns:
            bool: True if successfully cleaned up
        """
        doc_id = self.generate_doc_id(document_url)
        
        try:
            # Remove vector storage
            vector_removed = self.vector_storage.delete_collection(doc_id)
            
            # Remove metadata
            metadata_removed = self.metadata_manager.remove_document_metadata(doc_id)
            
            success = vector_removed and metadata_removed
            if success:
                print(f"✅ Successfully cleaned up document {doc_id}")
            else:
                print(f"⚠️ Partial cleanup for document {doc_id}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error cleaning up document {doc_id}: {e}")
            return False
