"""
Text Chunker Module
Handles chunking text into smaller pieces with overlap for better context preservation.
"""

import re
from typing import List, Dict, Any
from config.config import CHUNK_SIZE, CHUNK_OVERLAP
from logger.custom_logger import CustomLogger

# module logger
logger = CustomLogger().get_logger(__file__)


class TextChunker:
    """Handles text chunking with overlap and smart boundary detection."""
    
    def __init__(self):
        """Initialize the text chunker."""
        self.chunk_size = CHUNK_SIZE
        self.chunk_overlap = CHUNK_OVERLAP
    
    def chunk_text(self, pages: List[Dict[str, Any]], doc_id: str) -> List[str]:
        """
        Chunk text into smaller pieces with overlap.
        
        Args:
            pages: List of dicts like [{ "page_num": int, "content": str }]
            
        Returns:
            List[dict]: List of chunks with page number and content
        """
        logger.info("Chunking text", chunk_size=self.chunk_size, overlap=self.chunk_overlap)

        # Merge all pages into one text, but keep track of offsets
        merged_text = ""
        page_boundaries = []  # [(page_num, start_offset, end_offset)]
        offset = 0

        for p in pages:
            content = self._clean_text(p["content"])
            start_offset = offset
            merged_text += content + " "
            offset = len(merged_text)
            page_boundaries.append((p["page_num"], start_offset, offset))

        chunks = []
        start = 0

        while start < len(merged_text):
            end = start + self.chunk_size

            if end < len(merged_text):
                end = self._find_sentence_boundary(merged_text, start, end)

            chunk_text = merged_text[start:end].strip()

            if chunk_text and len(chunk_text) > 50:
                # Find which page the chunk starts in
                chunk_page = self._get_page_for_offset(start, page_boundaries)
                chunks.append(f"--- doc id: {doc_id}, page number: {chunk_page}\n{chunk_text}\n")

            # Move start with overlap
            start = end - self.chunk_overlap
            if start >= len(merged_text):
                break

        logger.info("Created chunks", count=len(chunks), chunk_size=self.chunk_size, overlap=self.chunk_overlap)
        return chunks

    def _get_page_for_offset(self, offset: int, page_boundaries: List[tuple]) -> int:
        """
        Find the page number for a given character offset in merged text.
        Args:
            offset: Character offset
            page_boundaries: List of (page_num, start_offset, end_offset)
        Returns:
            int: Page number where this offset belongs
        """
        for page_num, start, end in page_boundaries:
            if start <= offset < end:
                return page_num
        return page_boundaries[-1][0]  # fallback: last page

    def _clean_text(self, text: str) -> str:
        """Clean text by normalizing whitespace and removing excessive line breaks."""
        return re.sub(r'\s+', ' ', text).strip()
    
    def _find_sentence_boundary(self, text: str, start: int, preferred_end: int) -> int:
        """Find the best sentence boundary near the preferred end position."""
        search_start = max(start, preferred_end - 100)
        search_end = min(len(text), preferred_end + 50)
        
        sentence_endings = ['.', '!', '?']
        best_end = preferred_end
        
        for i in range(preferred_end - 1, search_start - 1, -1):
            if text[i] in sentence_endings:
                if self._is_valid_sentence_ending(text, i):
                    best_end = i + 1
                    break
        return best_end
    
    def _is_valid_sentence_ending(self, text: str, pos: int) -> bool:
        """Check if a punctuation mark represents a valid sentence ending."""
        if pos > 0 and text[pos] == '.':
            char_before = text[pos - 1]
            if char_before.isupper():
                word_start = pos - 1
                while word_start > 0 and text[word_start - 1].isalpha():
                    word_start -= 1
                word = text[word_start:pos]
                abbreviations = {'Dr', 'Mr', 'Mrs', 'Ms', 'Prof', 'Inc', 'Ltd', 'Corp', 'Co'}
                if word in abbreviations:
                    return False
        
        if pos + 1 < len(text):
            next_char = text[pos + 1]
            return next_char.isspace() or next_char.isupper()
        return True


