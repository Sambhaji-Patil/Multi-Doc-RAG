"""
Text Chunker Module

Handles chunking text into smaller pieces with overlap for better context preservation.
"""

import re
from typing import List
from config.config import CHUNK_SIZE, CHUNK_OVERLAP


class TextChunker:
    """Handles text chunking with overlap and smart boundary detection."""
    
    def __init__(self):
        """Initialize the text chunker."""
        self.chunk_size = CHUNK_SIZE
        self.chunk_overlap = CHUNK_OVERLAP
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into smaller pieces with overlap.
        
        Args:
            text: The input text to chunk
            
        Returns:
            List[str]: List of text chunks
        """
        print(f"✂️ Chunking text into {self.chunk_size} character chunks with {self.chunk_overlap} overlap")
        
        # Clean the text
        cleaned_text = self._clean_text(text)
        
        chunks = []
        start = 0
        
        while start < len(cleaned_text):
            end = start + self.chunk_size
            
            # Try to end at sentence boundary
            if end < len(cleaned_text):
                end = self._find_sentence_boundary(cleaned_text, start, end)
            
            chunk = cleaned_text[start:end].strip()
            
            # Only add chunk if it's meaningful
            if chunk and len(chunk) > 50:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(cleaned_text):
                break
        
        print(f"✅ Created {len(chunks)} chunks (size={self.chunk_size}, overlap={self.chunk_overlap})")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text by normalizing whitespace and removing excessive line breaks.
        
        Args:
            text: Raw text to clean
            
        Returns:
            str: Cleaned text
        """
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _find_sentence_boundary(self, text: str, start: int, preferred_end: int) -> int:
        """
        Find the best sentence boundary near the preferred end position.
        
        Args:
            text: The full text
            start: Start position of the chunk
            preferred_end: Preferred end position
            
        Returns:
            int: Adjusted end position at sentence boundary
        """
        # Look for sentence endings within a reasonable range
        search_start = max(start, preferred_end - 100)
        search_end = min(len(text), preferred_end + 50)
        
        sentence_endings = ['.', '!', '?']
        best_end = preferred_end
        
        # Search backwards from preferred end for sentence boundary
        for i in range(preferred_end - 1, search_start - 1, -1):
            if text[i] in sentence_endings:
                # Check if this looks like a real sentence ending
                if self._is_valid_sentence_ending(text, i):
                    best_end = i + 1
                    break
        
        return best_end
    
    def _is_valid_sentence_ending(self, text: str, pos: int) -> bool:
        """
        Check if a punctuation mark represents a valid sentence ending.
        
        Args:
            text: The full text
            pos: Position of the punctuation mark
            
        Returns:
            bool: True if it's a valid sentence ending
        """
        # Avoid breaking on abbreviations like "Dr.", "Mr.", etc.
        if pos > 0 and text[pos] == '.':
            # Look at the character before the period
            char_before = text[pos - 1]
            if char_before.isupper():
                # Might be an abbreviation
                word_start = pos - 1
                while word_start > 0 and text[word_start - 1].isalpha():
                    word_start -= 1
                
                word = text[word_start:pos]
                # Common abbreviations to avoid breaking on
                abbreviations = {'Dr', 'Mr', 'Mrs', 'Ms', 'Prof', 'Inc', 'Ltd', 'Corp', 'Co'}
                if word in abbreviations:
                    return False
        
        # Check if there's a space or newline after the punctuation
        if pos + 1 < len(text):
            next_char = text[pos + 1]
            return next_char.isspace() or next_char.isupper()
        
        return True
    
    def get_chunk_stats(self, chunks: List[str]) -> dict:
        """
        Get statistics about the created chunks.
        
        Args:
            chunks: List of text chunks
            
        Returns:
            dict: Statistics about the chunks
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "total_characters": 0,
                "total_words": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0
            }
        
        chunk_sizes = [len(chunk) for chunk in chunks]
        total_chars = sum(chunk_sizes)
        total_words = sum(len(chunk.split()) for chunk in chunks)
        
        return {
            "total_chunks": len(chunks),
            "total_characters": total_chars,
            "total_words": total_words,
            "avg_chunk_size": total_chars / len(chunks),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes)
        }
