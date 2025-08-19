from zipfile import ZipFile
from lxml import etree
from typing import List, Dict, Any
from logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__file__)

def extract_docx(docx_input) -> List[Dict[str, Any]]:
    """
    Extracts structured text from a DOCX file and groups it by page number.
    
    This function relies on the <w:lastRenderedPageBreak/> element, which is
    an indicator left by MS Word during the last save, to determine page breaks.
    The accuracy of page separation depends on the DOCX file being saved
    by a compatible word processor.

    Args:
        docx_input (str or file-like object): Path to the .docx file or a file-like object.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary represents a page.
        e.g., [{"page_num": 1, "content": "Text and tables from page 1..."}]
    """
    # Define the XML namespace for Word documents
    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    }

    try:
        zipf = ZipFile(docx_input)
        xml_content = zipf.read("word/document.xml")
    except Exception as e:
        logger.error("Error reading DOCX file", error=str(e))
        return []

    tree = etree.fromstring(xml_content)
    body = tree.find("w:body", ns)

    if body is None:
        return []

    pages = []
    current_page_num = 1
    current_page_content = []
    table_counter = 0

    # Iterate through the direct children of the <body> tag (e.g., paragraphs and tables)
    # This approach preserves the document's content order.
    for element in body.iterchildren():
        content_to_add = ""
        tag = etree.QName(element.tag).localname

        # --- 1. Process Paragraphs (<w:p>) ---
        if tag == "p":
            para_parts = []
            
            # Extract regular text from the paragraph
            texts = element.xpath(".//w:t/text()", namespaces=ns)
            para_text = "".join(texts).strip()
            if para_text:
                para_parts.append(para_text)

            # Extract text from any textboxes within this paragraph
            tb_contents = element.xpath(".//w:txbxContent", namespaces=ns)
            for tb in tb_contents:
                tb_texts = tb.xpath(".//w:t/text()", namespaces=ns)
                tb_text = " ".join(tb_texts).strip()
                if tb_text:
                    # Label textbox content for clarity
                    para_parts.append(f"[Textbox: {tb_text}]")
            
            content_to_add = "\n".join(para_parts)

        # --- 2. Process Tables (<w:tbl>) ---
        elif tag == "tbl":
            table_lines = []
            rows = element.xpath("./w:tr", namespaces=ns)
            for row in rows:
                row_texts = []
                cells = row.xpath("./w:tc", namespaces=ns)
                for cell in cells:
                    # Handle horizontally merged cells (gridSpan)
                    grid_span_el = cell.xpath("./w:tcPr/w:gridSpan", namespaces=ns)
                    span = int(grid_span_el[0].get(f"{{{ns['w']}}}val")) if grid_span_el else 1

                    # Extract all text from the cell
                    cell_text = "".join(cell.xpath(".//w:t/text()", namespaces=ns)).strip()
                    row_texts.extend([cell_text] * span)
                
                table_lines.append(", ".join(row_texts))
            
            table_csv = f"--- TABLE {table_counter} ---\n" + "\n".join(table_lines)
            content_to_add = table_csv
            table_counter += 1

        # --- 3. Check for a Page Break marker within the element ---
        # This break indicates the END of the current page.
        # It can be either a "soft" break (<w:lastRenderedPageBreak/>) 
        # or a "hard" break (<w:br w:type="page"/>).
        page_break_found = element.xpath('.//w:lastRenderedPageBreak | .//w:br[@w:type="page"]', namespaces=ns)

        if content_to_add:
            current_page_content.append(content_to_add)

        # If a page break was found, this element is the last on the page.
        if page_break_found:
            if current_page_content:
                pages.append({
                    "page_num": current_page_num,
                    "content": "\n".join(current_page_content).strip()
                })
            
            # Reset for the next page
            current_page_num += 1
            current_page_content = []

    # After the loop, add any remaining content as the final page.
    if current_page_content:
        pages.append({
            "page_num": current_page_num,
            "content": "\n".join(current_page_content).strip()
        })

    return pages