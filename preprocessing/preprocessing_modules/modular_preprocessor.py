"""
Modular Document Preprocessor

Main orchestrator class that uses all preprocessing modules to process documents.
"""

import os
import asyncio
from typing import List, Dict, Any, Tuple
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
        
        # In-memory cache for special document types (images, tabular, etc.)
        self.special_content_cache: Dict[str, Any] = {}
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

    # New function to retrieve special content
    def get_special_document_details(self, doc_id: str) -> Any:
        """
        Retrieves the cached content for a special document type (image, tabular, oneshot).
        
        Args:
            doc_id: The unique ID of the document.
            
        Returns:
            The cached content (e.g., file path for images, full text for tabular/oneshot)
            or None if the doc_id is not in the cache or is a 'normal' vectorized document.
        """
        return self.special_content_cache.get(doc_id)

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
    
    async def process_document(self, document_url: str, force_reprocess: bool = False, timeout: int = 300, skip_length_check=False) -> Tuple[str, str]:
        """
        Process a single document. Returns its ID and type.
        
        Args:
            document_url: URL of the document.
            force_reprocess: If True, reprocess even if already processed.
            timeout: Download timeout in seconds.
            
        Returns:
            A tuple containing:
            - doc_id (str): The unique document ID.
            - doc_type (str): The type of document, one of ["normal", "image", "tabular", "oneshot", "error"].
        """
        doc_id = self.generate_doc_id(document_url)
        
        if not force_reprocess and self.is_document_processed(document_url):
            print(f"✅ Document {doc_id} already processed, skipping...")
            return doc_id, "normal"
        
        print(f"🚀 Processing document: {doc_id}")
        print(f"📄 URL: {document_url}")
        
        temp_file_path = None
        ext = None
        try:
            # Step 1: Download Document
            temp_file_path, ext = await self.file_downloader.fetch_file(document_url, timeout=timeout)
            
            if temp_file_path == 'not supported':
                return f"⚠️ Document type '{ext}' is not supported.", "error"

            # Step 2: Extract text or identify special type
            full_text = ""
            doc_type = "normal" # Assume normal processing unless specified otherwise

            match ext.lower():
                case 'pdf':
                    full_text = self.text_extractor.extract_text_from_pdf(temp_file_path)
                case 'docx':
                    full_text = extract_docx(temp_file_path)
                case 'pptx':
                    full_text = extract_pptx(temp_file_path)
                case 'txt':
                    with open(temp_file_path, 'r') as f:
                        full_text = f.read()
                
                # --- Handle Special Types ---
                case 'url':
                    content = "URL for Context: " + temp_file_path
                    self.special_content_cache[doc_id] = content
                    self.metadata_manager.save_document_metadata([content], doc_id, document_url)
                    return doc_id, "oneshot"
                
                case 'xlsx':
                    content = extract_xlsx(temp_file_path)
                    self.special_content_cache[doc_id] = content
                    self.metadata_manager.save_document_metadata([str(content)], doc_id, document_url)
                    return doc_id, "tabular"
                
                case 'csv':
                    with open(temp_file_path, 'r') as f:
                        content = f.read()
                    self.special_content_cache[doc_id] = content
                    self.metadata_manager.save_document_metadata([content], doc_id, document_url)
                    return doc_id, "tabular"

                case 'png' | 'jpeg' | 'jpg':
                    self.special_content_cache[doc_id] = temp_file_path
                    self.metadata_manager.save_document_metadata([temp_file_path], doc_id, document_url)
                    # Note: The caller is responsible for not deleting the temp file if it's an image.
                    return doc_id, "image"

            # --- Continue with normal text processing ---
            # Step 3: Create chunks
            import json
            with open(f"test/extracted/{temp_file_path.split('\\')[-1]}.json", 'w', encoding='utf-8') as f:
                if isinstance(full_text, str):
                    f.write(full_text)
                else:
                    json.dump(full_text, f)

            chunks = self.text_chunker.chunk_text(full_text, doc_id=doc_id)

            
            with open(f"test/chunks/{temp_file_path.split('\\')[-1]}.json", 'w', encoding='utf-8') as f:
                json.dump(chunks, f)
            
            # Handle short documents as a special 'oneshot' type
            if (not skip_length_check) and len(chunks) < 5:
                print(f"Only {len(chunks)} chunks formed, treating as 'oneshot'.")
                self.special_content_cache[doc_id] = full_text
                self.metadata_manager.save_document_metadata(chunks, doc_id, document_url)
                return doc_id, "oneshot"
            
            if not chunks:
                raise ValueError("No chunks created from text")
            
            print(f"Chunk Statistics: {len(chunks)} chunks.")
            
            # Step 4: Create embeddings and store
            embeddings = await self.embedding_manager.create_embeddings(chunks)
            if not self.embedding_manager.validate_embeddings(embeddings, len(chunks)):
                raise ValueError("Invalid embeddings generated")
            
            await self.vector_storage.store_in_qdrant(chunks, embeddings, doc_id)
            
            # Step 5: Save metadata
            self.metadata_manager.save_document_metadata(chunks, doc_id, document_url)
            
            print(f"✅ Document {doc_id} processed successfully as '{doc_type}'")
            return doc_id, doc_type
            
        except Exception as e:
            print(f"❌ Error processing document {doc_id}: {str(e)}")
            return doc_id, "error"

    
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
        semaphore = asyncio.Semaphore(3)
        
        async def process_single(url):
            async with semaphore:
                try:
                    doc_id, doc_type = await self.process_document(url, force_reprocess)
                    if doc_type != "error":
                        return url, doc_id
                    return url, None
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
        """Get information about the preprocessing system."""
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
        """Remove all data for a specific document."""
        doc_id = self.generate_doc_id(document_url)
        
        try:
            # Remove from vector storage
            vector_removed = self.vector_storage.delete_document(doc_id)
            
            # Remove from metadata
            metadata_removed = self.metadata_manager.remove_document_metadata(doc_id)
            
            # Remove from in-memory cache
            if doc_id in self.special_content_cache:
                del self.special_content_cache[doc_id]
            
            success = vector_removed and metadata_removed
            if success:
                print(f"✅ Successfully cleaned up document {doc_id}")
            else:
                print(f"⚠️ Partial cleanup for document {doc_id}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error cleaning up document {doc_id}: {e}")
            return False