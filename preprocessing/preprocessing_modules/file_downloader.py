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

class FileDownloader:
    def __init__(self):
        # ... (rest of the class is the same) ...
        self.cache_dir = tempfile.mkdtemp(prefix="file_downloader_")
        print(f"📂 Temp cache directory created: {self.cache_dir}")
        atexit.register(self._cleanup_cache_dir)

    def _get_cache_path(self, cache_key: str, ext: str) -> str:
        """Generate a cache file path for the given cache key and extension."""
        key_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}{ext}")

    async def fetch_file(
        self,
        source: Union[str, bytes],
        filename: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
    ) -> Tuple[str, str]:
        # ... (dispatcher logic is the same) ...
        if isinstance(source, bytes):
            if not filename:
                raise ValueError("Argument 'filename' must be provided when source is bytes.")
            return self._handle_bytes(source, filename)
        elif isinstance(source, str):
            if os.path.exists(source):
                return self._handle_path(source)
            else:
                # Pass session-related configs to the handler
                return await self._handle_url(source, timeout, max_retries)
        else:
            raise TypeError("Source must be a URL string, a local file path string, or bytes.")

    def _handle_path(self, path: str) -> Tuple[str, str]:
        # ... (same as before) ...
        print(f"📂 Processing local file: {path}")
        cache_key = os.path.abspath(path)
        _, ext = os.path.splitext(path)
        if not ext:
            raise ValueError("File from path does not have an extension.")
        cache_path = self._get_cache_path(cache_key, ext)
        if os.path.exists(cache_path):
            print(f"⚡ Cache hit! Using cached file: {cache_path}")
            return cache_path, ext.lstrip(".")
        shutil.copy(path, cache_path)
        print(f"✅ File copied to cache: {cache_path}")
        return cache_path, ext.lstrip(".")

    def _handle_bytes(self, data: bytes, filename: str) -> Tuple[str, str]:
        # ... (same as before) ...
        print(f"📦 Processing byte stream (filename: {filename}, size: {len(data)/1024:.2f} KB)")
        cache_key = hashlib.sha256(data).hexdigest()
        _, ext = os.path.splitext(filename)
        if not ext:
            raise ValueError("Provided filename for byte stream does not have an extension.")
        cache_path = self._get_cache_path(cache_key, ext)
        if os.path.exists(cache_path):
            print(f"⚡ Cache hit! Using cached file: {cache_path}")
            return cache_path, ext.lstrip(".")
        with open(cache_path, "wb") as f:
            f.write(data)
        print(f"✅ Byte stream saved to cache: {cache_path}")
        return cache_path, ext.lstrip(".")

    async def _get_url_metadata(self, session: aiohttp.ClientSession, url: str) -> Tuple[str, str]:
        """
        Performs a HEAD request to get filename and extension before downloading.
        Returns (filename, extension_with_dot)
        """
        try:
            # First, try a HEAD request for efficiency
            async with session.head(url, allow_redirects=True) as response:
                response.raise_for_status() # Check for HTTP errors
                
                # Check Content-Disposition header first
                cd = response.headers.get('Content-Disposition', '')
                filename_match = re.findall('filename="?([^"]+)"?', cd)
                if filename_match:
                    filename = filename_match[0]
                    _, ext = os.path.splitext(filename)
                    if ext: return filename, ext

        except Exception as e:
            print(f"   ⚠️ HEAD request failed or not supported: {e}. Falling back to URL path.")

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
        print(f"📥 Processing URL: {url[:60]}...")
        cache_key = url
        
        timeout_config = aiohttp.ClientTimeout(total=timeout, connect=30, sock_read=120)

        # Create the session once for both HEAD and GET requests
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            # --- ROBUST CACHE CHECK ---
            # Get metadata (like filename and ext) *before* downloading content
            _, ext = await self._get_url_metadata(session, url)

            if ext:
                cache_path = self._get_cache_path(cache_key, ext)
                if os.path.exists(cache_path):
                    print(f"⚡ Cache hit! Using cached file: {cache_path}")
                    return cache_path, ext.lstrip(".")
            # --- END OF CACHE CHECK ---
            
            # If we are here, it means it's not in the cache, so proceed with download
            print(f"   ⬇️ No cache found. Starting download...")
            for attempt in range(max_retries):
                try:
                    print(f"   Attempt {attempt + 1}/{max_retries} (timeout: {timeout}s)")

                    async with session.get(url) as response:
                        response.raise_for_status() # Replaces the old `if response.status != 200`

                        # We already have the extension, but let's re-confirm filename for saving
                        cd = response.headers.get('Content-Disposition', '')
                        filename_match = re.findall('filename="?([^"]+)"?', cd)
                        if filename_match:
                            filename = filename_match[0]
                        else:
                            filename = os.path.basename(unquote(urlparse(url).path)) or "downloaded_file"
                        
                        final_ext = os.path.splitext(filename)[1]
                        if not final_ext:
                            return url, "url" # Handle cases with no extension

                        if final_ext.lower() not in ['.pdf', '.docx', '.pptx', '.png', '.xlsx', '.jpeg', '.jpg', '.txt', '.csv']:
                            print(f"   ❌ File type not supported: {final_ext}")
                            return ['not supported', final_ext.lstrip('.')]
                        
                        final_cache_path = self._get_cache_path(cache_key, final_ext)

                        with open(final_cache_path, "wb") as f:
                            # ... (download progress logic remains the same) ...
                            total_size = int(response.headers.get('content-length', 0))
                            downloaded = 0
                            async for chunk in response.content.iter_chunked(16384):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size and downloaded > 0 and downloaded % (1024 * 1024) < 16384:
                                    progress = (downloaded / total_size) * 100
                                    print(f"   Progress: {progress:.1f}% ({downloaded / (1024*1024):.1f} MB)")

                        print(f"✅ File downloaded successfully: {final_cache_path}")
                        return final_cache_path, final_ext.lstrip('.')

                except asyncio.TimeoutError:
                    print(f"   ⏰ Timeout on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 30
                        print(f"   ⏳ Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                except Exception as e:
                    print(f"   ❌ Error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 15
                        print(f"   ⏳ Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)

        raise Exception(f"Failed to download file after {max_retries} attempts")


    def _cleanup_cache_dir(self):
        # ... (same as before) ...
        if os.path.exists(self.cache_dir):
            try:
                shutil.rmtree(self.cache_dir)
                print(f"🗑️ Deleted temp cache directory: {self.cache_dir}")
            except Exception as e:
                print(f"⚠️ Could not delete cache directory {self.cache_dir}: {e}")