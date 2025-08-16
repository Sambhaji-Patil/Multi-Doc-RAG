import aiohttp
import asyncio
import tempfile
import os
import re
import shutil
import hashlib
import atexit
from urllib.parse import urlparse, unquote
from typing import List, Tuple


class FileDownloader:
    def __init__(self):
        # Create a temp directory for this process
        self.cache_dir = tempfile.mkdtemp(prefix="file_downloader_")
        print(f"📂 Temp cache directory created: {self.cache_dir}")

        # Ensure cleanup at process exit
        atexit.register(self._cleanup_cache_dir)

    def _get_cache_path(self, url: str, ext: str) -> str:
        """Generate a cache file path for the given URL and extension."""
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}{ext}")

    async def download_file(
        self, url: str, timeout: int = 300, max_retries: int = 3
    ) -> Tuple[str, str]:
        """
        Download any file type from a URL to the temp cache.
        Returns (file_path, extension_without_dot)
        """
        print(f"📥 Downloading file from: {url[:60]}...")

        # Determine file extension (before downloading)
        parsed_path = unquote(urlparse(url).path)
        guessed_ext = os.path.splitext(parsed_path)[1] or ""

        # Check if cached version exists
        if guessed_ext:
            cache_path = self._get_cache_path(url, guessed_ext)
            if os.path.exists(cache_path):
                print(f"⚡ Cache hit! Using cached file: {cache_path}")
                return cache_path, guessed_ext.lstrip(".")

        for attempt in range(max_retries):
            try:
                timeout_config = aiohttp.ClientTimeout(
                    total=timeout,
                    connect=30,
                    sock_read=120
                )

                async with aiohttp.ClientSession(timeout=timeout_config) as session:
                    print(f"   Attempt {attempt + 1}/{max_retries} (timeout: {timeout}s)")

                    async with session.get(url) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to download file: HTTP {response.status}")

                        # Extract filename from header or URL
                        cd = response.headers.get('Content-Disposition', '')
                        filename_match = re.findall('filename="?([^"]+)"?', cd)
                        if filename_match:
                            filename = filename_match[0]
                        else:
                            filename = os.path.basename(parsed_path)

                        if not filename:
                            filename = "downloaded_file"

                        ext = os.path.splitext(filename)[1]
                        if not ext:
                            return url, "url"

                        if ext not in ['.pdf', '.docx', '.pptx', '.png', '.xlsx', '.jpeg', '.jpg', '.txt', '.csv']:
                            print(f"   ❌ File type not supported: {ext}")
                            return ['not supported', ext.lstrip('.')]

                        # Final cache path based on extension
                        cache_path = self._get_cache_path(url, ext)

                        # Download directly to cache path
                        with open(cache_path, "wb") as f:
                            downloaded = 0
                            content_length = response.headers.get('content-length')
                            total_size = int(content_length) if content_length else None

                            async for chunk in response.content.iter_chunked(16384):
                                f.write(chunk)
                                downloaded += len(chunk)

                                if total_size and downloaded % (1024 * 1024) == 0:
                                    progress = (downloaded / total_size) * 100
                                    print(f"   Progress: {progress:.1f}% ({downloaded / (1024*1024):.1f} MB)")

                        print(f"✅ File downloaded successfully: {cache_path}")
                        return cache_path, ext.lstrip('.')

            except asyncio.TimeoutError:
                print(f"   ⏰ Timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30
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

        raise Exception(f"Failed to download file after {max_retries} attempts")

    def _cleanup_cache_dir(self):
        """Remove the entire cache directory."""
        if os.path.exists(self.cache_dir):
            try:
                shutil.rmtree(self.cache_dir)
                print(f"🗑️ Deleted temp cache directory: {self.cache_dir}")
            except Exception as e:
                print(f"⚠️ Could not delete cache directory {self.cache_dir}: {e}")
