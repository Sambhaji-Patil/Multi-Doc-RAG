# ShastraDocs Preprocessing Package

An advanced document preprocessing pipeline for RAG (Retrieval-Augmented Generation) systems. This modular package handles document ingestion, text extraction, chunking, embedding generation, and vector storage for multiple document formats.

## 🚀 Features

### Document Format Support
- **PDF**: Advanced text extraction with table handling and CID font support (Malayalam, complex scripts)
- **DOCX**: Complete Word document processing with tables and text boxes
- **PPTX**: PowerPoint extraction with OCR for images using OCR Space API
- **XLSX**: Excel spreadsheet processing with image OCR support
- **Images**: PNG, JPEG, JPG with table detection and OCR
- **Plain Text**: TXT and CSV file support
- **URLs**: Direct URL processing and Google Docs conversion

### Advanced Processing Capabilities
- **Smart Text Chunking**: Sentence-boundary aware chunking with configurable overlap
- **Embedding Generation**: Sentence transformer-based embeddings with batch processing
- **Vector Storage**: Qdrant integration for efficient similarity search
- **Table Extraction**: Automated table detection and formatting
- **OCR Integration**: OCR Space API for image text extraction
- **Metadata Management**: Comprehensive document metadata tracking
- **Parallel Processing**: Multi-threaded document processing
- **Caching**: Intelligent caching to avoid reprocessing

## 📁 Package Structure

```
preprocessing/
├── __init__.py                    # Package initialization
├── preprocessing.py               # Main entry point and CLI
└── preprocessing_modules/
    ├── __init__.py
    ├── modular_preprocessor.py    # Main orchestrator class
    ├── file_downloader.py         # Universal file downloading
    ├── pdf_extractor.py           # PDF text extraction
    ├── docx_extractor.py          # DOCX processing
    ├── pptx_extractor.py          # PowerPoint processing
    ├── xlsx_extractor.py          # Excel processing
    ├── image_extractor.py         # Image and table extraction
    ├── text_chunker.py            # Smart text chunking
    ├── embedding_manager.py       # Embedding generation
    ├── vector_storage.py          # Qdrant vector database
    └── metadata_manager.py        # Document metadata management
```

## 🛠️ Installation

### Dependencies
Note: these packages are already included in requirements.txt of the project
```bash
# Core dependencies
pip install aiohttp asyncio numpy pandas pathlib
pip install sentence-transformers qdrant-client
pip install pdfplumber pymupdf python-docx python-pptx openpyxl
pip install opencv-python pytesseract pillow lxml

# For image processing
pip install opencv-python pytesseract pillow

# For document parsing
pip install pdfplumber pymupdf python-docx python-pptx openpyxl lxml
```

### Environment Variables
Create a `.env` file with the following:
```env
# Required for PowerPoint OCR
OCR_SPACE_API_KEY=your_ocr_space_api_key

# Optional: Custom paths
OUTPUT_DIR=./vector_db
EMBEDDING_MODEL=Bge-large-en #or any model
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
BATCH_SIZE=32
```

## 🔧 Configuration

The package uses `config/config.py` for configuration:

```python
# Embedding configuration
EMBEDDING_MODEL = "Bge-large-en"  # Sentence transformer model
BATCH_SIZE = 32                       # Embedding batch size

# Chunking configuration
CHUNK_SIZE = 1600                     # Characters per chunk
CHUNK_OVERLAP = 500                   # Overlap between chunks

# Storage configuration
OUTPUT_DIR = "./vector_db"            # Vector database directory

# OCR configuration (for PPTX images)
OCR_SPACE_API_KEY = "your_api_key"    # OCR Space API key
```

## 📖 Usage

### Basic Usage

```python
from preprocessing import ModularDocumentPreprocessor

# Initialize preprocessor
preprocessor = ModularDocumentPreprocessor()

# Process a single document
doc_id = await preprocessor.process_document("https://example.com/document.pdf")

# Process multiple documents
urls = [
    "https://example.com/doc1.pdf",
    "https://example.com/doc2.docx",
    "https://example.com/presentation.pptx"
]
results = await preprocessor.process_multiple_documents(urls)

# Check processing status
info = preprocessor.get_document_info("https://example.com/document.pdf")
print(f"Document processed: {info}")
```

### Document Types and Return Values

```python
# Different document types return different formats
result = await preprocessor.process_document(url)

# Regular documents (PDF, DOCX, TXT)
if isinstance(result, str):
    doc_id = result  # Normal processing, returns document ID

# Special cases
elif isinstance(result, list):
    content, doc_type = result[0], result[1]
    
    if doc_type == 'oneshot':
        # Small documents processed as single chunk
        # Use content directly with LLM
        
    elif doc_type == 'tabular':
        # Excel/CSV with structured data
        # Use content for data analysis
        
    elif doc_type == 'image':
        # Image file - content is file path
        # Process with image_extractor
        
    elif doc_type == 'unsupported':
        # File format not supported
        print(f"Unsupported format: {content}")
```

### Advanced Usage

```python
# Force reprocessing
doc_id = await preprocessor.process_document(url, force_reprocess=True)

# Custom timeout for large files
doc_id = await preprocessor.process_document(url, timeout=600)  # 10 minutes

# Get system information
system_info = preprocessor.get_system_info()
print(f"Embedding model: {system_info['embedding_model']}")

# Get collection statistics
stats = preprocessor.get_collection_stats()
print(f"Total documents: {stats['total_documents']}")
print(f"Total chunks: {stats['total_chunks']}")

# List all processed documents
docs = preprocessor.list_processed_documents()
for doc_id, info in docs.items():
    print(f"{doc_id}: {info['document_url']} ({info['chunk_count']} chunks)")

# Cleanup document
success = preprocessor.cleanup_document(url)
```

### Image Processing

```python
from preprocessing_modules.image_extractor import extract_image

# Extract text and tables from images
text_content = extract_image("path/to/image.png")
print(text_content)

# Output format:
# ### Non-Table Text:
# Regular text content from the image
# 
# ### Table 1 (Markdown):
# | Column 1 | Column 2 | Column 3 |
# |----------|----------|----------|
# | Data 1   | Data 2   | Data 3   |
```

## 🎯 Command Line Interface

```bash
# Process a single document
python -m preprocessing --url "https://example.com/document.pdf"

# Process multiple documents from file
python -m preprocessing --urls-file urls.txt

# Force reprocessing
python -m preprocessing --url "https://example.com/document.pdf" --force

# List processed documents
python -m preprocessing --list

# Show collection statistics
python -m preprocessing --stats
```

### URLs File Format
```
https://example.com/doc1.pdf
https://example.com/doc2.docx
https://example.com/presentation.pptx
https://docs.google.com/document/d/abc123/edit?usp=sharing
```

## 🏗️ Architecture

### Modular Design
The package follows a modular architecture with clear separation of concerns:

1. **File Downloader**: Handles downloading from various sources with retry logic
2. **Text Extractors**: Specialized extractors for each document format
3. **Text Chunker**: Smart chunking with sentence boundary detection
4. **Embedding Manager**: Generates embeddings using sentence transformers
5. **Vector Storage**: Manages Qdrant vector database operations
6. **Metadata Manager**: Tracks document processing metadata

### Processing Pipeline
```
URL/File → Download → Extract Text → Chunk → Generate Embeddings → Store in Qdrant
                                     ↓
                               Save Metadata
```

### Document Processing Flow

1. **Download**: Securely download document to temporary location
2. **Format Detection**: Identify document type and select appropriate extractor
3. **Text Extraction**: Extract text content with format-specific handling
4. **Chunking**: Split text into overlapping chunks with smart boundaries
5. **Embedding**: Generate embeddings using sentence transformers
6. **Storage**: Store embeddings and metadata in Qdrant vector database
7. **Cleanup**: Remove temporary files and update registries

## 📊 Supported Formats

| Format | Extension | Features | Special Handling |
|--------|-----------|----------|------------------|
| PDF | .pdf | Text, tables, complex scripts | CID font mapping, parallel processing |
| Word | .docx | Text, tables, text boxes | XML parsing, gridSpan handling |
| PowerPoint | .pptx | Text, images, tables, notes | OCR Space API for images |
| Excel | .xlsx | Cells, images | OpenPyXL, OCR for embedded images |
| Images | .png, .jpg, .jpeg | Text, tables | OpenCV table detection, OCR |
| Text | .txt, .csv | Plain text | Direct processing |
| URLs | http/https | Web content | Google Docs conversion |

## 🔍 Advanced Features

### Table Processing
- Automatic table detection in PDFs and images
- GridSpan handling for complex table structures
- Markdown formatting for structured output
- Cell content extraction with proper spacing

### CID Font Support
- Advanced handling of Malayalam and complex scripts
- Character mapping resolution
- Proper spacing and conjunct handling
- Fallback extraction methods

### OCR Integration
- OCR Space API for PowerPoint images
- Tesseract OCR for Excel images
- Batch processing for efficiency
- Error handling and fallback options

### Caching System
- Document-level caching to avoid reprocessing
- Chunk caching for repeated operations
- Temporary file management
- Automatic cleanup on exit

## 🛡️ Error Handling

The package includes comprehensive error handling:

- **Network Issues**: Retry logic with exponential backoff
- **Corrupted Files**: Fallback extraction methods
- **Memory Issues**: Batch processing and streaming
- **Format Issues**: Multiple parser fallbacks
- **OCR Failures**: Graceful degradation with error messages

## 📈 Performance

### Optimization Features
- **Parallel Processing**: Multi-threaded document processing
- **Batch Operations**: Efficient embedding generation
- **Streaming**: Memory-efficient large file handling
- **Caching**: Avoid redundant processing
- **Connection Pooling**: Efficient HTTP operations

### Benchmarks
- **PDF Processing**: ~2-5 pages/second (depends on complexity)
- **Embedding Generation**: ~100-500 chunks/second (depends on model)
- **Vector Storage**: ~1000+ vectors/second insertion rate

## 🔧 Troubleshooting

### Common Issues

1. **OCR Space API Errors**
   ```python
   # Ensure API key is set
   export OCR_SPACE_API_KEY="your_key_here"
   ```

2. **Tesseract Not Found**
   ```bash
   # Install tesseract
   apt-get install tesseract-ocr
   # or
   brew install tesseract
   ```

3. **Memory Issues with Large Files**
   ```python
   # Reduce batch size in config
   BATCH_SIZE = 16
   ```

4. **Vector Database Issues**
   ```python
   # Check permissions on OUTPUT_DIR
   # Ensure sufficient disk space
   ```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging for troubleshooting
```
## 📄 License

This package is part of the ShastraDocs project. See the main project license for details.


*This preprocessing package is designed to handle the complex requirements of document processing in RAG systems, with a focus on reliability, performance, and format diversity.*