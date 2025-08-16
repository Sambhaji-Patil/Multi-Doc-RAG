from zipfile import ZipFile
from lxml import etree
from pathlib import Path

from pathlib import Path
import requests
import io
from urllib.parse import urlparse
import urllib.request

import fitz  

def extract_docx(docx_input) -> str:
    if isinstance(docx_input, (str, Path)):
        zipf = ZipFile(docx_input)
    elif isinstance(docx_input, io.BytesIO):
        zipf = ZipFile(docx_input)
    else:
        raise ValueError("Unsupported input type for extract_docx")

    xml_content = zipf.read("word/document.xml")
    tree = etree.fromstring(xml_content)

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    }

    text_blocks = []

    # Extract paragraphs
    paragraphs = tree.xpath("//w:p", namespaces=ns)
    for p in paragraphs:
        texts = p.xpath(".//w:t", namespaces=ns)
        para_text = "".join(t.text for t in texts if t.text)
        if para_text.strip():
            text_blocks.append(para_text.strip())

    # Extract from text boxes
    tb_contents = tree.xpath("//w:txbxContent", namespaces=ns)
    for tb in tb_contents:
        texts = tb.xpath(".//w:t", namespaces=ns)
        tb_text = "".join(t.text for t in texts if t.text)
        if tb_text.strip():
            text_blocks.append(tb_text.strip())

    return "\n\n".join(text_blocks)

def extract_pdf(pdf_input) -> str:
    text = []

    if isinstance(pdf_input, (str, Path)):
        doc = fitz.open(pdf_input)
    elif isinstance(pdf_input, io.BytesIO):
        doc = fitz.open(stream=pdf_input, filetype="pdf")
    else:
        raise ValueError("Unsupported input type for extract_pdf")

    with doc:
        for page in doc:
            page_text = page.get_text("text")
            text.append(page_text)

    return "\n".join(text)


def detect_file_type_from_bytes(content: bytes) -> str:
    if content.startswith(b'%PDF'):
        return "pdf"
    elif content[0:2] == b'PK' and b'word/' in content:  # DOCX is a ZIP with word/ inside
        return "docx"
    elif all(chr(b).isprintable() or chr(b).isspace() for b in content[:100]):
        return "txt"
    return None

def convert_google_docs_url(url: str) -> str:
    if "docs.google.com" in url:
        # Extract document ID from various Google Docs URL formats
        if "/document/d/" in url:
            doc_id = url.split("/document/d/")[1].split("/")[0]
            return f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
        elif "id=" in url:
            doc_id = url.split("id=")[1].split("&")[0]
            return f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
        # Handle URLs like the one you provided with complex parameters
        elif "?usp=drive_link" in url or "rtpof=true" in url:
            # Extract doc ID from the full URL
            if "/d/" in url:
                doc_id = url.split("/d/")[1].split("/")[0]
                return f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
    return url

def extract(file_path_or_url: str):
    is_url = urlparse(file_path_or_url).scheme in ("http", "https")

    if is_url:
        url = convert_google_docs_url(url)
        try:
            response = requests.get(file_path_or_url)
            response.raise_for_status()
            content = response.content
            file_type = detect_file_type_from_bytes(content)
            file_like = io.BytesIO(content)
        except Exception as e:
            raise ValueError(f"Failed to fetch file: {e}")
    else:
        file_type = Path(file_path_or_url).suffix.lower().lstrip(".")
        file_like = file_path_or_url  # keep as path for local files

    if file_type == "pdf":
        text = extract_pdf(file_like if is_url else file_path_or_url)
        elements = partition_text(text=text)
    elif file_type == "docx":
        text = extract_docx(file_like if is_url else file_path_or_url)
        elements = partition_text(text=text)
    elif file_type == "txt":
        if is_url:
            text = content.decode("utf-8", errors="ignore")
        else:
            with open(file_path_or_url, 'r', encoding='utf-8') as f:
                text = f.read()
        elements = partition_text(text=text)
    else:
        raise ValueError("Unsupported or undetectable file type.")

    # chunking logic
    chunks = []
    section = "Unknown"
    for i, el in enumerate(elements):
        if el.category == "Title":
            section = el.text.strip()
        elif el.category in ["NarrativeText", "ListItem"]:
            chunks.append({
                "clause_id": f"auto_{i}",
                "section_title": section,
                "raw_text": el.text.strip(),
                "source_file": (
                    Path(file_path_or_url).name if not is_url else file_path_or_url.split("/")[-1]
                ),
                "position_in_doc": i
            })
    return chunks
