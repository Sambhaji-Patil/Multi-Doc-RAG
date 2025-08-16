import os
import asyncio
from typing import List, Dict, Any

from config.config import *
from .preprocessing_modules.modular_preprocessor import ModularDocumentPreprocessor

class DocumentPreprocessor(ModularDocumentPreprocessor):
    """Backward compatibility alias for the modular document preprocessor."""
    pass

# CLI interface for preprocessing
async def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Document Preprocessing for RAG")
    parser.add_argument("--url", type=str, help="Single PDF URL to process")
    parser.add_argument("--urls-file", type=str, help="File containing PDF URLs (one per line)")
    parser.add_argument("--force", action="store_true", help="Force reprocessing even if already processed")
    parser.add_argument("--list", action="store_true", help="List all processed documents")
    parser.add_argument("--stats", action="store_true", help="Show collection statistics")
    
    args = parser.parse_args()
    
    preprocessor = DocumentPreprocessor()
    
    if args.list:
        docs = preprocessor.list_processed_documents()
        print(f"\n📚 Processed Documents ({len(docs)}):")
        for doc_id, info in docs.items():
            print(f"  • {doc_id}: {info['document_url'][:50]}... ({info.get('chunk_count', 'N/A')} chunks)")
    
    elif args.stats:
        stats = preprocessor.get_collection_stats()
        print(f"\n📊 Collection Statistics:")
        print(f"  • Total documents: {stats['total_documents']}")
        print(f"  • Total collections: {stats['total_collections']}")
        print(f"  • Total chunks: {stats['total_chunks']}")
    
    elif args.url:
        await preprocessor.process_document(args.url, args.force)
    
    elif args.urls_file:
        if not os.path.exists(args.urls_file):
            print(f"❌ File not found: {args.urls_file}")
            return
        
        with open(args.urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        if urls:
            await preprocessor.process_multiple_documents(urls, args.force)
        else:
            print("❌ No URLs found in file")
    
    else:
        print("❌ Please provide --url, --urls-file, --list, or --stats")
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
