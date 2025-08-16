from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from typing import List, Dict, Any
from PIL import Image
from io import BytesIO
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import os


from config.config import OCR_SPACE_API_KEY
API_URL = "https://api.ocr.space/parse/image"

assert OCR_SPACE_API_KEY, "OCR_SPACE_API_KEY not set"

def ocr_space_file(filename, api_key=OCR_SPACE_API_KEY, overlay=False, language="eng"):
    """Extract text from image file using OCR Space API"""
    payload = {
        "isOverlayRequired": overlay,
        "apikey": api_key,
        "language": language,
        "detectOrientation": True,
        "scale": True,
        "isTable": False,
        "OCREngine": 2
    }
    try:
        with open(filename, "rb") as f:
            response = requests.post(API_URL, files={filename: f}, data=payload, timeout=30)
        
        if response.status_code != 200:
            return filename, f"API Error: HTTP {response.status_code}"
            
        parsed = response.json()
        
        if parsed.get("OCRExitCode") == 1:
            parsed_text = parsed.get("ParsedResults", [{}])[0].get("ParsedText", "")
            return filename, parsed_text
        else:
            error_msg = parsed.get("ErrorMessage", ["Unknown error"])[0] if parsed.get("ErrorMessage") else "Unknown OCR error"
            return filename, f"OCR Error: {error_msg}"
            
    except requests.exceptions.Timeout:
        return filename, "Error: Request timeout"
    except requests.exceptions.RequestException as e:
        return filename, f"Error: Network error - {str(e)}"
    except Exception as e:
        return filename, f"Error: {e}"

def batch_ocr_parallel(filenames, max_workers=5):
    """Process multiple image files in parallel using OCR Space API"""
    results = {}
    if not filenames:
        return results
        
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(ocr_space_file, fname): fname for fname in filenames}
        for future in as_completed(future_to_file):
            fname, text = future.result()
            results[fname] = text
    return results

def extract_pptx_with_meta(pptx_path: str, tesseract_cmd: str = None) -> List[Dict[str, Any]]:
    """Extract content from PPTX with metadata, using OCR Space API for images"""
    prs = Presentation(pptx_path)
    all_slides_content = []
    
    # First pass: extract all images and save them temporarily
    temp_image_files = []
    image_to_shape_mapping = {}
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Extract all images first
        print(f"Extracting images from PPTX to temporary directory: {temp_dir}")
        for slide_index, slide in enumerate(prs.slides):
            for shape_index, shape in enumerate(slide.shapes):
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    try:
                        img = Image.open(BytesIO(shape.image.blob))
                        temp_file = os.path.join(temp_dir, f"slide_{slide_index}shape{shape_index}.png")
                        img.save(temp_file, 'PNG')
                        temp_image_files.append(temp_file)
                        image_to_shape_mapping[temp_file] = (slide_index, shape_index)
                        print(f"Extracted image: slide {slide_index}, shape {shape_index}")
                    except Exception as e:
                        print(f"Failed to extract image from slide {slide_index}, shape {shape_index}: {e}")
        
        # Process all images in parallel using OCR Space API
        print(f"Processing {len(temp_image_files)} images with OCR Space API...")
        ocr_results = batch_ocr_parallel(temp_image_files, max_workers=5)
        print(f"OCR processing completed for {len(ocr_results)} images")
        
        # Second pass: build the content structure
        for slide_index, slide in enumerate(prs.slides):
            slide_data = {
                "slide_number": slide_index + 1,
                "content_blocks": []
            }

            for shape_index, shape in enumerate(slide.shapes):
                content_block = {}

                if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX or shape.has_text_frame:
                    text = shape.text.strip()
                    if text:
                        content_block["type"] = "text"
                        content_block["content"] = text

                elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    # Find the corresponding OCR result
                    temp_file_key = None
                    for temp_file, (s_idx, sh_idx) in image_to_shape_mapping.items():
                        if s_idx == slide_index and sh_idx == shape_index:
                            temp_file_key = temp_file
                            break
                    
                    if temp_file_key and temp_file_key in ocr_results:
                        ocr_text = ocr_results[temp_file_key].strip()
                        if ocr_text and not ocr_text.startswith("Error:"):
                            content_block["type"] = "image"
                            content_block["content"] = ocr_text
                            print(f"OCR extracted from slide {slide_index}: {ocr_text[:100]}...")
                        else:
                            content_block["type"] = "image"
                            content_block["content"] = f"[OCR failed: {ocr_text}]"
                    else:
                        content_block["type"] = "image"
                        content_block["content"] = "[OCR processing failed - no result found]"

                elif shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                    try:
                        table = shape.table
                        content_block["type"] = "table"
                        table_content = "---Table---\n"
                        for row in table.rows:
                            row_content = ", ".join([cell.text.strip() for cell in row.cells])
                            table_content += row_content + "\n"
                        table_content += "-" * 11
                        content_block["content"] = table_content
                    except Exception as e:
                        content_block["type"] = "table"
                        content_block["content"] = f"[Table extraction failed: {str(e)}]"

                if content_block:
                    slide_data["content_blocks"].append(content_block)

            # Handle slide notes
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    slide_data["content_blocks"].append({
                        "type": "notes",
                        "content": notes
                    })

            all_slides_content.append(slide_data)
            
    finally:
        # Clean up temporary files
        print(f"Cleaning up {len(temp_image_files)} temporary files...")
        for temp_file in temp_image_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Failed to remove temp file {temp_file}: {e}")
        
        # Remove temp directory
        try:
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
            print("Temporary directory cleanup completed")
        except Exception as e:
            print(f"Failed to remove temp directory {temp_dir}: {e}")
    
    return all_slides_content

def extract_pptx(filepath: str) -> str:
    """
    Converts extracted pptx content into a plain text string for LLM input.
    Removes all metadata like slide numbers, block types, etc.
    """
    text_blocks = []
    
    for slide in extract_pptx_with_meta(filepath):
        for block in slide["content_blocks"]:
            content = block.get("content", "").strip()
            if content:
                text_blocks.append(content)
                
        # Optionally separate slides with a line
        text_blocks.append("\n--- End of Slide ---\n")
    
    return "\n".join(text_blocks).strip()

import json