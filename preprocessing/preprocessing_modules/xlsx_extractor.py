from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenPyXLImage
from typing import List, Dict, Any
from PIL import Image
from io import BytesIO
import pytesseract
import os

from typing import List, Dict

def extract_xlsx_with_meta(xlsx_path: str, tesseract_cmd: str = None) -> List[Dict[str, Any]]:
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    wb = load_workbook(xlsx_path, data_only=True)
    all_sheets_content = []

    for sheet in wb.worksheets:
        sheet_data = {
            "sheet_name": sheet.title,
            "content_blocks": []
        }

        # Extract table data
        for row in sheet.iter_rows(max_row=sheet.max_row, values_only=True):
            if all(cell is None for cell in row):
                continue  # skip completely empty rows
            row_data = [str(cell).strip() if cell is not None else "" for cell in row]
            content_block = {
                "type": "table_row",
                "content": ",".join(row_data)
            }
            sheet_data["content_blocks"].append(content_block)

        # Extract images from the sheet
        if hasattr(sheet, '_images'):
            for img in sheet._images:
                try:
                    if hasattr(img, '_data'):  # if it's a real OpenPyXL Image
                        image_data = img._data()
                    elif hasattr(img, '_ref'):
                        continue  # cell ref-only images; ignore
                    else:
                        continue

                    pil_img = Image.open(BytesIO(image_data))
                    ocr_text = pytesseract.image_to_string(pil_img).strip()

                    content_block = {
                        "type": "image",
                        "content": ocr_text if ocr_text else "[No OCR text detected]"
                    }
                except Exception as e:
                    content_block = {
                        "type": "image",
                        "content": f"[OCR failed: {str(e)}]"
                    }

                sheet_data["content_blocks"].append(content_block)

        all_sheets_content.append(sheet_data)

    return all_sheets_content


def extract_xlsx(filepath: str) -> str:
    lines = []

    for sheet in extract_xlsx_with_meta(filepath):
        lines.append(f"### Sheet: {sheet['sheet_name']}")
        for block in sheet['content_blocks']:
            if block['type'] == "table_row":
                lines.append(f"- {block['content']}")
            elif block['type'] == "image":
                lines.append(f"[Image OCR Content] {block['content']}")
            else:
                lines.append(f"[Unknown Content Type] {block['content']}")
        lines.append("")  # newline between sheets

    return "\n".join(lines)



