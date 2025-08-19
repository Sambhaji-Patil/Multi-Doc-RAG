"""
PDF Downloader Module

Handles downloading PDFs from URLs with retry logic and progress tracking.
"""

import os
import asyncio
import tempfile
import aiohttp
from typing import Optional
from logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__file__)


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
        logger.info("Downloading PDF", url_preview=(url[:50] + '...' if len(url) > 50 else url))
        
        for attempt in range(max_retries):
            try:
                # Enhanced timeout settings for large files
                timeout_config = aiohttp.ClientTimeout(
                    total=timeout,          # Total timeout
                    connect=30,             # Connection timeout
                    sock_read=120           # Socket read timeout
                )
                
                async with aiohttp.ClientSession(timeout=timeout_config) as session:
                    logger.info("Attempting PDF download", attempt=attempt + 1, max_retries=max_retries, timeout_s=timeout)
                    
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to download PDF: HTTP {response.status}")
                        
                        # Get content length for progress tracking
                        content_length = response.headers.get('content-length')
                        if content_length:
                            total_size = int(content_length)
                            logger.info("PDF size", size_mb=round(total_size / (1024*1024), 1))
                        
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
                                logger.info("PDF download progress", percent=round(progress, 1), downloaded_mb=round(downloaded/(1024*1024), 1))
                        
                        temp_file.close()
                        logger.info("PDF downloaded successfully", path=temp_file.name)
                        return temp_file.name
                        
            except asyncio.TimeoutError:
                logger.warning("Timeout downloading PDF", attempt=attempt + 1)
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30  # Increasing wait time
                    logger.info("Waiting before retry", wait_seconds=wait_time)
                    await asyncio.sleep(wait_time)
                continue
                
            except Exception as e:
                logger.error("Error downloading PDF", attempt=attempt + 1, error=str(e))
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 15
                    logger.info("Waiting before retry", wait_seconds=wait_time)
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
                logger.info("Cleaned up temporary file", path=temp_path)
            except Exception as e:
                logger.warning("Could not delete temporary file", path=temp_path, error=str(e))
