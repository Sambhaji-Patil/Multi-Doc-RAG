#!/usr/bin/env python3
"""
HuggingFace Spaces entry point for Advanced RAG API.
This file is the main entry point that HuggingFace Spaces will execute.
"""

# Import the FastAPI app from api.py
from api.api import app

# HuggingFace Spaces will automatically run this app
if __name__ == "__main__":
    import uvicorn
    from config.config import API_HOST, API_PORT
    
    # For HuggingFace Spaces, we typically run on 0.0.0.0:7860
    # But the import above is what actually matters for HF deployment
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=7860,  # HuggingFace Spaces default port
        log_level="info"
    )
