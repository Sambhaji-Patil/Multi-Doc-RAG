"""
PDF Downloader Module

Handles downloading PDFs from URLs with retry logic and progress tracking.
"""

import os
import asyncio
import tempfile
import aiohttp
from typing import Optional


class PDFDownloader:
    """Handles PDF downloading with enhanced error handling and retry logic."""
    
    def __init__(self):
        """Initialize the PDF downloader."""
        pass
    
    async def download_pdf(self, url: str, timeout: int = 300, max_retries: int = 3) -> str:
        """
        Download PDF from URL to a temporary file with enhanced error handling.
        
        Args:
            url: URL of the PDF to download
            timeout: Download timeout in seconds (default: 300s/5min)
            max_retries: Maximum number of retry attempts
            
        Returns:
            str: Path to the downloaded temporary file
            
        Raises:
            Exception: If download fails after all retries
        """
        print(f"📥 Downloading PDF from: {url[:50]}...")
        
        for attempt in range(max_retries):
            try:
                # Enhanced timeout settings for large files
                timeout_config = aiohttp.ClientTimeout(
                    total=timeout,          # Total timeout
                    connect=30,             # Connection timeout
                    sock_read=120           # Socket read timeout
                )
                
                async with aiohttp.ClientSession(timeout=timeout_config) as session:
                    print(f"   Attempt {attempt + 1}/{max_retries} (timeout: {timeout}s)")
                    
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to download PDF: HTTP {response.status}")
                        
                        # Get content length for progress tracking
                        content_length = response.headers.get('content-length')
                        if content_length:
                            total_size = int(content_length)
                            print(f"   File size: {total_size / (1024*1024):.1f} MB")
                        
                        # Create temporary file
                        temp_file = tempfile.NamedTemporaryFile(
                            delete=False, 
                            suffix=".pdf",
                            prefix="preprocess_"
                        )
                        
                        # Write content to temporary file with progress tracking
                        downloaded = 0
                        async for chunk in response.content.iter_chunked(16384):  # Larger chunks
                            temp_file.write(chunk)
                            downloaded += len(chunk)
                            
                            # Show progress for large files
                            if content_length and downloaded % (1024*1024) == 0:  # Every MB
                                progress = (downloaded / total_size) * 100
                                print(f"   Progress: {progress:.1f}% ({downloaded/(1024*1024):.1f} MB)")
                        
                        temp_file.close()
                        print(f"✅ PDF downloaded successfully: {temp_file.name}")
                        return temp_file.name
                        
            except asyncio.TimeoutError:
                print(f"   ⏰ Timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30  # Increasing wait time
                    print(f"   ⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                continue
                
            except Exception as e:
                print(f"   ❌ Error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 15
                    print(f"   ⏳ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                continue
        
        raise Exception(f"Failed to download PDF after {max_retries} attempts")
    
    def cleanup_temp_file(self, temp_path: str) -> None:
        """
        Clean up temporary file.
        
        Args:
            temp_path: Path to the temporary file to delete
        """
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                print(f"🗑️ Cleaned up temporary file: {temp_path}")
            except Exception as e:
                print(f"⚠️ Warning: Could not delete temporary file {temp_path}: {e}")
