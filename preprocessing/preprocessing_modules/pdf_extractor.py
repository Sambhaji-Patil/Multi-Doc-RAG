"""
Enhanced Text Extractor Module for FastAPI
Handles extracting text content from PDF files with improved performance,
table extraction, and proper CID font handling for scripts containing non English scripts.
Returns data structured by page number.
"""
import pdfplumber
import pymupdf  # PyMuPDF (fitz)
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
import concurrent.futures
from pathlib import Path
import logging
import re
import unicodedata

class TextExtractor:
    """FastAPI-compatible text extractor with enhanced capabilities."""
   
    def __init__(self, max_workers: int = 4, backend: str = "auto"):
        """
        Initialize the enhanced text extractor.
        
        Args:
            max_workers: Number of worker threads for parallel processing
            backend: Extraction backend ('pdfplumber', 'pymupdf', 'auto')
        """
        self.max_workers = max_workers
        self.backend = backend
        self.logger = logging.getLogger(__name__)
        self.cache = {}
        
    def extract_text_from_pdf(self, pdf_path: str, extract_tables: bool = True, 
                             handle_cid: bool = True) -> List[Dict[str, Union[int, str]]]:
        """
        Extract text from each page of a PDF file.
       
        Args:
            pdf_path: Path to the PDF file
            extract_tables: Whether to extract and format tables inline
            handle_cid: Whether to handle CID font mapping issues
           
        Returns:
            List[Dict]: A list of dictionaries, where each dictionary
                        represents a page and contains 'page_num' and 'content'.
                        Example: [{'page_num': 1, 'content': '...'}, ...]
           
        Raises:
            Exception: If text extraction fails
        """
        cached_data = self.cache.get(pdf_path)
        if cached_data:
            print("Using Cache: Skipped pdf extraction")
            return cached_data
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.logger.info(f"Extracting text from PDF: {pdf_path.name}")
        
        # Choose extraction method based on backend
        if self.backend == "pymupdf" or (self.backend == "auto" and handle_cid):
            pages_data = self._extract_with_pymupdf(pdf_path, extract_tables, handle_cid)
        else:
            pages_data = self._extract_with_pdfplumber(pdf_path, extract_tables)
            
        self.cache[pdf_path] = pages_data
        return pages_data
    
    def _fallback_text_extraction(self, page: pymupdf.Page) -> List[Dict]:
        """Fallback text extraction for problematic pages."""
        try:
            # Method 1: Try simple text extraction
            simple_text = page.get_text()
            if simple_text and simple_text.strip():
                self.logger.info("Using simple text extraction fallback")
                return [{
                    'type': 'text',
                    'content': simple_text,
                    'bbox': page.rect
                }]
        except:
            pass
        
        try:
            # Method 2: Try text extraction with different options
            text_options = ["text", "blocks", "words"]
            for option in text_options:
                try:
                    extracted = page.get_text(option)
                    if extracted:
                        if isinstance(extracted, list):
                            # For blocks/words, join them
                            text_content = ""
                            for item in extracted:
                                if isinstance(item, tuple) and len(item) > 4:
                                    text_content += str(item[4]) + " "  # text part
                                elif isinstance(item, str):
                                    text_content += item + " "
                            if text_content.strip():
                                self.logger.info(f"Using {option} extraction fallback")
                                return [{
                                    'type': 'text',
                                    'content': text_content.strip(),
                                    'bbox': page.rect
                                }]
                        elif isinstance(extracted, str) and extracted.strip():
                            self.logger.info(f"Using {option} extraction fallback")
                            return [{
                                'type': 'text',
                                'content': extracted,
                                'bbox': page.rect
                            }]
                except Exception as e:
                    self.logger.debug(f"Failed {option} extraction: {e}")
                    continue
        except:
            pass
        
        try:
            # Method 3: Check if page has images (might be scanned document)
            image_list = page.get_images()
            if image_list:
                self.logger.warning("Page appears to contain images - might be scanned document")
                return [{
                    'type': 'text',
                    'content': f"[Page contains {len(image_list)} image(s) - possible scanned document. Consider OCR processing.]",
                    'bbox': page.rect
                }]
        except:
            pass
        
        # Method 4: Last resort - return empty with warning
        self.logger.warning("All extraction methods failed, returning empty content")
        return [{
            'type': 'text',
            'content': "[Unable to extract text from this page - may be image-based or corrupted]",
            'bbox': page.rect
        }]
    
    def _extract_with_pymupdf_safe(self, pdf_path: Path, extract_tables: bool, 
                                  handle_cid: bool) -> str:
        """Safe PyMuPDF extraction with comprehensive error handling."""
        
        def extract_page_content_safe(page_data: Tuple[int, pymupdf.Page]) -> Dict:
            page_num, page = page_data
            result = {
                'page_num': page_num + 1,
                'content_blocks': []
            }
            
            try:
                # Check if page is valid
                if not hasattr(page, 'rect'):
                    raise Exception("Invalid page object")
                
                # Try to get basic page info first
                page_rect = page.rect
                if not page_rect or page_rect.is_empty:
                    raise Exception("Empty page")
                
                # Extract text with error handling
                text_blocks = []
                table_blocks = []
                
                # Text extraction with fallbacks
                if handle_cid:
                    try:
                        text_blocks = self._extract_text_blocks_with_proper_spacing(page)
                    except Exception as text_error:
                        self.logger.warning(f"Advanced text extraction failed on page {page_num + 1}: {text_error}")
                        text_blocks = self._fallback_text_extraction(page)
                else:
                    try:
                        text = page.get_text()
                        if text and text.strip():
                            text_blocks.append({
                                'type': 'text',
                                'content': text,
                                'bbox': page.rect
                            })
                        else:
                            text_blocks = self._fallback_text_extraction(page)
                    except Exception as simple_error:
                        self.logger.warning(f"Simple text extraction failed on page {page_num + 1}: {simple_error}")
                        text_blocks = self._fallback_text_extraction(page)
                
                # Table extraction with error handling
                if extract_tables:
                    try:
                        tables = page.find_tables()
                        for i, table in enumerate(tables):
                            try:
                                table_data = table.extract()
                                if table_data and any(any(cell for cell in row if cell) for row in table_data):
                                    formatted_table = self._format_table_as_text(table_data, page_num + 1, i + 1)
                                    table_blocks.append({
                                        'type': 'table',
                                        'content': formatted_table,
                                        'bbox': table.bbox
                                    })
                            except Exception as table_error:
                                self.logger.warning(f"Failed to extract table {i+1} on page {page_num + 1}: {table_error}")
                    except Exception as tables_error:
                        self.logger.warning(f"Table detection failed on page {page_num + 1}: {tables_error}")
                
                # Combine and sort blocks by position
                all_blocks = text_blocks + table_blocks
                if all_blocks:
                    # Sort by y-coordinate (top to bottom), handle missing bbox gracefully
                    try:
                        all_blocks.sort(key=lambda x: x.get('bbox', [0, 0, 0, 0])[1])
                    except:
                        # If sorting fails, keep original order
                        pass
                
                result['content_blocks'] = all_blocks if all_blocks else [{
                    'type': 'text',
                    'content': f"[No content extracted from page {page_num + 1}]",
                    'bbox': (0, 0, 0, 0)
                }]
                
            except Exception as e:
                self.logger.error(f"Critical error processing page {page_num + 1}: {e}")
                result['content_blocks'] = [{
                    'type': 'text',
                    'content': f"[Critical error on page {page_num + 1}: {str(e)}]",
                    'bbox': (0, 0, 0, 0)
                }]
            
            return result
        
        return extract_page_content_safe

    def _extract_with_pymupdf(self, pdf_path: Path, extract_tables: bool, 
                             handle_cid: bool) -> List[Dict[str, Union[int, str]]]:
        """Extract using PyMuPDF, returning content per page."""
        
        extract_page_content_safe = self._extract_with_pymupdf_safe(pdf_path, extract_tables, handle_cid)
        
        try:
            doc = pymupdf.open(pdf_path)
            
            if not doc or doc.page_count == 0:
                raise Exception("Invalid or empty PDF document")
            
            self.logger.info(f"Processing {doc.page_count} pages with PyMuPDF")
            
            page_results = []
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    page_data = []
                    for i in range(doc.page_count):
                        try:
                            page_data.append((i, doc[i]))
                        except Exception as page_error:
                            self.logger.error(f"Failed to access page {i+1}: {page_error}")
                            page_data.append((i, None))
                    
                    if page_data:
                        page_results = list(executor.map(extract_page_content_safe, page_data))
                    else:
                        raise Exception("No accessible pages found")
            
            except Exception as parallel_error:
                self.logger.warning(f"Parallel processing failed, trying sequential: {parallel_error}")
                for i in range(doc.page_count):
                    try:
                        result = extract_page_content_safe((i, doc[i]))
                        page_results.append(result)
                    except Exception as seq_error:
                        self.logger.error(f"Sequential processing failed for page {i+1}: {seq_error}")
                        page_results.append({
                            'page_num': i + 1,
                            'content_blocks': [{'type': 'text', 'content': f"[Error: Could not process page {i+1}]"}]
                        })

            final_pages = []
            successful_pages = 0
            total_chars = 0

            # Sort results by page number to ensure correct order
            page_results.sort(key=lambda p: p.get('page_num', 0))

            for result in page_results:
                if not result or 'content_blocks' not in result:
                    continue
                
                page_content = ""
                page_has_content = False
                
                for block in result['content_blocks']:
                    content = block.get('content', '').strip()
                    if not content:
                        continue
                    
                    if block.get('type') == 'text':
                        if not content.startswith('[Error') and not content.startswith('[No content') and not content.startswith('[Unable'):
                            page_has_content = True
                        page_content += content + "\n"
                    elif block.get('type') == 'table':
                        page_content += "\n" + content + "\n"
                        page_has_content = True
                
                if page_has_content:
                    successful_pages += 1
                
                cleaned_content = self._clean_final_text(page_content)
                total_chars += len(cleaned_content)
                
                final_pages.append({
                    'page_num': result['page_num'],
                    'content': cleaned_content
                })
            
            doc.close()
            
            self.logger.info(f"Successfully processed {successful_pages}/{len(page_results)} pages, extracted {total_chars} characters with PyMuPDF")
            
            if successful_pages == 0 and page_results:
                raise Exception("No content could be extracted from any page. This might be a scanned document requiring OCR.")
            
            return final_pages
            
        except Exception as e:
            error_msg = f"Failed to extract text with PyMuPDF: {str(e)}"
            self.logger.error(error_msg)
            
            self.logger.info("Attempting pdfplumber fallback...")
            try:
                return self._extract_with_pdfplumber(pdf_path, extract_tables)
            except Exception as fallback_error:
                self.logger.error(f"Pdfplumber fallback also failed: {fallback_error}")
                raise Exception(f"{error_msg}. Fallback with pdfplumber also failed: {fallback_error}")
    
    def _extract_text_blocks_with_proper_spacing(self, page: pymupdf.Page) -> List[Dict]:
        """Extract text blocks with proper word spacing and line handling."""
        text_blocks = []
        
        try:
            text_dict = page.get_text("dict")
        except Exception as e:
            self.logger.warning(f"Failed to get text dict, falling back: {e}")
            return self._fallback_text_extraction(page)
        
        if not text_dict or "blocks" not in text_dict:
            self.logger.warning("Invalid text dictionary, using fallback")
            return self._fallback_text_extraction(page)
        
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            
            block_text = ""
            current_line_y = None
            
            for line in block["lines"]:
                line_y = line.get("bbox", [0, 0, 0, 0])[1]
                
                line_text = ""
                prev_span_end = None
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    if not span_text.strip():
                        continue
                    
                    if self._has_cid_issues(span_text):
                        span_text = self._resolve_cid_text_advanced(span_text, span)
                    
                    span_bbox = span.get("bbox", [0, 0, 0, 0])
                    if prev_span_end is not None and span_bbox[0] - prev_span_end > 3: # Word gap threshold
                        line_text += " "
                    
                    line_text += span_text
                    prev_span_end = span_bbox[2]
                
                block_text += line_text + "\n"
            
            if block_text.strip():
                text_blocks.append({
                    'type': 'text',
                    'content': block_text,
                    'bbox': block.get("bbox", page.rect)
                })
        
        if not text_blocks:
            return self._fallback_text_extraction(page)
        
        return text_blocks
    
    def _has_cid_issues(self, text: str) -> bool:
        """Check if text has CID mapping issues."""
        return bool(re.search(r'\(cid:\d+\)|cid-\d+', text, re.IGNORECASE))
    
    def _resolve_cid_text_advanced(self, text: str, span: Dict) -> str:
        """Advanced CID resolution with better character recovery."""
        if not self._has_cid_issues(text):
            return text
        
        processed = re.sub(r'\s*\(cid:\d+\)\s*', '', text, flags=re.IGNORECASE)
        processed = re.sub(r'\s*cid-\d+\s*', '', processed, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', processed).strip()

    def _format_table_as_text(self, table_data: List[List], page_num: int, table_num: int) -> str:
        """Format table data as readable text."""
        if not table_data:
            return ""
        
        try:
            df = pd.DataFrame(table_data).fillna('').astype(str)
            formatted = f"\n{'='*60}\n"
            formatted += f"TABLE {table_num} (Page {page_num})\n"
            formatted += f"{'='*60}\n"
            formatted += df.to_string(index=False, header=False, max_colwidth=30)
            formatted += f"\n{'='*60}\n"
            return formatted
        except Exception as e:
            self.logger.warning(f"Failed to format table: {e}")
            return f"\n[TABLE {table_num} - Page {page_num}: Formatting Error]\n"
    
    def _extract_with_pdfplumber(self, pdf_path: Path, extract_tables: bool) -> List[Dict[str, Union[int, str]]]:
        """Extract using pdfplumber, returning content per page."""
        
        def extract_page_content(page_data: Tuple[int, pdfplumber.page.Page]) -> Dict[str, Union[int, str]]:
            page_num, page = page_data
            page_content = ""
            
            try:
                text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                page_content += text
                
                if extract_tables:
                    tables = page.extract_tables()
                    if tables:
                        page_content += "\n"
                        for i, table in enumerate(tables):
                            if table:
                                formatted_table = self._format_table_as_text(table, page_num + 1, i + 1)
                                page_content += formatted_table + "\n"
            except Exception as e:
                self.logger.error(f"Error processing page {page_num + 1} with pdfplumber: {e}")
                page_content = f"[Error extracting page {page_num + 1}]"

            return {
                'page_num': page_num + 1,
                'content': self._clean_final_text(page_content)
            }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    page_data = [(i, pdf.pages[i]) for i in range(len(pdf.pages))]
                    page_results = list(executor.map(extract_page_content, page_data))
            
            total_chars = sum(len(page['content']) for page in page_results)
            self.logger.info(f"Extracted {total_chars} characters from {len(page_results)} pages using pdfplumber.")
            return page_results
            
        except Exception as e:
            raise Exception(f"Failed to extract text with pdfplumber: {str(e)}")
    
    def _clean_final_text(self, text: str) -> str:
        """Final cleanup of extracted text."""
        if not text:
            return ""
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'[ \t]*\n[ \t]*', '\n', text)
        lines = text.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        return '\n'.join(cleaned_lines).strip()
    
    def validate_extracted_text(self, text: str, min_chars: int = 50) -> Tuple[bool, Dict]:
        """
        Validate extracted text from a single page with detailed feedback.
       
        Args:
            text: The extracted text to validate
            min_chars: Minimum number of alphabetic characters required
           
        Returns:
            Tuple of (is_valid, validation_details)
        """
        details = {
            'total_chars': len(text) if text else 0,
            'alphabetic_chars': 0,
            'has_content': bool(text and text.strip()),
            'cid_issues': 0,
            'validation_passed': False,
            'line_breaks_ratio': 0
        }
        
        if not text or not text.strip():
            return False, details
        
        details['alphabetic_chars'] = sum(1 for char in text if char.isalpha())
        details['cid_issues'] = len(re.findall(r'\(cid:\d+\)|cid-\d+|\[\?\]', text, re.IGNORECASE))
        
        if details['total_chars'] > 0:
            details['line_breaks_ratio'] = text.count('\n') / details['total_chars']
        
        details['validation_passed'] = (
            details['alphabetic_chars'] >= min_chars and 
            details['line_breaks_ratio'] < 0.1
        )
        
        return details['validation_passed'], details