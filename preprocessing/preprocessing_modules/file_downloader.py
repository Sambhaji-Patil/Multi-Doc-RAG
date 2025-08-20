import aiohttp
import asyncio
import tempfile
import os
import re
import shutil
import hashlib
import atexit
from urllib.parse import urlparse, unquote
from typing import List, Tuple, Union, Optional
from logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__file__)


class FileDownloader:
    def __init__(self):
        self.file_dir = "files"
        os.makedirs(self.file_dir, exist_ok=True)

    def _get_cache_path(self, cache_key: str, ext: str) -> str:
        """Generate a cache file path for the given cache key and extension."""
        key_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
        return os.path.join(self.file_dir, f"{key_hash}{ext}")

    async def fetch_file(
        self,
        source: Union[str, bytes],
        filename: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
    ) -> Tuple[str, str]:
        """Dispatch to the appropriate handler based on the source type."""
        if isinstance(source, bytes):
            if not filename:
                raise ValueError("Argument 'filename' must be provided when source is bytes.")
            return self._handle_bytes(source, filename)
        elif isinstance(source, str):
            # Handle local file paths (including URL-encoded paths)
            decoded_source = unquote(source)
            if os.path.exists(source):
                return self._handle_path(source)
            elif os.path.exists(decoded_source):
                return self._handle_path(decoded_source)
            else:
                # Pass session-related configs to the handler
                return await self._handle_url(source, timeout, max_retries)
        else:
            raise TypeError("Source must be a URL string, a local file path string, or bytes.")

    def _handle_path(self, path: str) -> Tuple[str, str]:
        """Handle local file paths with proper normalization and URL decoding."""
        decoded_path = unquote(path)
        normalized_path = os.path.normpath(os.path.abspath(decoded_path))

        logger.info("Processing local file", original_path=path, decoded_path=decoded_path, normalized_path=normalized_path)
        if path != decoded_path:
            logger.info("Decoded to", decoded_path=decoded_path)

        # Check if file actually exists
        if not os.path.exists(normalized_path):
            raise FileNotFoundError(f"Local file not found: {normalized_path}")

        cache_key = normalized_path
        _, ext = os.path.splitext(normalized_path)
        if not ext:
            raise ValueError("File from path does not have an extension.")

        # Check supported file types
        supported_extensions = ['.pdf', '.docx', '.pptx', '.png', '.xlsx', '.jpeg', '.jpg', '.txt', '.csv']
        if ext.lower() not in supported_extensions:
            raise ValueError(f"File type '{ext}' is not supported. Supported types: {supported_extensions}")

        cache_path = self._get_cache_path(cache_key, ext)
        if os.path.exists(cache_path):
            logger.info("Cache hit", cache_path=cache_path)
            return cache_path, ext.lstrip('.')

        shutil.copy(normalized_path, cache_path)
        logger.info("File copied to cache", cache_path=cache_path)
        return cache_path, ext.lstrip('.')

    def _handle_bytes(self, data: bytes, filename: str) -> Tuple[str, str]:
        logger.info("Processing byte stream", filename=filename, size_kb=len(data) / 1024.0)
        cache_key = hashlib.sha256(data).hexdigest()
        _, ext = os.path.splitext(filename)
        if not ext:
            raise ValueError("Provided filename for byte stream does not have an extension.")
        cache_path = self._get_cache_path(cache_key, ext)
        if os.path.exists(cache_path):
            logger.info("Cache hit", cache_path=cache_path)
            return cache_path, ext.lstrip('.')
        with open(cache_path, "wb") as f:
            f.write(data)
        logger.info("Byte stream saved to cache", cache_path=cache_path)
        return cache_path, ext.lstrip('.')

    async def _get_url_metadata(self, session: aiohttp.ClientSession, url: str) -> Tuple[str, str]:
        """
        Performs a HEAD request to get filename and extension before downloading.
        Returns (filename, extension_with_dot)
        """
        try:
            async with session.head(url, allow_redirects=True) as response:
                response.raise_for_status()

                cd = response.headers.get('Content-Disposition', '')
                filename_match = re.findall('filename="?([^\"]+)"?', cd)
                if filename_match:
                    filename = filename_match[0]
                    _, ext = os.path.splitext(filename)
                    if ext:
                        return filename, ext

        except Exception as e:
            logger.warning("HEAD request failed or not supported, falling back to URL path", url=url, error=str(e))

        # Fallback to parsing the URL path
        parsed_path = unquote(urlparse(url).path)
        filename = os.path.basename(parsed_path) or "downloaded_file"
        _, ext = os.path.splitext(filename)
        return filename, ext

    async def _handle_url(
        self, url: str, timeout: int, max_retries: int
    ) -> Union[Tuple[str, str], List[str]]:
        """
        Download any file type from a URL to the temp cache, with robust caching.
        """
        logger.info("Processing URL", url_preview=(url[:60] + '...' if len(url) > 60 else url))
        cache_key = url

        timeout_config = aiohttp.ClientTimeout(total=timeout, connect=30, sock_read=120)

        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            # --- ROBUST CACHE CHECK ---
            _, ext = await self._get_url_metadata(session, url)

            if ext:
                cache_path = self._get_cache_path(cache_key, ext)
                if os.path.exists(cache_path):
                    logger.info("Cache hit", cache_path=cache_path)
                    return cache_path, ext.lstrip('.')

            # If not cached, download
            logger.info("No cache found. Starting download", url=url)
            for attempt in range(max_retries):
                try:
                    logger.info("Download attempt", attempt=attempt + 1, max_retries=max_retries, timeout_s=timeout)

                    async with session.get(url) as response:
                        response.raise_for_status()

                        cd = response.headers.get('Content-Disposition', '')
                        filename_match = re.findall('filename="?([^\"]+)"?', cd)
                        if filename_match:
                            filename = filename_match[0]
                        else:
                            filename = os.path.basename(unquote(urlparse(url).path)) or "downloaded_file"

                        final_ext = os.path.splitext(filename)[1]
                        if not final_ext:
                            return url, "url"

                        if final_ext.lower() not in ['.pdf', '.docx', '.pptx', '.png', '.xlsx', '.jpeg', '.jpg', '.txt', '.csv']:
                            logger.error("File type not supported", file_type=final_ext)
                            return ['not supported', final_ext.lstrip('.')]

                        final_cache_path = self._get_cache_path(cache_key, final_ext)

                        with open(final_cache_path, "wb") as f:
                            total_size = int(response.headers.get('content-length', 0))
                            downloaded = 0
                            async for chunk in response.content.iter_chunked(16384):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size and downloaded > 0 and downloaded % (1024 * 1024) < 16384:
                                    progress = (downloaded / total_size) * 100
                                    logger.info("Download progress", percent=round(progress, 1), downloaded_mb=round(downloaded / (1024*1024), 1))

                        logger.info("File downloaded successfully", cache_path=final_cache_path)
                        print("🟢 File Downloaded successfully")
                        return final_cache_path, final_ext.lstrip('.')

                except asyncio.TimeoutError:
                    logger.warning("Timeout on download attempt", attempt=attempt + 1)
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 30
                        logger.info("Waiting before retry", wait_seconds=wait_time)
                        await asyncio.sleep(wait_time)
                except Exception as e:
                    logger.error("Error on download attempt", attempt=attempt + 1, error=str(e))
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 15
                        logger.info("Waiting before retry", wait_seconds=wait_time)
                        await asyncio.sleep(wait_time)

        raise Exception(f"Failed to download file after {max_retries} attempts")


    def _cleanup_file_dir(self):
        if os.path.exists(self.file_dir):
            try:
                shutil.rmtree(self.file_dir)
                logger.info("Deleted temp cache directory", file_dir=self.file_dir)
            except Exception as e:
                logger.warning("Could not delete cache directory", file_dir=self.file_dir, error=str(e))