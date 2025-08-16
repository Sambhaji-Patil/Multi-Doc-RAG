from docx import Document
from docx.document import Document as _Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from typing import Union, List, Dict, Any
from PIL import Image
from io import BytesIO
import pytesseract
import os

from zipfile import ZipFile
from lxml import etree
from pathlib import Path
import io
from zipfile import ZipFile
from lxml import etree

from zipfile import ZipFile
from lxml import etree

from zipfile import ZipFile
from lxml import etree

def extract_docx(docx_input) -> str:
    zipf = ZipFile(docx_input)
    xml_content = zipf.read("word/document.xml")
    tree = etree.fromstring(xml_content)

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    }

    text_blocks = []

    # 1. Extract all tables with gridSpan handling (same as before)
    tables = tree.xpath("//w:tbl", namespaces=ns)
    table_elements = set(tables)  # To compare against ancestors
    table_index = 0
    for tbl in tables:
        rows = tbl.xpath("./w:tr", namespaces=ns)
        sub_tables = []
        current_table = []

        prev_col_count = None
        for row in rows:
            row_texts = []
            cells = row.xpath("./w:tc", namespaces=ns)
            col_count = 0
            for cell in cells:
                grid_span_el = cell.xpath("./w:tcPr/w:gridSpan", namespaces=ns)
                span = int(grid_span_el[0].get(f"{{{ns['w']}}}val")) if grid_span_el else 1
                col_count += span

                texts = cell.xpath(".//w:t", namespaces=ns)
                cell_text = " ".join(t.text for t in texts if t.text).strip()
                row_texts.extend([cell_text] * span)

            # Heuristic to split: if row has 1 cell or empty row, or sharp col_count drop
            if not any(row_texts) or (prev_col_count and col_count < prev_col_count // 2):
                if current_table:
                    sub_tables.append(current_table)
                    current_table = []
                prev_col_count = None
                continue

            current_table.append(row_texts)
            prev_col_count = col_count

        # Append any remaining rows
        if current_table:
            sub_tables.append(current_table)

        for sub_index, sub_table in enumerate(sub_tables):
            table_lines = []
            for row in sub_table:
                table_lines.append(", ".join(str(t) for t in row))
            table_csv = f"--- TABLE {table_index} ---\n" + "\n".join(table_lines)
            text_blocks.append(table_csv)
            table_index += 1



    all_paragraphs = tree.xpath("//w:p", namespaces=ns)
    for p in all_paragraphs:
        # Check if this paragraph is inside a table by walking up to the root
        if not any(ancestor.tag == f"{{{ns['w']}}}tbl" for ancestor in p.iterancestors()):
            texts = p.xpath(".//w:t", namespaces=ns)
            para_text = "".join(t.text for t in texts if t.text)
            if para_text.strip():
                text_blocks.append(para_text.strip())

    # 3. Extract textboxes separately
    tb_contents = tree.xpath("//w:txbxContent", namespaces=ns)
    for tb in tb_contents:
        texts = tb.xpath(".//w:t", namespaces=ns)
        tb_text = " ".join(t.text for t in texts if t.text)
        if tb_text.strip():
            text_blocks.append(tb_text.strip())

    return "\n\n".join(text_blocks)

