#!/usr/bin/env python3
"""
Main entry point for HuggingFace Spaces deployment.
This is the standard entry point that HuggingFace expects.
"""

import uvicorn
from api.api import app

if __name__ == "__main__":
    # HuggingFace Spaces runs on port 7860 by default
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860,
        log_level="info"
    )
